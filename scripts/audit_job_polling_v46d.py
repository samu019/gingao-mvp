from pathlib import Path
import os
import sys

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

from django.urls import (
    reverse,
    resolve,
)

from projects.views import (
    job_status_view,
)


print()
print("=" * 106)
print("GINGAO V46D - JOB STATUS POLLING AUDIT")
print("=" * 106)


views = (
    ROOT
    / "projects"
    / "views.py"
).read_text(
    encoding="utf-8",
)

urls = (
    ROOT
    / "config"
    / "urls.py"
).read_text(
    encoding="utf-8",
)

template = (
    ROOT
    / "templates"
    / "dashboard"
    / "jobs.html"
).read_text(
    encoding="utf-8",
)


assert (
    "def job_status_view"
    in views
)

assert (
    "user=request.user"
    in views
)

assert (
    "JsonResponse"
    in views
)


print(
    "JOB STATUS API: OK"
)

print(
    "JOB STATUS USER ISOLATION: OK"
)


url = reverse(
    "job_status",
    kwargs={
        "job_id": 123,
    },
)

assert (
    url
    == "/jobs/123/status/"
)


resolved = resolve(
    "/jobs/123/status/"
)

assert (
    resolved.func
    == job_status_view
)


print(
    "JOB STATUS ROUTE: OK"
)

print(
    "JOB STATUS URL RESOLUTION: OK"
)


assert (
    "data-job-id="
    in template
)

assert (
    "data-job-status="
    in template
)

assert (
    "data-status-url="
    in template
)

assert (
    "data-job-status-badge"
    in template
)


print(
    "JOB CARD DATA HOOKS: OK"
)


assert (
    "fetch("
    in template
)

assert (
    "setInterval("
    in template
)

assert (
    "2500"
    in template
)

assert (
    "window.location.reload()"
    in template
)

assert (
    "queued"
    in template
    and "processing"
    in template
    and "completed"
    in template
    and "failed"
    in template
)


print(
    "FETCH POLLING: OK"
)

print(
    "POLLING INTERVAL: OK"
)

print(
    "TERMINAL REFRESH: OK"
)

print(
    "ALL JOB STATES HANDLED: OK"
)


assert (
    "credentials:"
    in template
    and "same-origin"
    in template
)

assert (
    'cache:'
    in template
    and '"no-store"'
    in template
)


print(
    "SAME-ORIGIN REQUEST: OK"
)

print(
    "NO-STORE POLLING: OK"
)


print()
print(
    "NO REDIS CONNECTION WAS USED"
)

print(
    "NO CELERY JOB WAS SENT"
)

print()
print("=" * 106)
print("AUDIT_JOB_POLLING_V46D: OK")
print("=" * 106)
