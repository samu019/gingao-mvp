from pathlib import Path
import os
import sys
import re

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)

import django
django.setup()

from generations.tasks import (
    execute_generation_job_task,
)

from generations.models import (
    GenerationJob,
)


print()
print("=" * 104)
print("GINGAO V46C - CELERY DISPATCH AUDIT")
print("=" * 104)


tasks_file = (
    ROOT
    / "generations"
    / "tasks.py"
)

views_file = (
    ROOT
    / "projects"
    / "views.py"
)


tasks_text = tasks_file.read_text(
    encoding="utf-8",
)

views_text = views_file.read_text(
    encoding="utf-8",
)


assert (
    "execute_generation_job_task"
    in tasks_text
)

assert (
    "GenerationJob.objects"
    in tasks_text
)

assert (
    "execute_job("
    in tasks_text
)


print(
    "CELERY TASK EXISTS: OK"
)

print(
    "TASK LOADS GENERATION JOB: OK"
)

print(
    "TASK CALLS JOB RUNNER: OK"
)


assert hasattr(
    execute_generation_job_task,
    "delay",
)

assert hasattr(
    execute_generation_job_task,
    "apply_async",
)


print(
    "CELERY TASK DELAY API: OK"
)


delay_count = len(
    re.findall(
        r"execute_generation_job_task"
        r"\.delay\s*\(",
        views_text,
    )
)

direct_retry_count = len(
    re.findall(
        r"execute_job\s*\(\s*"
        r"new_job\s*\)",
        views_text,
        flags=re.MULTILINE,
    )
)


print(
    "ASYNC DISPATCH CALLS:",
    delay_count,
)

print(
    "DIRECT RETRY EXECUTE CALLS:",
    direct_retry_count,
)


assert delay_count >= 1

assert direct_retry_count == 0


print(
    "VIEW USES ASYNC CELERY DISPATCH: OK"
)

print(
    "DIRECT RETRY EXECUTION REMOVED: OK"
)


# =============================================================================
# NO BROKER CALL TEST
# =============================================================================
#
# Do NOT call .delay() here because that would try Redis.
# Instead inspect task registration only.

task_name = (
    execute_generation_job_task.name
)

assert (
    task_name
    == "gingao.execute_generation_job"
)


print(
    "TASK NAME REGISTERED: OK"
)

print()
print(
    "NO CELERY JOB WAS SENT"
)

print(
    "NO REDIS CONNECTION WAS REQUIRED"
)

print()
print("=" * 104)
print("AUDIT_CELERY_DISPATCH_V46C: OK")
print("=" * 104)
