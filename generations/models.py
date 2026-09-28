import uuid
from django.db import models
from projects.models import Project, Scene
class VideoGeneration(models.Model):
    STATUS=[('queued','Queued'),('processing','Processing'),('complete','Complete'),('failed','Failed')]
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='generations')
    scene=models.ForeignKey(Scene,on_delete=models.SET_NULL,null=True,blank=True,related_name='generations')
    model_code=models.CharField(max_length=64,default='ltx-fast')
    resolution=models.CharField(max_length=16,default='720p')
    duration_seconds=models.PositiveIntegerField(default=3)
    estimated_credits=models.PositiveIntegerField(default=0)
    status=models.CharField(max_length=16,choices=STATUS,default='queued')
    provider_job_id=models.CharField(max_length=128,blank=True)
    output_url=models.URLField(blank=True)
    error_message=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)



# ============================================================
# Gingao Job Queue Core
# ============================================================

import uuid as _uuid

from django.conf import settings as _settings


class GenerationJob(models.Model):

    TYPE_IMAGE = "image"
    TYPE_VIDEO = "video"
    TYPE_AUDIO = "audio"
    TYPE_FINAL = "final"

    TYPE_CHOICES = [
        (TYPE_IMAGE, "Image"),
        (TYPE_VIDEO, "Video"),
        (TYPE_AUDIO, "Audio"),
        (TYPE_FINAL, "Final"),
    ]

    STATUS_QUEUED = "queued"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_QUEUED, "Queued"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    user = models.ForeignKey(
        _settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="gingao_jobs",
    )

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="generation_jobs",
    )

    scene = models.ForeignKey(
        "projects.Scene",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="generation_jobs",
    )

    job_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        db_index=True,
    )

    provider = models.CharField(
        max_length=80,
        default="mock",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_QUEUED,
        db_index=True,
    )

    idempotency_key = models.CharField(
        max_length=180,
        unique=True,
        default=_uuid.uuid4,
    )

    attempts = models.PositiveIntegerField(
        default=0
    )

    max_attempts = models.PositiveIntegerField(
        default=3
    )

    result_url = models.TextField(
        blank=True,
        default="",
    )

    error_message = models.TextField(
        blank=True,
        default="",
    )

    payload = models.JSONField(
        blank=True,
        default=dict,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    finished_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = [
            "-created_at"
        ]

    def __str__(self):
        return (
            f"{self.job_type} - "
            f"{self.project_id} - "
            f"{self.status}"
        )
