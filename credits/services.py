from django.db import transaction
from .models import CreditTransaction, CreditWallet


class InsufficientCredits(Exception):
    pass


@transaction.atomic
def get_or_create_wallet(user):
    wallet, _ = CreditWallet.objects.select_for_update().get_or_create(user=user)
    return wallet


@transaction.atomic
def grant_credits(user, amount, reference=""):
    if amount <= 0:
        raise ValueError("amount must be greater than zero")

    wallet = get_or_create_wallet(user)

    if not wallet.unlimited:
        wallet.balance += amount
        wallet.save(update_fields=["balance", "updated_at"])

    CreditTransaction.objects.create(
        wallet=wallet,
        kind="grant",
        amount=amount,
        reference=reference,
    )

    return wallet


@transaction.atomic
def reserve_credits(user, amount, reference=""):
    if amount <= 0:
        raise ValueError("amount must be greater than zero")

    wallet = get_or_create_wallet(user)

    if not wallet.unlimited:
        if wallet.balance < amount:
            raise InsufficientCredits(
                f"Saldo insuficiente: disponible={wallet.balance}, necesario={amount}"
            )

        wallet.balance -= amount
        wallet.save(update_fields=["balance", "updated_at"])

    CreditTransaction.objects.create(
        wallet=wallet,
        kind="reserve",
        amount=-amount,
        reference=reference,
    )

    return wallet


@transaction.atomic
def refund_credits(user, amount, reference=""):
    if amount <= 0:
        raise ValueError("amount must be greater than zero")

    wallet = get_or_create_wallet(user)

    if not wallet.unlimited:
        wallet.balance += amount
        wallet.save(update_fields=["balance", "updated_at"])

    CreditTransaction.objects.create(
        wallet=wallet,
        kind="refund",
        amount=amount,
        reference=reference,
    )

    return wallet
