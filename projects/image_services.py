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


# =============================================================================
# GINGAO_SINGLE_STORYBOARD_PROMPT_REFRESH_V56B
# =============================================================================

def build_storyboard_prompt(
    scene,
    characters,
):
    character_context = " ".join(
        f"{character.name}: {character.visual_prompt}"
        for character in characters
    )

    scene_text = (
        f"{scene.script} "
        f"{scene.image_prompt}"
    ).lower()

    interior_vehicle_markers = (
        "driver",
        "driver's seat",
        "inside the car",
        "car interior",
        "vehicle interior",
        "steering wheel",
        "at the wheel",
        "al volante",
        "interior del coche",
        "dentro del coche",
    )

    single_person_guard = ""

    # GINGAO_SINGLE_VEHICLE_OCCUPANT_GUARD_V56C
    human_type_markers = {
        "character",
        "person",
        "human",
        "persona",
        "humano",
    }

    human_characters = [
        character
        for character in characters
        if (
            (character.character_type or "")
            .strip()
            .lower()
            in human_type_markers
        )
    ]

    vehicle_markers = (
        "car",
        "vehicle",
        "bmw",
        "automobile",
        "sedan",
        "coupe",
        "suv",
        "coche",
        "vehiculo",
        "veh?culo",
        "auto",
        "automovil",
        "autom?vil",
    )

    single_vehicle_occupant_guard = ""

    if (
        len(human_characters) == 1
        and any(
            marker in scene_text
            for marker in vehicle_markers
        )
    ):
        single_vehicle_occupant_guard = (
            "\n\nSINGLE VEHICLE OCCUPANT RULE:\n"
            "The protagonist is the only person in the vehicle. "
            "Do not add passengers or additional occupants. "
            "Do not invent another driver or companion. "
            "If the vehicle interior is visible through windows, "
            "only the protagonist may be visible inside. "
            "Do not show extra human faces, heads or bodies "
            "inside the vehicle."
        )

    if any(
        marker in scene_text
        for marker in interior_vehicle_markers
    ):
        single_person_guard = (
            "\n\nSINGLE PERSON INTERIOR RULE:\n"
            "Show exactly one visible human inside the vehicle. "
            "Only the intended driver may be visible. "
            "No passenger. No second person. No duplicate face. "
            "No duplicated head or body. "
            "No mirror or window reflection that looks like "
            "another human face. "
            "Do not create extra people in the cabin."
        )

    return (
        f"{scene.image_prompt}\n\n"
        f"CHARACTER CONSISTENCY:\n"
        f"{character_context}"
        f"{single_vehicle_occupant_guard}"
        f"{single_person_guard}\n\n"
        "Keep every recurring character exactly consistent "
        "across all scenes. Vertical 9:16 composition."
    )


@transaction.atomic
def prepare_storyboard(project):

    characters = list(
        project.characters.all()
    )

    if not characters:
        characters = prepare_characters(project)

    storyboard = []

    for scene in project.scenes.all():

        prompt = build_storyboard_prompt(
            scene,
            characters,
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
