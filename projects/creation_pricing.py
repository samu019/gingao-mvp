from math import ceil


# GINGAO_CREATION_PRICING_V37

QUALITY_LABELS = {
    "fast": "Rapida",
    "standard": "Estandar",
    "premium": "Premium",
}


VALID_ASPECT_RATIOS = {
    "9:16",
    "16:9",
    "1:1",
    "4:5",
}


VALID_QUALITY_TIERS = {
    "fast",
    "standard",
    "premium",
}


def calculate_creation_cost(
    duration,
    quality="standard",
    voice_enabled=True,
):
    duration = max(
        1,
        int(duration)
    )

    if quality not in VALID_QUALITY_TIERS:
        quality = "standard"

    blocks = max(
        1,
        ceil(
            duration / 15
        )
    )

    base = blocks * 2

    multipliers = {
        "fast": 1.0,
        "standard": 1.5,
        "premium": 2.25,
    }

    visual_cost = ceil(
        base
        * multipliers[quality]
    )

    voice_cost = (
        blocks
        if voice_enabled
        else 0
    )

    return int(
        visual_cost
        + voice_cost
    )


def normalize_creation_options(
    *,
    duration,
    aspect_ratio,
    quality,
    voice_enabled,
):
    allowed_durations = {
        15,
        20,
        30,
        60,
    }

    try:
        duration = int(
            duration
        )
    except (
        TypeError,
        ValueError,
    ):
        duration = 20

    if duration not in allowed_durations:
        duration = 20

    if aspect_ratio not in VALID_ASPECT_RATIOS:
        aspect_ratio = "9:16"

    if quality not in VALID_QUALITY_TIERS:
        quality = "standard"

    voice_enabled = bool(
        voice_enabled
    )

    cost = calculate_creation_cost(
        duration=duration,
        quality=quality,
        voice_enabled=voice_enabled,
    )

    return {
        "duration":
            duration,
        "aspect_ratio":
            aspect_ratio,
        "quality":
            quality,
        "voice_enabled":
            voice_enabled,
        "cost":
            cost,
    }
