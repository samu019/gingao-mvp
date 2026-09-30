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
