from io import BytesIO

import qrcode

from django.contrib.auth.decorators import (
    login_required,
)
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
)
from django.shortcuts import (
    get_object_or_404,
)

from credits.models import Payment


@login_required
def payment_qr_view(
    request,
    payment_id,
):
    payment = get_object_or_404(
        Payment,
        id=payment_id,
        user=request.user,
    )

    if (
        payment.payment_method
        != Payment.METHOD_USDT
    ):
        return HttpResponseBadRequest(
            "QR unavailable."
        )

    metadata = (
        payment.metadata
        or {}
    )

    address = str(
        metadata.get(
            "pay_address",
            "",
        )
    ).strip()

    if not address:
        return HttpResponseBadRequest(
            "Payment address unavailable."
        )

    # The QR intentionally contains the address only.
    # USDT exists on multiple networks and there is no
    # universal cross-wallet payment URI we should invent.
    image = qrcode.make(
        address
    )

    buffer = BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    response = HttpResponse(
        buffer.getvalue(),
        content_type="image/png",
    )

    response[
        "Cache-Control"
    ] = (
        "private, no-store, max-age=0"
    )

    response[
        "X-Content-Type-Options"
    ] = "nosniff"

    return response
