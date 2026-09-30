from django.conf import settings
from django.db import models
class Project(models.Model):
    STATUS=[('draft','Draft'),('script','Script'),('images','Images'),('rendering','Rendering'),('complete','Complete'),('failed','Failed')]
    owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='projects')
    title=models.CharField(max_length=160)

    # GINGAO_STORY_IDEA_PERSISTENCE_V52A
    story_idea = models.TextField(
        blank=True,
    )

    template_code=models.CharField(max_length=64,default='fruit_story')
    status=models.CharField(max_length=16,choices=STATUS,default='draft')
    target_duration_seconds=models.PositiveIntegerField(default=15)

    # GINGAO_PROJECT_OPTIONS_V37
    aspect_ratio = models.CharField(
        max_length=10,
        default="9:16",
    )

    voice_enabled = models.BooleanField(
        default=True,
    )

    # GINGAO_VOICE_PRESET_V49A
    voice_preset = models.CharField(
        max_length=40,
        default="warm_female",
    )

    quality_tier = models.CharField(
        max_length=20,
        default="standard",
    )

    estimated_credit_cost = models.PositiveIntegerField(
        default=0,
    )

    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
class Scene(models.Model):
    project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='scenes')
    position=models.PositiveIntegerField()
    script=models.TextField(blank=True)
    image_prompt=models.TextField(blank=True)
    video_prompt=models.TextField(blank=True)
    duration_seconds=models.PositiveIntegerField(default=3)
    class Meta:
        ordering=['position']
        unique_together=[('project','position')]



class Character(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="characters",
    )

    name = models.CharField(
        max_length=120
    )

    character_type = models.CharField(
        max_length=80,
        blank=True
    )

    description = models.TextField(
        blank=True
    )

    visual_prompt = models.TextField(
        blank=True
    )

    reference_image_url = models.URLField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.project_id}: {self.name}"


class StoryboardImage(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("ready", "Ready"),
        ("failed", "Failed"),
    ]

    scene = models.OneToOneField(
        Scene,
        on_delete=models.CASCADE,
        related_name="storyboard_image",
    )

    prompt = models.TextField()

    image_url = models.URLField(
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"Storyboard scene {self.scene_id}"
