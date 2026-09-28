from django.db import transaction

from credits.services import reserve_credits, refund_credits
from .models import VideoGeneration


COST_TABLE = {
    ("ltx-fast", "720p", 3): 18,
    ("ltx-fast", "720p", 5): 30,
    ("ltx-quality", "720p", 5): 45,
}


def estimate_credits(model_code, resolution, duration_seconds):
    return COST_TABLE.get(
        (model_code, resolution, duration_seconds),
        max(10, duration_seconds * 6),
    )


@transaction.atomic
def create_generation(
    *,
    project,
    scene=None,
    model_code="ltx-fast",
    resolution="720p",
    duration_seconds=3,
):
    estimated = estimate_credits(
        model_code,
        resolution,
        duration_seconds
    )

    generation = VideoGeneration.objects.create(
        project=project,
        scene=scene,
        model_code=model_code,
        resolution=resolution,
        duration_seconds=duration_seconds,
        estimated_credits=estimated,
        status="queued",
    )

    reserve_credits(
        project.owner,
        estimated,
        reference=f"generation:{generation.pk}",
    )

    return generation


@transaction.atomic
def mark_generation_complete(generation, output_url):
    generation.status = "complete"
    generation.output_url = output_url
    generation.error_message = ""

    generation.save(
        update_fields=[
            "status",
            "output_url",
            "error_message",
            "updated_at",
        ]
    )

    return generation


@transaction.atomic
def mark_generation_failed(generation, error_message):
    if generation.status == "failed":
        return generation

    generation.status = "failed"
    generation.error_message = str(error_message)[:4000]

    generation.save(
        update_fields=[
            "status",
            "error_message",
            "updated_at",
        ]
    )

    refund_credits(
        generation.project.owner,
        generation.estimated_credits,
        reference=f"refund:generation:{generation.pk}",
    )

    return generation
