import hashlib
import hmac
import json
from dataclasses import dataclass
from decimal import Decimal

import requests
from django.conf import settings


@dataclass
class NowPaymentsResult:
    ok: bool
    provider_payment_id: str = ""
    checkout_url: str = ""
    payment_status: str = ""
    pay_address: str = ""
    pay_amount: str = ""
    pay_currency: str = ""
    raw: dict = None
    error: str = ""


def _require_live_credentials():
    if not settings.NOWPAYMENTS_API_KEY:
        raise RuntimeError(
            "NOWPAYMENTS_API_KEY is not configured."
        )

    if not settings.NOWPAYMENTS_IPN_SECRET:
        raise RuntimeError(
            "NOWPAYMENTS_IPN_SECRET is not configured."
        )


def _headers():
    return {
        "x-api-key":
            settings.NOWPAYMENTS_API_KEY,

        "Content-Type":
            "application/json",
    }


def _absolute_url(
    request,
    path,
):
    public_base = (
        getattr(
            settings,
            "GINGAO_PUBLIC_BASE_URL",
            "",
        )
        .strip()
        .rstrip("/")
    )

    if public_base:
        return (
            public_base
            + "/"
            + str(path).lstrip("/")
        )

    if request is None:
        raise RuntimeError(
            "GINGAO_PUBLIC_BASE_URL is not "
            "configured and no request exists."
        )

    return request.build_absolute_uri(
        path
    )




# ============================================================
# GINGAO_V50D4_LIVE_READINESS
# ============================================================

def get_live_readiness():
    public_base = (
        getattr(
            settings,
            "GINGAO_PUBLIC_BASE_URL",
            "",
        )
        .strip()
        .rstrip("/")
    )

    checks = {
        "api_key":
            bool(
                getattr(
                    settings,
                    "NOWPAYMENTS_API_KEY",
                    "",
                )
            ),

        "ipn_secret":
            bool(
                getattr(
                    settings,
                    "NOWPAYMENTS_IPN_SECRET",
                    "",
                )
            ),

        "public_base_url":
            bool(public_base),

        "https":
            public_base.startswith(
                "https://"
            ),

        "not_localhost":
            (
                "localhost"
                not in public_base.lower()
                and
                "127.0.0.1"
                not in public_base
            ),
    }

    return {
        "ready":
            all(
                checks.values()
            ),
        "checks":
            checks,
        "public_base_url":
            public_base,
    }


def check_nowpayments_connectivity():
    """
    Read-only connectivity test.

    - GET /status: checks NOWPayments API availability.
    - GET /estimate: validates our x-api-key without creating a payment.
    - Does not create invoices, payments or modify credits.
    """
    result = {
        "api_status": False,
        "api_key": False,
        "ready": False,
        "error": "",
    }

    try:
        status_response = requests.get(
            settings.NOWPAYMENTS_API_BASE_URL + "/status",
            timeout=settings.NOWPAYMENTS_TIMEOUT_SECONDS,
        )
        status_response.raise_for_status()

        status_data = status_response.json()

        result["api_status"] = (
            str(status_data.get("message", "")).upper()
            == "OK"
        )

        estimate_response = requests.get(
            settings.NOWPAYMENTS_API_BASE_URL + "/estimate",
            headers=_headers(),
            params={
                "amount": "1",
                "currency_from": "usd",
                "currency_to": "btc",
            },
            timeout=settings.NOWPAYMENTS_TIMEOUT_SECONDS,
        )
        estimate_response.raise_for_status()

        estimate_data = estimate_response.json()

        result["api_key"] = (
            "estimated_amount" in estimate_data
            or "amount_from" in estimate_data
        )

        result["ready"] = (
            result["api_status"]
            and result["api_key"]
        )

    except Exception as exc:
        result["error"] = (
            exc.__class__.__name__
        )

    return result



def require_live_readiness():
    result = get_live_readiness()

    if not result["ready"]:
        missing = [
            key
            for key, ok
            in result["checks"].items()
            if not ok
        ]

        raise RuntimeError(
            "NOWPayments live configuration "
            "is incomplete: "
            + ", ".join(missing)
        )

    return result


