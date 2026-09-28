from django.db import transaction
from django.utils import timezone

from credits.models import Payment
from credits.plans import get_plan
from credits.commerce import grant_credits

from .payment_providers import (
    get_payment_provider,
)


VALID_METHODS = {
    Payment.METHOD_CARD,
    Payment.METHOD_USDT,
}


def create_payment(
    *,
    user,
    plan_code,
    payment_method,
    request=None,
):
    plan = get_plan(
        plan_code
    )

    if plan is None:
        raise ValueError(
            "Plan desconocido."
        )

    payment_method = (
        str(payment_method)
        .strip()
        .lower()
    )

    if payment_method not in VALID_METHODS:
        raise ValueError(
            "Metodo de pago no soportado."
        )

    payment = Payment.objects.create(
        user=user,
        plan_code=plan.code,
        amount_usd=plan.price_usd,
        credits=plan.credits,
        payment_method=payment_method,
        provider="initializing",
    )

    provider = get_payment_provider(
        payment_method
    )

    checkout = provider.create_checkout(
        payment=payment,
        request=request,
    )

    if not checkout.ok:

        payment.status = (
            Payment.STATUS_FAILED
        )

        payment.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        raise RuntimeError(
            checkout.error
            or "No se pudo crear checkout."
        )

    payment.provider = (
        checkout.provider
    )

    payment.provider_payment_id = (
        checkout.provider_payment_id
    )

    payment.checkout_url = (
        checkout.checkout_url
    )

    payment.metadata = (
        checkout.metadata
        or {}
    )

    payment.save(
        update_fields=[
            "provider",
            "provider_payment_id",
            "checkout_url",
            "metadata",
            "updated_at",
        ]
    )

    return payment


@transaction.atomic
def confirm_payment(
    *,
    payment_id,
):
    payment = (
        Payment.objects
        .select_for_update()
        .select_related("user")
        .get(id=payment_id)
    )

    # Idempotencia:
    # si ya fue acreditado, no repetimos.
    if payment.credited_at is not None:

        return payment, False

    if payment.status == (
        Payment.STATUS_FAILED
    ):
        raise RuntimeError(
            "El pago esta marcado como fallido."
        )

    if payment.status == (
        Payment.STATUS_EXPIRED
    ):
        raise RuntimeError(
            "El pago esta expirado."
        )

    now = timezone.now()

    payment.status = (
        Payment.STATUS_PAID
    )

    payment.paid_at = (
        payment.paid_at or now
    )

    payment.save(
        update_fields=[
            "status",
            "paid_at",
            "updated_at",
        ]
    )

    grant_credits(
        user=payment.user,
        amount=payment.credits,
        description=(
            f"PAYMENT "
            f"{payment.provider_payment_id} "
            f"{payment.plan_code}"
        ),
    )

    payment.credited_at = now

    payment.save(
        update_fields=[
            "credited_at",
            "updated_at",
        ]
    )

    return payment, True


@transaction.atomic
def fail_payment(
    *,
    payment_id,
):
    payment = (
        Payment.objects
        .select_for_update()
        .get(id=payment_id)
    )

    if payment.credited_at is not None:
        raise RuntimeError(
            "No puede fallarse un pago "
            "que ya fue acreditado."
        )

    payment.status = (
        Payment.STATUS_FAILED
    )

    payment.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    return payment
