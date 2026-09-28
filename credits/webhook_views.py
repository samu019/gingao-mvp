import json

from django.http import JsonResponse
from django.views.decorators.csrf import (
    csrf_exempt,
)
from django.views.decorators.http import (
    require_POST,
)

from credits.payment_webhooks import (
    InvalidWebhookSignature,
    WebhookValidationError,
    process_nowpayments_ipn,
)


@csrf_exempt
@require_POST
def nowpayments_webhook_view(
    request,
):
    """
    Public NOWPayments IPN endpoint.

    Authentication is the NOWPayments HMAC signature,
    not Django session/CSRF.
    """

    signature = (
        request.headers.get(
            "x-nowpayments-sig",
            "",
        )
    )

    try:
        payload = json.loads(
            request.body.decode(
                "utf-8"
            )
        )

    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        return JsonResponse(
            {
                "ok": False,
                "error":
                    "invalid_json",
            },
            status=400,
        )

    try:
        result = (
            process_nowpayments_ipn(
                payload=payload,
                signature=signature,
            )
        )

    except InvalidWebhookSignature:
        return JsonResponse(
            {
                "ok": False,
                "error":
                    "invalid_signature",
            },
            status=401,
        )

    except WebhookValidationError as exc:
        return JsonResponse(
            {
                "ok": False,
                "error":
                    str(exc),
            },
            status=400,
        )

    except Exception:
        # Do not expose internal exception details
        # to the public webhook caller.
        return JsonResponse(
            {
                "ok": False,
                "error":
                    "internal_error",
            },
            status=500,
        )

    return JsonResponse(
        result,
        status=200,
    )
