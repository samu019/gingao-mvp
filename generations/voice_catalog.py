import os


DEFAULT_VOICE_PRESET = "warm_female"


VOICE_PRESETS = {
    "warm_female": {
        "label": "Femenina c?lida",
        "description": "Voz cercana, suave y natural.",
        "category": "female",
        "env": "GINGAO_VOICE_WARM_FEMALE_ID",
    },

    "young_female": {
        "label": "Femenina joven",
        "description": "Voz fresca, ligera y din?mica.",
        "category": "female",
        "env": "GINGAO_VOICE_YOUNG_FEMALE_ID",
    },

    "elegant_female": {
        "label": "Femenina elegante",
        "description": "Voz refinada para contenido premium.",
        "category": "female",
        "env": "GINGAO_VOICE_ELEGANT_FEMALE_ID",
    },

    "deep_male": {
        "label": "Masculina profunda",
        "description": "Voz grave con presencia narrativa.",
        "category": "male",
        "env": "GINGAO_VOICE_DEEP_MALE_ID",
    },

    "young_male": {
        "label": "Masculina joven",
        "description": "Voz moderna, clara y natural.",
        "category": "male",
        "env": "GINGAO_VOICE_YOUNG_MALE_ID",
    },

    "mature_male": {
        "label": "Masculina madura",
        "description": "Voz seria y con car?cter.",
        "category": "male",
        "env": "GINGAO_VOICE_MATURE_MALE_ID",
    },

    "cinematic": {
        "label": "Narrador cinematogr?fico",
        "description": "Voz pensada para historias y narraci?n.",
        "category": "narrator",
        "env": "GINGAO_VOICE_CINEMATIC_ID",
    },

    "energetic": {
        "label": "En?rgica",
        "description": "Voz expresiva para contenido din?mico.",
        "category": "dynamic",
        "env": "GINGAO_VOICE_ENERGETIC_ID",
    },
}


def normalize_voice_preset(value):
    code = str(
        value
        or ""
    ).strip().lower()

    if code in VOICE_PRESETS:
        return code

    return DEFAULT_VOICE_PRESET


def get_voice_preset(value):
    code = normalize_voice_preset(
        value
    )

    data = dict(
        VOICE_PRESETS[code]
    )

    data["code"] = code

    return data


def get_voice_id(
    preset_code,
):
    preset = get_voice_preset(
        preset_code
    )

    env_name = preset["env"]

    return (
        os.environ.get(
            env_name,
            ""
        )
        .strip()
    )


def available_voice_presets():
    return [
        {
            "code": code,
            **data,
            "configured": bool(
                os.environ.get(
                    data["env"],
                    ""
                ).strip()
            ),
        }
        for code, data
        in VOICE_PRESETS.items()
    ]
