from django.conf import settings
from django.db import models
class CreditWallet(models.Model):
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='wallet')
    balance=models.PositiveIntegerField(default=0)
    unlimited=models.BooleanField(default=False)
    updated_at=models.DateTimeField(auto_now=True)
class CreditTransaction(models.Model):
    TYPES=[('grant','Grant'),('reserve','Reserve'),('charge','Charge'),('refund','Refund'),('purchase','Purchase')]
    wallet=models.ForeignKey(CreditWallet,on_delete=models.CASCADE,related_name='transactions')
    kind=models.CharField(max_length=16,choices=TYPES)
    amount=models.IntegerField()
    reference=models.CharField(max_length=128,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)



# ============================================================
# Gingao Payment Core
# ============================================================

import uuid as _uuid

from django.conf import settings as _settings


class Payment(models.Model):

    METHOD_CARD = "card"
    METHOD_USDT = "usdt"

    METHOD_CHOICES = [
        (METHOD_CARD, "Tarjeta bancaria"),
        (METHOD_USDT, "USDT"),
    ]

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_PAID = "paid"
    STATUS_FAILED = "failed"
    STATUS_EXPIRED = "expired"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_PAID, "Paid"),
        (STATUS_FAILED, "Failed"),
        (STATUS_EXPIRED, "Expired"),
    ]

    user = models.ForeignKey(
        _settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="gingao_payments",
    )

    plan_code = models.CharField(
        max_length=50
    )

    amount_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    credits = models.PositiveIntegerField()

    payment_method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
    )

    provider = models.CharField(
        max_length=60,
        default="mock",
    )

    provider_payment_id = models.CharField(
        max_length=120,
        unique=True,
        default=_uuid.uuid4,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )

    checkout_url = models.TextField(
        blank=True,
        default="",
    )

    metadata = models.JSONField(
        blank=True,
        default=dict,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    credited_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.user} - "
            f"{self.plan_code} - "
            f"{self.payment_method} - "
            f"{self.status}"
        )
