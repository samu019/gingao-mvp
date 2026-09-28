from django.conf import settings
from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import uuid4


@dataclass
class CheckoutResult:
    ok: bool
    provider: str
    provider_payment_id: str
    checkout_url: str
    error: str = ""
    metadata: dict = None


class PaymentProvider(ABC):

    code = "base"

    @abstractmethod
    def create_checkout(
        self,
        *,
        payment,
        request=None,
    ):
        raise NotImplementedError


class MockCardProvider(PaymentProvider):

    code = "mock_card"

    def create_checkout(
        self,
        *,
        payment,
        request=None,
    ):
        provider_payment_id = (
            "card_mock_"
            + uuid4().hex
        )

        checkout_url = (
            f"/billing/payment/"
            f"{payment.id}/"
        )

        return CheckoutResult(
            ok=True,
            provider=self.code,
            provider_payment_id=
                provider_payment_id,
            checkout_url=checkout_url,
        )


class MockUSDTProvider(PaymentProvider):

    code = "mock_usdt"

    def create_checkout(
        self,
        *,
        payment,
        request=None,
    ):
        provider_payment_id = (
            "usdt_mock_"
            + uuid4().hex
        )

        checkout_url = (
            f"/billing/payment/"
            f"{payment.id}/"
        )

        return CheckoutResult(
            ok=True,
            provider=self.code,
            provider_payment_id=
                provider_payment_id,
            checkout_url=checkout_url,
        )


# ============================================================
# GINGAO_V50D2_NOWPAYMENTS_PROVIDERS
# ============================================================


class NowPaymentsUSDTProvider(
    PaymentProvider
):
    code = "nowpayments"

    def create_checkout(
        self,
        *,
        payment,
        request=None,
    ):
        from .nowpayments import (
            create_usdt_payment,
        )

        result = create_usdt_payment(
            payment=payment,
            request=request,
        )

        return CheckoutResult(
            ok=result.ok,
            provider=self.code,
            provider_payment_id=(
                result.provider_payment_id
            ),
            checkout_url=(
                result.checkout_url or ""
            ),
            error=result.error,
            metadata={
                "nowpayments_type":
                    "payment",

                "payment_status":
                    result.payment_status,

                "pay_address":
                    result.pay_address,

                "pay_amount":
                    result.pay_amount,

                "pay_currency":
                    result.pay_currency,

                "raw":
                    result.raw or {},
            },
        )


class NowPaymentsCardProvider(
    PaymentProvider
):
    code = "nowpayments"

    def create_checkout(
        self,
        *,
        payment,
        request=None,
    ):
        from .nowpayments import (
            create_card_invoice,
        )

        result = create_card_invoice(
            payment=payment,
            request=request,
        )

        return CheckoutResult(
            ok=result.ok,
            provider=self.code,
            provider_payment_id=(
                result.provider_payment_id
            ),
            checkout_url=(
                result.checkout_url or ""
            ),
            error=result.error,
            metadata={
                "nowpayments_type":
                    "invoice",

                "invoice_url":
                    result.checkout_url,

                "raw":
                    result.raw or {},
            },
        )


PROVIDERS = {
    "card": MockCardProvider,
    "usdt": MockUSDTProvider,
}


def get_payment_provider(
    payment_method
):
    method = (
        str(payment_method)
        .strip()
        .lower()
    )

    payment_mode = getattr(
        settings,
        "GINGAO_PAYMENT_MODE",
        "disabled",
    )

    if payment_mode == "disabled":
        raise RuntimeError(
            "Los pagos estan desactivados."
        )

    if payment_mode == "live":

        live_providers = {
            "card":
                NowPaymentsCardProvider,

            "usdt":
                NowPaymentsUSDTProvider,
        }

        provider_class = (
            live_providers.get(
                method
            )
        )

        if provider_class is None:
            raise ValueError(
                "Metodo de pago no soportado."
            )

        return provider_class()

    if not getattr(
        settings,
        "GINGAO_MOCK_PAYMENTS_ENABLED",
        False,
    ):
        raise RuntimeError(
            "Los proveedores Mock "
            "no estan permitidos."
        )

    provider_class = PROVIDERS.get(
        method
    )

    if provider_class is None:
        raise ValueError(
            "Metodo de pago no soportado."
        )

    return provider_class()

