import logging
import unicodedata

from django.db import transaction

from .models import (
    Character,
    StoryboardImage,
)
from .story_ai import analyze_story


# GINGAO_DYNAMIC_ENTITY_PREP_V52C
logger = logging.getLogger(__name__)


def _project_text(project):
    # GINGAO_STORY_SOURCE_PRIORITY_V52C1
    story_idea = (
        getattr(project, "story_idea", "")
        or ""
    ).strip()

    if story_idea:
        return story_idea

    parts = [
        project.title or "",
    ]

    parts.extend(
        scene.script
        for scene in project.scenes.all()
    )

    return " ".join(
        str(part).strip()
        for part in parts
        if part and str(part).strip()
    )


def _normalize_name(value):
    value = unicodedata.normalize(
        "NFKD",
        value or "",
    )

    value = "".join(
        ch
        for ch in value
        if not unicodedata.combining(ch)
    )

    return value.lower().strip()


def _coerce_entity_type(value):
    value = (
        str(value or "")
        .strip()
        .lower()
    )

    mapping = {
        "character": "character",
        "person": "person",
        "human": "human_character",
        "human_character": "human_character",
        "animal": "animal",
        "vehicle": "vehicle",
        "location": "location",
        "building": "building",
        "object": "object",
        "machine": "machine",
        "creature": "creature",
        "food": "food",
        "product": "product",
        "prop": "prop",
        "main_character": "main_character",
    }

    return mapping.get(
        value,
        value or "main_character",
    )


def _default_entity_data(project):
    return [
        {
            "name": "Protagonista",
            "type": "main_character",
            "description":
                "Entidad principal del proyecto.",
            "prompt":
                "Main subject of the story, visually clear, "
                "repeatable and consistent across all scenes.",
        }
    ]


def _entities_from_story_ai(project):
    idea = _project_text(project)

    if not idea:
        return []

    analysis = analyze_story(idea)

    result = []
    seen = set()

    for item in analysis.get("entities", []):
        name = str(
            item.get("name", "")
        ).strip()

        entity_type = _coerce_entity_type(
            item.get("type")
        )

        description = str(
            item.get("description", "")
        ).strip()

        visual_prompt = str(
            item.get("visual_prompt", "")
        ).strip()

        if not name or not visual_prompt:
            continue

        key = _normalize_name(name)

        if key in seen:
            continue

        seen.add(key)

        result.append(
            {
                "name": name,
                "type": entity_type,
                "description":
                    description
                    or f"{name} entity in the story.",
                "prompt": visual_prompt,
            }
        )

    return result


def _unique_character_data(project):
    try:
        entities = _entities_from_story_ai(
            project
        )

        if entities:
            return entities

    except Exception as exc:
        logger.exception(
            (
                "Story entity analysis failed "
                "project_id=%s "
                "error_type=%s "
                "error=%s"
            ),
            getattr(project, "id", None),
            type(exc).__name__,
            str(exc),
        )

    return _default_entity_data(project)


@transaction.atomic
def prepare_characters(project):
    definitions = _unique_character_data(project)

    project.characters.all().delete()

    result = []

    for data in definitions:
        result.append(
            Character.objects.create(
                project=project,
                name=data["name"],
                character_type=data["type"],
                description=data["description"],
                visual_prompt=data["prompt"],
            )
        )

    return result


@transaction.atomic
def prepare_storyboard(project):

    characters = list(
        project.characters.all()
    )

    if not characters:
        characters = prepare_characters(project)

    character_context = " ".join(
        f"{character.name}: {character.visual_prompt}"
        for character in characters
    )

    storyboard = []

    for scene in project.scenes.all():

        prompt = (
            f"{scene.image_prompt}\n\n"
            f"CHARACTER CONSISTENCY:\n"
            f"{character_context}\n\n"
            "Keep every recurring character exactly consistent "
            "across all scenes. Vertical 9:16 composition."
        )

        # GINGAO_STORYBOARD_INVALIDATION_V52D
        # A rebuilt visual structure invalidates the previous
        # scene image logically. The physical file is preserved.
        item, _ = StoryboardImage.objects.update_or_create(
            scene=scene,
            defaults={
                "prompt": prompt,
                "image_url": "",
                "status": "pending",
            }
        )

        storyboard.append(item)

    project.status = "images"
    project.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    return storyboard
