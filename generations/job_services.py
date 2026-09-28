from django.db import transaction
from django.utils import timezone

from config.runtime import (
    get_runtime_config,
)

from generations.models import (
    GenerationJob,
)


ACTIVE_STATUSES = {
    GenerationJob.STATUS_QUEUED,
    GenerationJob.STATUS_PROCESSING,
}


def make_idempotency_key(
    *,
    user,
    project,
    job_type,
    scene=None,
):
    scene_part = (
        f"scene:{scene.id}"
        if scene is not None
        else "scene:none"
    )

    return (
        f"user:{user.id}|"
        f"project:{project.id}|"
        f"{scene_part}|"
        f"type:{job_type}"
    )


@transaction.atomic
def create_job(
    *,
    user,
    project,
    job_type,
    scene=None,
    provider=None,
    payload=None,
):
    cfg = get_runtime_config()

    if provider is None:

        if job_type == (
            GenerationJob.TYPE_IMAGE
        ):
            provider = (
                cfg.image_provider
            )

        elif job_type == (
            GenerationJob.TYPE_VIDEO
        ):
            provider = (
                cfg.video_provider
            )

        elif job_type == (
            GenerationJob.TYPE_AUDIO
        ):
            provider = (
                cfg.audio_provider
            )

        else:
            provider = "internal"

    key = make_idempotency_key(
        user=user,
        project=project,
        job_type=job_type,
        scene=scene,
    )

    existing = (
        GenerationJob.objects
        .select_for_update()
        .filter(
            idempotency_key__startswith=(
                key + "|"
            ),
            status__in=ACTIVE_STATUSES,
        )
        .first()
    )

    if existing is not None:
        return existing, False

    # Permite nuevo job despu?s de completar/fallar,
    # pero con clave ?nica renovada.
    unique_key = (
        key
        + "|"
        + timezone.now().strftime(
            "%Y%m%d%H%M%S%f"
        )
    )

    job = GenerationJob.objects.create(
        user=user,
        project=project,
        scene=scene,
        job_type=job_type,
        provider=provider,
        status=(
            GenerationJob.STATUS_QUEUED
        ),
        idempotency_key=unique_key,
        payload=payload or {},
    )

    return job, True


@transaction.atomic
def mark_processing(job_id):

    job = (
        GenerationJob.objects
        .select_for_update()
        .get(id=job_id)
    )

    if job.status == (
        GenerationJob.STATUS_COMPLETED
    ):
        return job

    job.status = (
        GenerationJob.STATUS_PROCESSING
    )

    job.attempts += 1

    if job.started_at is None:
        job.started_at = timezone.now()

    job.error_message = ""

    job.save(
        update_fields=[
            "status",
            "attempts",
            "started_at",
            "error_message",
            "updated_at",
        ]
    )

    return job


@transaction.atomic
def mark_completed(
    *,
    job_id,
    result_url="",
):

    job = (
        GenerationJob.objects
        .select_for_update()
        .get(id=job_id)
    )

    job.status = (
        GenerationJob.STATUS_COMPLETED
    )

    job.result_url = (
        result_url or ""
    )

    job.finished_at = timezone.now()

    job.error_message = ""

    job.save(
        update_fields=[
            "status",
            "result_url",
            "finished_at",
            "error_message",
            "updated_at",
        ]
    )

    return job


@transaction.atomic
def mark_failed(
    *,
    job_id,
    error_message,
):

    job = (
        GenerationJob.objects
        .select_for_update()
        .get(id=job_id)
    )

    job.status = (
        GenerationJob.STATUS_FAILED
    )

    job.error_message = str(
        error_message
    )[:4000]

    job.finished_at = (
        timezone.now()
    )

    job.save(
        update_fields=[
            "status",
            "error_message",
            "finished_at",
            "updated_at",
        ]
    )

    return job


def can_retry(job):

    return (
        job.status
        == GenerationJob.STATUS_FAILED
        and job.attempts
        < job.max_attempts
    )
