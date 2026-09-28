from dataclasses import dataclass

from config.runtime import (
    get_runtime_config,
)


@dataclass(frozen=True)
class CostEstimate:

    provider: str
    external_usd: float
    internal_credits: int
    note: str = ""


def image_megapixels():
    cfg = get_runtime_config()

    return (
        cfg.image_width
        * cfg.image_height
        / 1_000_000
    )


def estimate_image_cost():

    cfg = get_runtime_config()

    if cfg.image_provider == "mock":

        return CostEstimate(
            provider="mock",
            external_usd=0.0,
            internal_credits=0,
            note="Development Mock"
        )

    if cfg.image_provider == "fal":

        # FLUX.2 Turbo provisional:
        # coste estimado por megapixel.
        #
        # Este valor es configurable y
        # debe revisarse antes de produccion.
        price_per_mp = 0.008

        external = (
            image_megapixels()
            * price_per_mp
        )

        return CostEstimate(
            provider="fal",
            external_usd=external,
            internal_credits=(
                cfg.image_credit_cost
            ),
            note=(
                "Estimacion provisional "
                "FLUX.2 Turbo"
            )
        )

    return CostEstimate(
        provider=cfg.image_provider,
        external_usd=0.0,
        internal_credits=(
            cfg.image_credit_cost
        ),
        note=(
            "Proveedor real sin precio "
            "configurado."
        )
    )


def estimate_video_scene_cost(
    duration_seconds,
):

    cfg = get_runtime_config()

    if cfg.video_provider == "mock":

        return CostEstimate(
            provider="mock",
            external_usd=0.0,
            internal_credits=0,
            note="Development Mock"
        )

    return CostEstimate(
        provider=cfg.video_provider,
        external_usd=0.0,
        internal_credits=(
            cfg.video_credit_cost
        ),
        note=(
            "Precio externo pendiente "
            "de benchmark real."
        )
    )


def estimate_audio_cost(
    duration_seconds,
):

    cfg = get_runtime_config()

    if cfg.audio_provider == "mock":

        return CostEstimate(
            provider="mock",
            external_usd=0.0,
            internal_credits=0,
            note="Development Mock"
        )

    return CostEstimate(
        provider=cfg.audio_provider,
        external_usd=0.0,
        internal_credits=(
            cfg.audio_credit_cost
        ),
        note=(
            "Precio externo pendiente "
            "de benchmark real."
        )
    )


def estimate_project_cost(
    project
):

    scenes = list(
        project.scenes
        .all()
        .order_by("position")
    )

    image_cost = (
        estimate_image_cost()
    )

    total_external = 0.0
    total_credits = 0

    image_external = (
        image_cost.external_usd
        * len(scenes)
    )

    image_credits = (
        image_cost.internal_credits
        * len(scenes)
    )

    total_external += (
        image_external
    )

    total_credits += (
        image_credits
    )

    video_external = 0.0
    video_credits = 0

    for scene in scenes:

        estimate = (
            estimate_video_scene_cost(
                scene.duration_seconds
            )
        )

        video_external += (
            estimate.external_usd
        )

        video_credits += (
            estimate.internal_credits
        )

    total_external += (
        video_external
    )

    total_credits += (
        video_credits
    )

    duration = sum(
        int(
            scene.duration_seconds
            or 0
        )
        for scene in scenes
    )

    audio_cost = (
        estimate_audio_cost(
            duration
        )
    )

    total_external += (
        audio_cost.external_usd
    )

    total_credits += (
        audio_cost.internal_credits
    )

    return {
        "scene_count":
            len(scenes),

        "duration_seconds":
            duration,

        "image_external_usd":
            image_external,

        "image_credits":
            image_credits,

        "video_external_usd":
            video_external,

        "video_credits":
            video_credits,

        "audio_external_usd":
            audio_cost.external_usd,

        "audio_credits":
            audio_cost.internal_credits,

        "total_external_usd":
            total_external,

        "total_internal_credits":
            total_credits,
    }
