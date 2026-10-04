from celery import shared_task

from .models import VideoGeneration
from .services import (
    mark_generation_complete,
    mark_generation_failed,
)


@shared_task(bind=True, max_retries=2)
def render_video(self, generation_id):
    generation = VideoGeneration.objects.select_related(
        "project__owner"
    ).get(pk=generation_id)

    generation.status = "processing"
    generation.save(
        update_fields=["status", "updated_at"]
    )

    try:
        output_url = (
            f"https://example.invalid/mock/"
            f"{generation.id}.mp4"
        )

        mark_generation_complete(
            generation,
            output_url
        )

        return output_url

    except Exception as exc:
        mark_generation_failed(
            generation,
            exc
        )

        raise

# =============================================================================
# GINGAO_CELERY_JOB_TASK_V46C
# =============================================================================

from celery import shared_task

from generations.models import (
    GenerationJob,
)

from generations.job_runner import (
    execute_job,
)

from credits.models import (
    CreditTransaction,
)

from credits.services import (
    refund_credits,
)



def _refund_failed_video_job(
    job,
):
    if job.job_type != (
        GenerationJob.TYPE_VIDEO
    ):
        return

    amount = int(
        getattr(
            job,
            "estimated_credits",
            0,
        )
        or 0
    )

    if amount <= 0:
        return

    reference = (
        f"refund:video-generation:{job.id}"
    )

    already_refunded = (
        CreditTransaction.objects
        .filter(
            reference=reference,
            kind="refund",
        )
        .exists()
    )

    if already_refunded:
        return

    refund_credits(
        job.user,
        amount,
        reference=reference,
    )


@shared_task(
    bind=True,
    name="gingao.execute_generation_job",
)
def execute_generation_job_task(
    self,
    job_id,
):

    try:

        job = (
            GenerationJob.objects
            .select_related(
                "user",
                "project",
                "scene",
            )
            .get(
                id=job_id
            )
        )

    except GenerationJob.DoesNotExist:

        return {
            "ok": False,
            "job_id": job_id,
            "error": (
                "GenerationJob not found."
            ),
        }


    if job.status == (
        GenerationJob.STATUS_COMPLETED
    ):

        return {
            "ok": True,
            "job_id": job.id,
            "status": job.status,
            "result_url":
                job.result_url,
            "skipped": True,
        }


    try:

        completed_job = (
            execute_job(
                job
            )
        )

        return {
            "ok": True,
            "job_id":
                completed_job.id,

            "status":
                completed_job.status,

            "result_url":
                completed_job.result_url,

            "attempts":
                completed_job.attempts,
        }


    except Exception as exc:

        # execute_job already updates the
        # GenerationJob state to failed.
        #
        # Video jobs also refund their reserved internal credits.
        # The refund is idempotent by reference so the same job cannot
        # receive the same refund twice.

        refund_error = ""

        try:

            _refund_failed_video_job(
                job
            )

        except Exception as refund_exc:

            refund_error = (
                f" Credit refund failed: "
                f"{refund_exc}"
            )

        return {
            "ok": False,
            "job_id": job.id,
            "status": (
                GenerationJob
                .STATUS_FAILED
            ),
            "error": (
                str(exc)[:4000]
                + refund_error
            )[:4000],
        }

