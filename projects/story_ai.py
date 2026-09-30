# GINGAO_STORY_AI_PROVIDER_V52B

import json
import os

import requests


OPENAI_RESPONSES_URL = (
    "https://api.openai.com/v1/responses"
)


STORY_STRUCTURE_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                    },
                    "type": {
                        "type": "string",
                    },
                    "description": {
                        "type": "string",
                    },
                    "visual_prompt": {
                        "type": "string",
                    },
                },
                "required": [
                    "name",
                    "type",
                    "description",
                    "visual_prompt",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "entities",
    ],
    "additionalProperties": False,
}


def _extract_output_text(payload):
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue

        for content in item.get("content", []):
            if content.get("type") == "output_text":
                text = content.get("text", "")

                if text:
                    return text

    raise RuntimeError(
        "Story AI response did not contain output_text."
    )


def analyze_story_openai(
    idea,
    *,
    model=None,
    timeout=60,
):
    """
    Analyze a free-form story and identify recurring
    visual entities.

    This function does not mutate Django models and
    does not generate images, video or audio.
    """

    api_key = (
        os.environ
        .get(
            "OPENAI_API_KEY",
            "",
        )
        .strip()
    )

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured."
        )

    model = (
        model
        or os.environ.get(
            "GINGAO_STORY_MODEL",
            "gpt-5.6-luna",
        ).strip()
    )

    prompt = f"""
Analyze the following story idea for an AI video generation system.

Identify only recurring or visually important entities whose appearance
should remain consistent across scenes.

An entity may be ANY visually relevant thing, including:
- human
- fictional character
- animal
- food
- vehicle
- building
- location
- object
- machine
- creature
- product
- clothing
- prop

Do NOT assume the story is about fruit.
Do NOT create entities from incidental adjectives or colors.
Do NOT confuse a color with an object or character.

For each entity:
- name: concise human-readable name in the story language
- type: semantic category such as character, person, animal,
  vehicle, location, building, object, machine, creature, food
- description: concise identity and role
- visual_prompt: precise English prompt describing stable visual identity
  for repeated image generation

IMPORTANT SEMANTIC RULE:
Classify by narrative role before physical material.
If an entity behaves as an agent in the story ? for example it speaks,
decides, reacts emotionally, runs, helps, fights, protects, searches,
chases, performs actions intentionally, or acts as a protagonist ?
classify it as "character", even if physically it is a fruit, food,
animal, vehicle, machine, object, toy, product, or other thing.

Examples:
- a normal banana on a table -> food
- an anthropomorphic banana that talks or acts -> character
- a parked car -> vehicle
- a talking heroic car -> character
- a normal dog -> animal
- a detective dog that speaks and makes decisions -> character

Preserve the user's actual subjects.
Do not replace them with generic alternatives.

STORY IDEA:
{idea}
""".strip()

    payload = {
        "model": model,
        "store": False,
        "input": prompt,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "gingao_story_structure",
                "strict": True,
                "schema": STORY_STRUCTURE_SCHEMA,
            }
        },
    }

    response = requests.post(
        OPENAI_RESPONSES_URL,
        headers={
            "Authorization":
                f"Bearer {api_key}",
            "Content-Type":
                "application/json",
        },
        json=payload,
        timeout=timeout,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            "Story AI request failed "
            f"with HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    data = response.json()

    output_text = _extract_output_text(
        data
    )

    parsed = json.loads(
        output_text
    )

    if not isinstance(
        parsed.get("entities"),
        list,
    ):
        raise RuntimeError(
            "Story AI returned invalid entities."
        )

    return parsed


def analyze_story(
    idea,
    *,
    provider=None,
):
    provider = (
        provider
        or os.environ.get(
            "GINGAO_STORY_PROVIDER",
            "openai",
        )
    ).strip().lower()

    if provider == "openai":
        return analyze_story_openai(
            idea
        )

    raise RuntimeError(
        f"Unsupported story provider: {provider}"
    )



# =============================================================================
# GINGAO_GENERIC_SCENE_GENERATOR_V54B
# =============================================================================

STORY_SCENES_SCHEMA = {
    "type": "object",
    "properties": {
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                    },
                    "image_prompt": {
                        "type": "string",
                    },
                    "video_prompt": {
                        "type": "string",
                    },
                },
                "required": [
                    "script",
                    "image_prompt",
                    "video_prompt",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "scenes",
    ],
    "additionalProperties": False,
}


