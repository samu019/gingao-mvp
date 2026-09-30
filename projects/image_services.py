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
    scene_text = (
        f"{scene.script} "
        f"{scene.image_prompt}"
    ).lower()

    # -------------------------------------------------------------------------
    # Semantic entity groups
    # -------------------------------------------------------------------------

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

    non_human_characters = [
        character
        for character in characters
        if character not in human_characters
    ]

    character_context = " ".join(
        f"{character.name}: {character.visual_prompt}"
        for character in characters
    )

    non_human_context = " ".join(
        f"{character.name}: {character.visual_prompt}"
        for character in non_human_characters
    )

    # -------------------------------------------------------------------------
    # Vehicle scene detection
    # -------------------------------------------------------------------------

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

    interior_vehicle_markers = (
        "driver's seat",
        "inside the car",
        "car interior",
        "vehicle interior",
        "steering wheel",
        "at the wheel",
        "al volante",
        "interior del coche",
        "dentro del coche",
        "se sienta al volante",
    )

    exterior_driving_markers = (
        "driving",
        "drives",
        "driven",
        "turning onto",
        "turns onto",
        "moving along",
        "moving through",
        "travelling",
        "traveling",
        "avenue",
        "road",
        "street",
        "conduce",
        "conduciendo",
        "circula",
        "circulando",
        "toma una avenida",
        "avenida",
        "carretera",
        "calle",
    )

    has_vehicle = any(
        marker in scene_text
        for marker in vehicle_markers
    )

    is_interior_vehicle_scene = any(
        marker in scene_text
        for marker in interior_vehicle_markers
    )

    is_exterior_driving_scene = (
        has_vehicle
        and not is_interior_vehicle_scene
        and any(
            marker in scene_text
            for marker in exterior_driving_markers
        )
    )

    # =========================================================================
    # GINGAO_EXTERIOR_DRIVING_COMPOSITION_V56E
    #
    # Exterior driving shots intentionally hide the cabin.
    # This avoids FLUX inventing passengers or duplicate faces.
    # The original image_prompt is NOT reused here because it may explicitly
    # request a visible driver through the window.
    # =========================================================================

    if is_exterior_driving_scene:
        return (
            "VERTICAL 9:16 CINEMATIC PHOTOREALISTIC EXTERIOR "
            "DRIVING SHOT.\n\n"

            "EXTERIOR VEHICLE COMPOSITION ? HIGHEST PRIORITY:\n"
            "Show the vehicle from outside while it is moving through "
            "the environment described by the story. "
            "Use a cinematic front three-quarter, side, rear "
            "three-quarter, or tracking angle. "
            "The vehicle itself is the visual subject of this shot. "
            "The cabin must NOT be visually readable. "
            "Use realistic dark glass, natural reflections, city-light "
            "reflections, angle, framing, or motion to obscure the cabin. "
            "No human face may be visible through the windshield or windows. "
            "No human body, head, passenger, driver, silhouette, or occupant "
            "may be visible anywhere inside the vehicle. "
            "Do not depict the protagonist through the glass in this shot. "
            "Do not show faces reflected in the windows. "
            "Do not create additional occupants.\n\n"

            f"NARRATIVE ACTION:\n{scene.script}\n\n"

            "NON-HUMAN VISUAL CONTINUITY:\n"
            f"{non_human_context}\n\n"

            "Preserve the exact recurring vehicle make, model, color, "
            "body style, wheels, headlights, proportions and realistic "
            "appearance established in previous scenes. "
            "Preserve the established location and nighttime atmosphere. "
            "The shot must communicate vehicle movement without showing "
            "any person inside the cabin. "
            "Vertical 9:16 composition."
        )

    # -------------------------------------------------------------------------
    # Interior / ordinary vehicle protection
    # -------------------------------------------------------------------------

    single_vehicle_occupant_guard = ""

    if (
        len(human_characters) == 1
        and has_vehicle
    ):
        # GINGAO_SINGLE_VEHICLE_OCCUPANT_GUARD_V56C
        # GINGAO_POSITIVE_SINGLE_OCCUPANT_COMPOSITION_V56D
        single_vehicle_occupant_guard = (
            "\n\nSINGLE VEHICLE OCCUPANT COMPOSITION:\n"
            "Exactly one human exists inside the entire vehicle: "
            "the protagonist in the driver's seat. "
            "Show the protagonist clearly seated behind the steering wheel. "
            "The front passenger seat is clearly empty. "
            "All rear seats are clearly empty. "
            "There is exactly one human face visible in or through the car. "
            "Use a driver-side camera angle whenever possible. "
            "Keep passenger-side and rear windows dark or naturally tinted "
            "if needed to prevent false occupants. "
            "The cabin contains one human silhouette only. "
            "No passenger, companion, second driver or background occupant "
            "may appear inside the vehicle."
        )

    single_person_guard = ""

    if is_interior_vehicle_scene:
        # GINGAO_SINGLE_PERSON_INTERIOR_GUARD_V56A
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
