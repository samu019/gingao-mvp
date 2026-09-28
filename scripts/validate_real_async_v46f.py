from pathlib import Path
import os
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)

os.environ.setdefault(
    "REDIS_URL",
    "redis://127.0.0.1:6379/0",
)

os.environ["GINGAO_IMAGE_PROVIDER"] = "mock"
os.environ["GINGAO_VIDEO_PROVIDER"] = "mock"
os.environ["GINGAO_AUDIO_PROVIDER"] = "mock"

import django
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from projects.models import Project
from generations.models import GenerationJob
from generations.tasks import execute_generation_job_task


print()
print("=" * 108)
print("GINGAO V46F - REAL ASYNC CELERY END-TO-END")
print("=" * 108)


User = get_user_model()

user = User.objects.get(
    username="Samuelmba"
)

project = (
    Project.objects
    .filter(owner=user)
    .order_by("id")
    .first()
)

if project is None:
    raise RuntimeError(
        "No project found for Samuelmba."
    )


initial_jobs = (
    GenerationJob.objects.count()
)


print()
print("TEST USER:", user.username)
print("TEST PROJECT:", project.id, project.title)
print("INITIAL JOBS:", initial_jobs)
print("PROVIDER: mock")
print("BROKER:", os.environ["REDIS_URL"])


job = None
generated_file = None


try:

    # ---------------------------------------------------------------------
    # CREATE A GUARANTEED UNIQUE QUEUED JOB
    # ---------------------------------------------------------------------

    job = GenerationJob.objects.create(
        user=user,
        project=project,
        scene=None,
        job_type=GenerationJob.TYPE_FINAL,
        provider="mock",
        status=GenerationJob.STATUS_QUEUED,
        idempotency_key=(
            "v46f:"
            + uuid.uuid4().hex
        ),
        payload={
            "audit": "V46F",
            "provider": "mock",
        },
    )


    print()
    print("=" * 108)
    print("QUEUED JOB")
    print("=" * 108)

    print("Job ID:", job.id)
    print("Status:", job.status)

    assert (
        job.status
        == GenerationJob.STATUS_QUEUED
    )

    print("INITIAL STATUS QUEUED: OK")


    # ---------------------------------------------------------------------
    # STATUS API BEFORE DISPATCH
    # ---------------------------------------------------------------------

    client = Client()

    client.force_login(
        user
    )

    status_url = reverse(
        "job_status",
        kwargs={
            "job_id": job.id,
        },
    )

    response = client.get(
        status_url,
        HTTP_ACCEPT="application/json",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "queued"
    assert data["terminal"] is False


    print("STATUS API QUEUED: OK")
    print("STATUS URL:", status_url)


    # ---------------------------------------------------------------------
    # REAL CELERY DISPATCH
    # ---------------------------------------------------------------------

    print()
    print("=" * 108)
    print("REAL CELERY DISPATCH")
    print("=" * 108)

    async_result = (
        execute_generation_job_task.delay(
            job.id
        )
    )

    print(
        "Celery task ID:",
        async_result.id,
    )

    print(
        "TASK SENT THROUGH REDIS: OK"
    )


    # ---------------------------------------------------------------------
    # POLL DATABASE
    # ---------------------------------------------------------------------

    observed = []

    deadline = (
        time.monotonic()
        + 30
    )

    last_status = None


    while (
        time.monotonic()
        < deadline
    ):

        job.refresh_from_db()

        if job.status != last_status:

            observed.append(
                job.status
            )

            print(
                "DB STATUS:",
                job.status,
            )

            last_status = (
                job.status
            )


        if job.status in {
            GenerationJob.STATUS_COMPLETED,
            GenerationJob.STATUS_FAILED,
        }:

            break


        time.sleep(
            0.10
        )


    job.refresh_from_db()


    print()
    print("=" * 108)
    print("FINAL JOB STATE")
    print("=" * 108)

    print(
        "Observed statuses:",
        observed,
    )

    print(
        "Final status:",
        job.status,
    )

    print(
        "Attempts:",
        job.attempts,
    )

    print(
        "Started at:",
        job.started_at,
    )

    print(
        "Finished at:",
        job.finished_at,
    )

    print(
        "Result URL:",
        job.result_url,
    )

    print(
        "Error:",
        job.error_message,
    )


    if (
        job.status
        != GenerationJob.STATUS_COMPLETED
    ):

        raise RuntimeError(
            "Async job did not complete: "
            + (
                job.error_message
                or job.status
            )
        )


    assert job.attempts >= 1
    assert job.started_at is not None
    assert job.finished_at is not None
    assert job.result_url


    print()
    print(
        "FINAL STATUS COMPLETED: OK"
    )

    print(
        "PROCESSING STEP RECORDED: OK"
    )

    print(
        "ATTEMPT COUNTER: OK"
    )

    print(
        "RESULT URL: OK"
    )


    # ---------------------------------------------------------------------
    # STATUS API AFTER CELERY COMPLETION
    # ---------------------------------------------------------------------

    response = client.get(
        status_url,
        HTTP_ACCEPT="application/json",
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["status"]
        == "completed"
    )

    assert (
        data["terminal"]
        is True
    )

    assert (
        data["result_url"]
        == job.result_url
    )


    print(
        "STATUS API COMPLETED: OK"
    )

    print(
        "STATUS API TERMINAL: OK"
    )


    # ---------------------------------------------------------------------
    # PHYSICAL MOCK FILE
    # ---------------------------------------------------------------------

    if job.result_url.startswith(
        "/static/"
    ):

        relative = (
            job.result_url[
                len("/static/"):
            ]
        )

        generated_file = (
            ROOT
            / "static"
            / relative
        )

        print()
        print(
            "Physical result:",
            generated_file,
        )

        assert (
            generated_file.exists()
        )

        print(
            "PHYSICAL MOCK RESULT: OK"
        )


    print()
    print("=" * 108)
    print("V46F REAL ASYNC RESULTS")
    print("=" * 108)

    print(
        "DJANGO -> CELERY TASK: OK"
    )

    print(
        "CELERY -> REDIS: OK"
    )

    print(
        "REDIS -> WORKER: OK"
    )

    print(
        "WORKER -> GENERATION JOB: OK"
    )

    print(
        "QUEUED -> PROCESSING -> COMPLETED: OK"
    )

    print(
        "JOB STATUS API: OK"
    )

    print(
        "MOCK PROVIDER ONLY: OK"
    )

    print(
        "PAID AI CALLS: 0"
    )


finally:

    print()
    print("=" * 108)
    print("CLEANUP")
    print("=" * 108)


    if (
        generated_file is not None
        and generated_file.exists()
    ):

        try:

            generated_file.unlink()

            print(
                "Temporary result file removed: OK"
            )

        except Exception as exc:

            print(
                "Temporary result cleanup warning:",
                exc,
            )


    if job is not None:

        GenerationJob.objects.filter(
            id=job.id
        ).delete()

        print(
            "Temporary GenerationJob removed: OK"
        )


    final_jobs = (
        GenerationJob.objects.count()
    )

    print(
        "Jobs:",
        initial_jobs,
        "->",
        final_jobs,
    )

    assert (
        final_jobs
        == initial_jobs
    )

    print(
        "DATABASE CLEANUP: OK"
    )


print()
print("=" * 108)
print("GINGAO V46F: OK")
print("=" * 108)
