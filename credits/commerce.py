from dataclasses import dataclass

from django.db import models
from django.db import transaction

from credits.models import (
    CreditTransaction,
    CreditWallet,
)

from .plans import get_plan


@dataclass
class CreditOperation:
    ok: bool
    amount: int
    balance_before: int
    balance_after: int
    transaction: object = None
    message: str = ""


def _model_fields(model):
    return {
        field.name: field
        for field in model._meta.fields
    }


def _wallet_for_update(user):
    wallet, _ = (
        CreditWallet.objects
        .select_for_update()
        .get_or_create(
            user=user,
            defaults={"balance": 0},
        )
    )

    return wallet


def _required_fields_satisfied(
    model,
    kwargs,
):
    supplied = set(kwargs)

    for field in model._meta.fields:

        if field.primary_key:
            continue

        if field.name in supplied:
            continue

        if field.auto_created:
            continue

        if getattr(
            field,
            "auto_now",
            False
        ):
            continue

        if getattr(
            field,
            "auto_now_add",
            False
        ):
            continue

        if field.has_default():
            continue

        if field.null or field.blank:
            continue

        if isinstance(
            field,
            models.BooleanField
        ):
            continue

        return False, field.name

    return True, None


def _create_transaction(
    *,
    user,
    wallet,
    amount,
    operation,
    description,
):
    fields = _model_fields(
        CreditTransaction
    )

    candidates = {
        "user": user,
        "owner": user,
        "wallet": wallet,

        "amount": amount,
        "credits": amount,
        "delta": amount,

        "operation": operation,
        "kind": operation,
        "transaction_type": operation,
        "type": operation,

        "description": description,
        "note": description,
        "reason": description,
    }

    kwargs = {}

    for key, value in candidates.items():
        if key in fields:
            kwargs[key] = value

    ok, _ = _required_fields_satisfied(
        CreditTransaction,
        kwargs,
    )

    if not ok:
        # La operaci?n de saldo sigue siendo v?lida.
        # Simplemente no forzamos un modelo incompatible.
        return None

    return CreditTransaction.objects.create(
        **kwargs
    )


@transaction.atomic
def grant_credits(
    *,
    user,
    amount,
    description="Credit grant",
):
    amount = int(amount)

    if amount <= 0:
        raise ValueError(
            "El importe debe ser positivo."
        )

    wallet = _wallet_for_update(
        user
    )

    before = int(
        wallet.balance or 0
    )

    wallet.balance = (
        before + amount
    )

    wallet.save(
        update_fields=["balance"]
    )

    tx = _create_transaction(
        user=user,
        wallet=wallet,
        amount=amount,
        operation="grant",
        description=description,
    )

    return CreditOperation(
        ok=True,
        amount=amount,
        balance_before=before,
        balance_after=wallet.balance,
        transaction=tx,
        message="Creditos a?adidos.",
    )


@transaction.atomic
def reserve_credits(
    *,
    user,
    amount,
    description="Credit reservation",
):
    amount = int(amount)

    if amount <= 0:
        raise ValueError(
            "El importe debe ser positivo."
        )

    wallet = _wallet_for_update(
        user
    )

    before = int(
        wallet.balance or 0
    )

    if before < amount:
        return CreditOperation(
            ok=False,
            amount=amount,
            balance_before=before,
            balance_after=before,
            message=(
                "Creditos insuficientes."
            ),
        )

    wallet.balance = (
        before - amount
    )

    wallet.save(
        update_fields=["balance"]
    )

    tx = _create_transaction(
        user=user,
        wallet=wallet,
        amount=-amount,
        operation="reserve",
        description=description,
    )

    return CreditOperation(
        ok=True,
        amount=amount,
        balance_before=before,
        balance_after=wallet.balance,
        transaction=tx,
        message="Creditos reservados.",
    )


@transaction.atomic
def refund_credits(
    *,
    user,
    amount,
    description="Credit refund",
):
    amount = int(amount)

    if amount <= 0:
        raise ValueError(
            "El importe debe ser positivo."
        )

    wallet = _wallet_for_update(
        user
    )

    before = int(
        wallet.balance or 0
    )

    wallet.balance = (
        before + amount
    )

    wallet.save(
        update_fields=["balance"]
    )

    tx = _create_transaction(
        user=user,
        wallet=wallet,
        amount=amount,
        operation="refund",
        description=description,
    )

    return CreditOperation(
        ok=True,
        amount=amount,
        balance_before=before,
        balance_after=wallet.balance,
        transaction=tx,
        message="Creditos devueltos.",
    )


def simulate_plan_purchase(
    *,
    user,
    plan_code,
):
    plan = get_plan(
        plan_code
    )

    if plan is None:
        raise ValueError(
            "Plan desconocido."
        )

    result = grant_credits(
        user=user,
        amount=plan.credits,
        description=(
            "SIMULATED PURCHASE "
            f"{plan.name} "
            f"${plan.price_usd:.2f}"
        ),
    )

    return plan, result


def transaction_history(
    user,
    limit=30,
):
    fields = _model_fields(
        CreditTransaction
    )

    qs = (
        CreditTransaction.objects
        .all()
        .order_by("-pk")
    )

    if "user" in fields:
        qs = qs.filter(
            user=user
        )

    elif "owner" in fields:
        qs = qs.filter(
            owner=user
        )

    elif "wallet" in fields:
        wallet = (
            CreditWallet.objects
            .filter(user=user)
            .first()
        )

        if wallet is None:
            return []

        qs = qs.filter(
            wallet=wallet
        )

    else:
        return []

    return list(
        qs[:limit]
    )


def transaction_display(tx):
    fields = _model_fields(
        CreditTransaction
    )

    def value(*names):
        for name in names:
            if name in fields:
                current = getattr(
                    tx,
                    name,
                    None
                )
                if current not in (
                    None,
                    ""
                ):
                    return current
        return None

    amount = value(
        "amount",
        "credits",
        "delta",
    )

    operation = value(
        "operation",
        "kind",
        "transaction_type",
        "type",
    )

    description = value(
        "description",
        "note",
        "reason",
    )

    created = value(
        "created_at",
        "created",
        "timestamp",
    )

    return {
        "amount": amount,
        "operation": operation or "Movimiento",
        "description": (
            description or ""
        ),
        "created": created,
    }