def create_usdt_payment(
    *,
    payment,
    request,
):
    """
    Create a direct USDT payment.

    NETWORK FUNCTION:
    Only call this when GINGAO_PAYMENT_MODE=live.
    """

    _require_live_credentials()
    require_live_readiness()

    callback_url = _absolute_url(
        request,
        "/billing/webhook/nowpayments/",
    )

    payload = {
        "price_amount":
            float(payment.amount_usd),

        "price_currency":
            "usd",

        "pay_currency":
            settings.NOWPAYMENTS_USDT_CURRENCY,

        "order_id":
            str(payment.id),

        "order_description":
            (
                f"Gingao {payment.plan_code} "
                f"- {payment.credits} credits"
            ),

        "ipn_callback_url":
            callback_url,
    }

    response = requests.post(
        (
            settings.NOWPAYMENTS_API_BASE_URL
            + "/payment"
        ),
        headers=_headers(),
        json=payload,
        timeout=(
            settings
            .NOWPAYMENTS_TIMEOUT_SECONDS
        ),
    )

    response.raise_for_status()

    data = response.json()

    payment_id = str(
        data.get(
            "payment_id",
            "",
        )
    ).strip()

    if not payment_id:
        raise RuntimeError(
            "NOWPayments did not return payment_id."
        )

    return NowPaymentsResult(
        ok=True,
        provider_payment_id=payment_id,
        payment_status=str(
            data.get(
                "payment_status",
                "",
            )
        ),
        pay_address=str(
            data.get(
                "pay_address",
                "",
            )
        ),
        pay_amount=str(
            data.get(
                "pay_amount",
                "",
            )
        ),
        pay_currency=str(
            data.get(
                "pay_currency",
                "",
            )
        ),
        raw=data,
    )


def create_card_invoice(
    *,
    payment,
    request,
):
    """
    Create a NOWPayments invoice.

    The NOWPayments invoice checkout may expose
    fiat/card purchase options supported by their
    fiat partner.

    NETWORK FUNCTION:
    Only call this when GINGAO_PAYMENT_MODE=live.
    """

    _require_live_credentials()
    require_live_readiness()

    callback_url = _absolute_url(
        request,
        "/billing/webhook/nowpayments/",
    )

    success_url = _absolute_url(
        request,
        (
            f"/billing/payment/"
            f"{payment.id}/"
        ),
    )

    cancel_url = _absolute_url(
        request,
        "/billing/",
    )

    payload = {
        "price_amount":
            float(payment.amount_usd),

        "price_currency":
            "usd",

        "order_id":
            str(payment.id),

        "order_description":
            (
                f"Gingao {payment.plan_code} "
                f"- {payment.credits} credits"
            ),

        "ipn_callback_url":
            callback_url,

        "success_url":
            success_url,

        "cancel_url":
            cancel_url,
    }

    response = requests.post(
        (
            settings.NOWPAYMENTS_API_BASE_URL
            + "/invoice"
        ),
        headers=_headers(),
        json=payload,
        timeout=(
            settings
            .NOWPAYMENTS_TIMEOUT_SECONDS
        ),
    )

    response.raise_for_status()

    data = response.json()

    invoice_id = str(
        data.get(
            "id",
            data.get(
                "invoice_id",
                "",
            ),
        )
    ).strip()

    invoice_url = str(
        data.get(
            "invoice_url",
            "",
        )
    ).strip()

    if not invoice_id:
        raise RuntimeError(
            "NOWPayments did not return invoice id."
        )

    if not invoice_url:
        raise RuntimeError(
            "NOWPayments did not return invoice_url."
        )

    return NowPaymentsResult(
        ok=True,
        provider_payment_id=invoice_id,
        checkout_url=invoice_url,
        raw=data,
    )


def canonical_ipn_payload(
    payload,
):
    """
    NOWPayments IPN signature canonicalization.

    JSON keys are sorted recursively by json.dumps
    with compact separators.
    """

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def calculate_ipn_signature(
    payload,
):
    secret = (
        settings.NOWPAYMENTS_IPN_SECRET
    )

    if not secret:
        raise RuntimeError(
            "NOWPAYMENTS_IPN_SECRET "
            "is not configured."
        )

    body = canonical_ipn_payload(
        payload
    )

    return hmac.new(
        secret.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha512,
    ).hexdigest()


def verify_ipn_signature(
    *,
    payload,
    signature,
):
    if not signature:
        return False

    expected = calculate_ipn_signature(
        payload
    )

    return hmac.compare_digest(
        expected.lower(),
        str(signature).strip().lower(),
    )


def normalize_status(
    status,
):
    """
    Gingao fixed-price credit-plan policy.

    Only NOWPayments 'finished' is considered
    final enough to release purchased credits.
    """

    value = (
        str(status or "")
        .strip()
        .lower()
    )

    if value == "finished":
        return "paid"

    if value in {
        "waiting",
    }:
        return "pending"

    if value in {
        "confirming",
        "confirmed",
        "sending",
        "partially_paid",
    }:
        return "processing"

    if value in {
        "failed",
        "refunded",
    }:
        return "failed"

    if value == "expired":
        return "expired"

    return "pending"

