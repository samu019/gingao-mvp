import os
from dataclasses import dataclass


VALID_MODES = {
    "development",
    "production",
}


def env_str(
    name,
    default="",
):
    return (
        os.environ
        .get(name, default)
        .strip()
    )


def env_int(
    name,
    default,
):
    try:
        return int(
            env_str(
                name,
                str(default)
            )
        )
    except ValueError:
        return int(default)


def env_float(
    name,
    default,
):
    try:
        return float(
            env_str(
                name,
                str(default)
            )
        )
    except ValueError:
        return float(default)


def env_bool(
    name,
    default=False,
):
    raw = env_str(
        name,
        "1" if default else "0"
    ).lower()

    return raw in {
        "1",
        "true",
        "yes",
        "on",
    }


@dataclass(frozen=True)
class RuntimeConfig:

    mode: str

    image_provider: str
    video_provider: str
    audio_provider: str

    allow_real_image_bulk: bool
    allow_real_video_bulk: bool

    image_width: int
    image_height: int

    credits_per_usd: int

    image_credit_cost: int
    video_credit_cost: int
    audio_credit_cost: int

    fal_key_configured: bool


def get_runtime_config():

    mode = env_str(
        "GINGAO_MODE",
        "development"
    ).lower()

    if mode not in VALID_MODES:
        mode = "development"

    image_provider = env_str(
        "GINGAO_IMAGE_PROVIDER",
        "mock"
    ).lower()

    video_provider = env_str(
        "GINGAO_VIDEO_PROVIDER",
        "mock"
    ).lower()

    audio_provider = env_str(
        "GINGAO_AUDIO_PROVIDER",
        "mock"
    ).lower()

    return RuntimeConfig(
        mode=mode,

        image_provider=image_provider,
        video_provider=video_provider,
        audio_provider=audio_provider,

        allow_real_image_bulk=env_bool(
            "GINGAO_ALLOW_REAL_BULK",
            False
        ),

        allow_real_video_bulk=env_bool(
            "GINGAO_ALLOW_REAL_VIDEO_BULK",
            False
        ),

        image_width=env_int(
            "GINGAO_IMAGE_WIDTH",
            768
        ),

        image_height=env_int(
            "GINGAO_IMAGE_HEIGHT",
            1365
        ),

        credits_per_usd=env_int(
            "GINGAO_CREDITS_PER_USD",
            100
        ),

        image_credit_cost=env_int(
            "GINGAO_IMAGE_CREDIT_COST",
            1
        ),

        video_credit_cost=env_int(
            "GINGAO_VIDEO_CREDIT_COST",
            10
        ),

        audio_credit_cost=env_int(
            "GINGAO_AUDIO_CREDIT_COST",
            2
        ),

        fal_key_configured=bool(
            env_str(
                "FAL_KEY",
                ""
            )
        ),
    )


def production_warnings():

    cfg = get_runtime_config()

    warnings = []

    if cfg.mode != "production":
        warnings.append(
            "GINGAO_MODE no esta en production."
        )

    if cfg.image_provider == "mock":
        warnings.append(
            "El proveedor de imagen sigue en Mock."
        )

    if cfg.video_provider == "mock":
        warnings.append(
            "El proveedor de video sigue en Mock."
        )

    if cfg.audio_provider == "mock":
        warnings.append(
            "El proveedor de audio sigue en Mock."
        )

    if (
        cfg.image_provider == "fal"
        and not cfg.fal_key_configured
    ):
        warnings.append(
            "FAL_KEY no esta configurada."
        )

    return warnings


def production_ready():
    return len(
        production_warnings()
    ) == 0
