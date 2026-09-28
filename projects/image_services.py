from django.db import transaction

from .models import (
    Character,
    StoryboardImage,
)


FRUIT_LIBRARY = {
    "fresa": {
        "name": "Fresa",
        "type": "anthropomorphic_fruit",
        "description":
            "Fresa antropomorfica expresiva, energetica y simpatica.",
        "prompt":
            "Anthropomorphic strawberry character, vivid red strawberry "
            "body, green leafy crown, large expressive brown eyes, "
            "small red arms and legs, red shoes, friendly cinematic "
            "3D cartoon design, consistent proportions."
    },

    "strawberry": {
        "name": "Fresa",
        "type": "anthropomorphic_fruit",
        "description":
            "Fresa antropomorfica expresiva, energetica y simpatica.",
        "prompt":
            "Anthropomorphic strawberry character, vivid red strawberry "
            "body, green leafy crown, large expressive brown eyes, "
            "small red arms and legs, red shoes, friendly cinematic "
            "3D cartoon design, consistent proportions."
    },

    "platano": {
        "name": "Platano",
        "type": "anthropomorphic_fruit",
        "description":
            "Platano antropomorfico alto, protector y divertido.",
        "prompt":
            "Anthropomorphic yellow banana character, tall curved banana "
            "body, large expressive brown eyes, yellow arms and legs, "
            "yellow shoes, brave but humorous cinematic 3D cartoon design, "
            "consistent proportions."
    },

    "pl?tano": {
        "name": "Platano",
        "type": "anthropomorphic_fruit",
        "description":
            "Platano antropomorfico alto, protector y divertido.",
        "prompt":
            "Anthropomorphic yellow banana character, tall curved banana "
            "body, large expressive brown eyes, yellow arms and legs, "
            "yellow shoes, brave but humorous cinematic 3D cartoon design, "
            "consistent proportions."
    },

    "banana": {
        "name": "Platano",
        "type": "anthropomorphic_fruit",
        "description":
            "Platano antropomorfico alto, protector y divertido.",
        "prompt":
            "Anthropomorphic yellow banana character, tall curved banana "
            "body, large expressive brown eyes, yellow arms and legs, "
            "yellow shoes, brave but humorous cinematic 3D cartoon design, "
            "consistent proportions."
    },

    "naranja": {
        "name": "Naranja",
        "type": "anthropomorphic_fruit",
        "description":
            "Naranja antropomorfica alegre y expresiva.",
        "prompt":
            "Anthropomorphic orange fruit character, bright orange body, "
            "green leaf detail, expressive eyes, cartoon arms and legs, "
            "cinematic polished 3D design."
    },

    "manzana": {
        "name": "Manzana",
        "type": "anthropomorphic_fruit",
        "description":
            "Manzana antropomorfica expresiva.",
        "prompt":
            "Anthropomorphic red apple character, small green leaf, "
            "large expressive eyes, arms and legs, cinematic polished "
            "3D cartoon design."
    },
}


def _project_text(project):
    parts = [
        project.title or "",
    ]

    parts.extend(
        scene.script
        for scene in project.scenes.all()
    )

    return " ".join(parts).lower()


def _unique_character_data(project):
    text = _project_text(project)

    found = []
    names = set()

    if project.template_code == "fruit_story":

        for keyword, data in FRUIT_LIBRARY.items():
            if keyword in text and data["name"] not in names:
                found.append(data)
                names.add(data["name"])

        # Para historias de frutas donde no se detecta
        # ningun nombre concreto.
        if not found:
            found = [
                FRUIT_LIBRARY["fresa"],
                FRUIT_LIBRARY["platano"],
            ]

    elif project.template_code == "kids_story":

        found = [
            {
                "name": "Protagonista",
                "type": "kids_character",
                "description":
                    "Personaje principal amigable para una historia infantil.",
                "prompt":
                    "Friendly colorful 3D cartoon protagonist for children, "
                    "large expressive eyes, warm approachable design, "
                    "consistent body proportions."
            }
        ]

    elif project.template_code == "short_drama":

        found = [
            {
                "name": "Protagonista",
                "type": "human_character",
                "description":
                    "Personaje principal de la historia dramatica.",
                "prompt":
                    "Cinematic human protagonist, realistic consistent face, "
                    "natural proportions, emotionally expressive appearance."
            }
        ]

    else:

        found = [
            {
                "name": "Protagonista",
                "type": "main_character",
                "description":
                    "Personaje principal del proyecto.",
                "prompt":
                    "Main consistent cinematic character matching the story, "
                    "clear visual identity and repeatable appearance."
            }
        ]

    return found


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

        item, _ = StoryboardImage.objects.update_or_create(
            scene=scene,
            defaults={
                "prompt": prompt,
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