# =============================================================================
# GINGAO_NARRATION_BUDGET_V55B
# =============================================================================

def narration_word_budget(
    duration_seconds,
    scene_count,
):
    """
    Approximate spoken-word budget for natural short-form narration.

    Target: ~2.2 words/second.
    Hard ceiling: ~2.6 words/second.
    """

    try:
        duration = max(
            1,
            int(duration_seconds or 15),
        )
    except (
        TypeError,
        ValueError,
    ):
        duration = 15

    scene_count = max(
        1,
        int(scene_count or 1),
    )

    target_words = max(
        scene_count,
        round(duration * 2.2),
    )

    max_words = max(
        target_words,
        round(duration * 2.6),
    )

    return {
        "target_words": target_words,
        "max_words": max_words,
    }


def generate_story_scenes_openai(
    idea,
    *,
    scene_count,
    target_duration_seconds=15,
    aspect_ratio="9:16",
    template_code="custom",
    model=None,
    timeout=90,
):
    """
    Convert a free-form user story into concrete scene definitions.

    Does not mutate Django models.
    Does not generate images, video or audio.
    """

    idea = str(
        idea or ""
    ).strip()

    if not idea:
        raise RuntimeError(
            "Story idea is empty."
        )

    scene_count = max(
        1,
        int(scene_count or 1),
    )

    api_key = (
        os.environ
        .get(
            "OPENAI_API_KEY",
            "",
        )
        .strip()
    )

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured."
        )

    model = (
        model
        or os.environ.get(
            "GINGAO_STORY_MODEL",
            "gpt-5.6-luna",
        ).strip()
    )

    narration_budget = narration_word_budget(
        target_duration_seconds,
        scene_count,
    )

    target_words = narration_budget[
        "target_words"
    ]

    max_words = narration_budget[
        "max_words"
    ]

    prompt = f"""
You are the story-planning engine for Gingao,
an AI video generation platform.

Transform the user's story into exactly {scene_count} sequential scenes.

USER STORY:
{idea}

PROJECT:
- aspect ratio: {aspect_ratio}
- template hint: {template_code}
- total video duration: {target_duration_seconds} seconds
- target narration length: about {target_words} words total
- absolute narration ceiling: {max_words} words total

CRITICAL CONTENT RULES:

1. Preserve the user's actual subjects literally and semantically.

If the user describes:
- a banana, keep a banana;
- a carrot, keep a carrot;
- a human person, keep that human person;
- a woman with black hair and a red jacket, preserve those traits;
- a dog, preserve the dog;
- a BMW, preserve the BMW;
- a house, preserve the house.

Never replace a subject with a generic fruit, person,
animal, object, vehicle, or other substitute.

2. Do NOT assume the story is about fruit.
Do NOT assume it is a cartoon.
Do NOT assume it is about children.
Do NOT force anthropomorphism.
Do NOT invent arms, legs, faces or human behavior
unless the story requires them.

3. Respect every important visual attribute supplied by the user:
- age
- gender presentation
- hairstyle
- hair color
- skin appearance
- clothing
- accessories
- object type
- vehicle make/model/color
- architecture
- environment
- species
- colors
- materials
- relevant physical characteristics.

4. Keep recurring subjects visually consistent across scenes.

5. Each scene must describe what ACTUALLY happens at that moment.
Do not use vague placeholders such as:
- "the character reacts"
- "the protagonist acts"
- "the conflict increases"
when the concrete subjects/actions are known.

6. script:
Write ONLY the narration that can actually be spoken in the final video.
Use the SAME LANGUAGE as the user's story.

# GINGAO_SCRIPT_LANGUAGE_V55D
The script must stay entirely in that language.
Do not introduce unnecessary words from another language.
Foreign words are allowed only when they are proper names,
brand names, model names, places, or terms that must remain unchanged.

The combined word count of ALL script fields must target about
{target_words} words and MUST NOT exceed {max_words} words.

Keep narration concise, natural and useful.
Prefer one short sentence or phrase per scene.

Do NOT put image-generation instructions in script.
Do NOT put camera instructions in script.
Do NOT put animation instructions in script.
Do NOT copy image_prompt or video_prompt into script.

The script must describe the actual story event,
not technical generation instructions.

7. image_prompt:
Write a precise ENGLISH image-generation prompt for THAT scene.
Explicitly name every important subject visible in the scene.
Describe their concrete appearance, action, location and composition.
Preserve continuity with previous scenes.

Do not merely say:
"same character",
"main character",
"the protagonist",
"fruit character",
"the person".

State the actual identity and useful visual traits.

8. video_prompt:
Write a precise ENGLISH image-to-video motion prompt.
Describe only the movement, expressions, camera behavior,
environmental motion and action that should occur from the scene image.
Do not redesign subjects.

9. Follow the user's requested visual style if one is present.
If no visual style is specified, use a coherent cinematic treatment
appropriate to the actual story without changing subject identity.

10. The scenes must form one continuous story:
beginning -> development -> action/conflict -> resolution.

Return exactly {scene_count} scenes.
""".strip()

    payload = {
        "model": model,
        "store": False,
        "input": prompt,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "gingao_story_scenes",
                "strict": True,
                "schema": STORY_SCENES_SCHEMA,
            }
        },
    }

    response = requests.post(
        OPENAI_RESPONSES_URL,
        headers={
            "Authorization":
                f"Bearer {api_key}",
            "Content-Type":
                "application/json",
        },
        json=payload,
        timeout=timeout,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            "Story scene AI request failed "
            f"with HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    data = response.json()

    output_text = _extract_output_text(
        data
    )

    parsed = json.loads(
        output_text
    )

    scenes = parsed.get(
        "scenes"
    )

    if not isinstance(
        scenes,
        list,
    ):
        raise RuntimeError(
            "Story scene AI returned invalid scenes."
        )

    if len(scenes) != scene_count:
        raise RuntimeError(
            "Story scene AI returned "
            f"{len(scenes)} scenes; "
            f"expected {scene_count}."
        )

    result = []

    for index, scene in enumerate(
        scenes,
        start=1,
    ):
        if not isinstance(
            scene,
            dict,
        ):
            raise RuntimeError(
                f"Scene {index} is invalid."
            )

        script = str(
            scene.get(
                "script",
                "",
            )
        ).strip()

        image_prompt = str(
            scene.get(
                "image_prompt",
                "",
            )
        ).strip()

        video_prompt = str(
            scene.get(
                "video_prompt",
                "",
            )
        ).strip()

        if (
            not script
            or not image_prompt
            or not video_prompt
        ):
            raise RuntimeError(
                f"Scene {index} contains empty fields."
            )

        result.append(
            {
                "script": script,
                "image_prompt": image_prompt,
                "video_prompt": video_prompt,
            }
        )

    return result


def generate_story_scenes(
    idea,
    *,
    scene_count,
    target_duration_seconds=15,
    aspect_ratio="9:16",
    template_code="custom",
    provider=None,
):
    provider = (
        provider
        or os.environ.get(
            "GINGAO_STORY_PROVIDER",
            "openai",
        )
    ).strip().lower()

    if provider == "openai":
        return generate_story_scenes_openai(
            idea,
            scene_count=scene_count,
            target_duration_seconds=(
                target_duration_seconds
            ),
            aspect_ratio=aspect_ratio,
            template_code=template_code,
        )

    raise RuntimeError(
        f"Unsupported story provider: {provider}"
    )
