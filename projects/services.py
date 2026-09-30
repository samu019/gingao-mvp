from django.db import transaction

from .models import Scene
from .story_ai import generate_story_scenes


# GINGAO_GENERIC_SCRIPT_PIPELINE_V54B


def _clean(text):
    return " ".join(
        (text or "").split()
    ).strip()


def _duration_distribution(
    total,
    count,
):
    total = max(
        int(total or 15),
        count * 2,
    )

    base = total // count
    remainder = total % count

    values = []

    for index in range(count):

        value = (
            base
            + (
                1
                if index < remainder
                else 0
            )
        )

        values.append(
            max(
                2,
                value,
            )
        )

    return values


def _scene_count_for_duration(
    duration,
):
    """
    Keep short-form Gingao projects compact
    while providing enough visual beats.
    """

    duration = max(
        1,
        int(duration or 15),
    )

    if duration <= 20:
        return 6

    if duration <= 40:
        return 8

    return 10


def generate_project_script(
    project,
    idea,
):
    """
    Build script, image prompts and video prompts
    directly from the user's actual story.

    The external AI call happens BEFORE database mutation.
    """

    idea = _clean(
        idea
        or getattr(
            project,
            "story_idea",
            "",
        )
        or project.title
    )

    if not idea:
        raise RuntimeError(
            "No hay una idea de historia para generar el guion."
        )

    scene_count = (
        _scene_count_for_duration(
            project.target_duration_seconds
        )
    )

    definitions = (
        generate_story_scenes(
            idea,
            scene_count=scene_count,
            aspect_ratio=(
                project.aspect_ratio
                or "9:16"
            ),
            template_code=(
                project.template_code
                or "custom"
            ),
        )
    )

    if len(definitions) != scene_count:
        raise RuntimeError(
            "El generador devolvio una cantidad "
            "inesperada de escenas."
        )

    durations = (
        _duration_distribution(
            project.target_duration_seconds,
            scene_count,
        )
    )

    scenes = []

    with transaction.atomic():

        project.scenes.all().delete()

        for position, definition in enumerate(
            definitions,
            start=1,
        ):

            scene = Scene.objects.create(
                project=project,
                position=position,
                script=definition[
                    "script"
                ],
                image_prompt=definition[
                    "image_prompt"
                ],
                video_prompt=definition[
                    "video_prompt"
                ],
                duration_seconds=(
                    durations[
                        position - 1
                    ]
                ),
            )

            scenes.append(
                scene
            )

        project.status = "script"

        project.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    return scenes
