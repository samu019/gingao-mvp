from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction

from credits.models import Payment
from credits.payment_services import (
    confirm_payment,
    fail_payment,
)

from credits.nowpayments import (
    normalize_status,
    verify_ipn_signature,
)


class WebhookValidationError(Exception):
    pass


class InvalidWebhookSignature(
    WebhookValidationError
):
    pass


def _clean_string(value):
    return str(
        value
        if value is not None
        else ""
    ).strip()


def _decimal(value):
    try:
        return Decimal(
            _clean_string(value)
        )
    except (
        InvalidOperation,
        ValueError,
    ):
        raise WebhookValidationError(
            "Invalid decimal value."
        )


def _validate_price(
    *,
    payment,
    payload,
    require=False,
):
    raw_amount = payload.get(
        "price_amount"
    )

    raw_currency = payload.get(
        "price_currency"
    )

    if (
        raw_amount is None
        and raw_currency is None
        and not require
    ):
        return

    if raw_amount is None:
        raise WebhookValidationError(
            "Missing price_amount."
        )

    if raw_currency is None:
        raise WebhookValidationError(
            "Missing price_currency."
        )

    currency = (
        _clean_string(
            raw_currency
        )
        .lower()
    )

    if currency != "usd":
        raise WebhookValidationError(
            "Unexpected price_currency."
        )

    amount = _decimal(
        raw_amount
    )

    if amount != payment.amount_usd:
        raise WebhookValidationError(
            "Unexpected price_amount."
        )


def _safe_event_snapshot(
    payload,
):
    allowed = [
        "payment_id",
        "payment_status",
        "order_id",
        "price_amount",
        "price_currency",
        "pay_amount",
        "pay_currency",
        "actually_paid",
        "outcome_amount",
        "outcome_currency",
        "invoice_id",
        "purchase_id",
    ]

    return {
        key: payload.get(key)
        for key in allowed
        if key in payload
    }


@transaction.atomic
def process_nowpayments_ipn(
    *,
    payload,
    signature,
):
    """
    Validate and process a NOWPayments IPN.

    No credit is granted unless:
    - payment mode is live;
    - HMAC signature is valid;
    - order_id matches a local Payment;
    - provider is NOWPayments;
    - external payment identity is valid;
    - amount/currency validation succeeds;
    - provider status is exactly 'finished'.
    """

    if not getattr(
        settings,
        "GINGAO_PAYMENTS_LIVE",
        False,
    ):
        raise WebhookValidationError(
            "Live payments are disabled."
        )

    if not isinstance(
        payload,
        dict,
    ):
        raise WebhookValidationError(
            "Webhook payload must be an object."
        )

    if not verify_ipn_signature(
        payload=payload,
        signature=signature,
    ):
        raise InvalidWebhookSignature(
            "Invalid NOWPayments signature."
        )

    order_id = _clean_string(
        payload.get("order_id")
    )

    if not order_id:
        raise WebhookValidationError(
            "Missing order_id."
        )

    try:
        local_payment_id = int(
            order_id
        )
    except (
        TypeError,
        ValueError,
    ):
        raise WebhookValidationError(
            "Invalid order_id."
        )

    try:
        payment = (
            Payment.objects
            .select_for_update()
            .select_related("user")
            .get(
                id=local_payment_id
            )
        )

    except Payment.DoesNotExist:
        raise WebhookValidationError(
            "Unknown local payment."
        )

    if payment.provider != "nowpayments":
        raise WebhookValidationError(
            "Payment provider mismatch."
        )

    external_payment_id = (
        _clean_string(
            payload.get("payment_id")
        )
    )

    if not external_payment_id:
        raise WebhookValidationError(
            "Missing payment_id."
        )

    metadata = dict(
        payment.metadata
        or {}
    )

    # Direct USDT payment:
    # provider_payment_id IS the NOWPayments payment_id.
    if (
        payment.payment_method
        == Payment.METHOD_USDT
    ):
        if (
            external_payment_id
            != payment.provider_payment_id
        ):
            raise WebhookValidationError(
                "NOWPayments payment_id mismatch."
            )

    # Card / invoice flow:
    # provider_payment_id currently stores the invoice id.
    # The first valid signed payment IPN binds the actual
    # NOWPayments payment_id to this local payment.
    elif (
        payment.payment_method
        == Payment.METHOD_CARD
    ):
        # GINGAO_V50D4_INVOICE_ID_CHECK
        incoming_invoice_id = (
            _clean_string(
                payload.get(
                    "invoice_id"
                )
            )
        )

        if (
            incoming_invoice_id
            and
            incoming_invoice_id
            != payment.provider_payment_id
        ):
            raise WebhookValidationError(
                "NOWPayments invoice_id mismatch."
            )

        bound_payment_id = (
            _clean_string(
                metadata.get(
                    "nowpayments_payment_id"
                )
            )
        )

        if (
            bound_payment_id
            and bound_payment_id
            != external_payment_id
        ):
            raise WebhookValidationError(
                "Unexpected NOWPayments "
                "invoice payment_id."
            )

        if not bound_payment_id:
            metadata[
                "nowpayments_payment_id"
            ] = external_payment_id

    else:
        raise WebhookValidationError(
            "Unsupported payment method."
        )

    provider_status = (
        _clean_string(
            payload.get(
                "payment_status"
            )
        )
        .lower()
    )

    if not provider_status:
        raise WebhookValidationError(
            "Missing payment_status."
        )

    normalized = normalize_status(
        provider_status
    )

    # Validate provided price fields on every event.
    # On final success they are mandatory.
    _validate_price(
        payment=payment,
        payload=payload,
        require=(
            normalized == "paid"
        ),
    )

    metadata[
        "last_provider_status"
    ] = provider_status

    metadata[
        "last_ipn"
    ] = _safe_event_snapshot(
        payload
    )

    payment.metadata = metadata

    payment.save(
        update_fields=[
            "metadata",
            "updated_at",
        ]
    )

    # Never downgrade an already credited purchase.
    if payment.credited_at is not None:

        if provider_status == "refunded":
            return {
                "ok": True,
                "action":
                    "refund_requires_review",
                "credited": False,
                "payment_id":
                    payment.id,
            }

        return {
            "ok": True,
            "action":
                "already_credited",
            "credited": False,
            "payment_id":
                payment.id,
        }

    # Final successful state.
    if normalized == "paid":

        payment, credited = (
            confirm_payment(
                payment_id=payment.id
            )
        )

        return {
            "ok": True,
            "action":
                "credited"
                if credited
                else "already_credited",
            "credited":
                bool(credited),
            "payment_id":
                payment.id,
        }

    # Provider failure/refund before credit.
    if normalized == "failed":

        fail_payment(
            payment_id=payment.id
        )

        return {
            "ok": True,
            "action":
                "failed",
            "credited": False,
            "payment_id":
                payment.id,
        }

    # Expiration.
    if normalized == "expired":

        payment.status = (
            Payment.STATUS_EXPIRED
        )

        payment.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return {
            "ok": True,
            "action":
                "expired",
            "credited": False,
            "payment_id":
                payment.id,
        }

    # Intermediate states.
    target_status = (
        Payment.STATUS_PROCESSING
        if normalized == "processing"
        else Payment.STATUS_PENDING
    )

    # Do not downgrade terminal states.
    if payment.status not in {
        Payment.STATUS_PAID,
        Payment.STATUS_FAILED,
        Payment.STATUS_EXPIRED,
    }:
        payment.status = (
            target_status
        )

        payment.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    return {
        "ok": True,
        "action":
            normalized,
        "credited": False,
        "payment_id":
            payment.id,
    }
