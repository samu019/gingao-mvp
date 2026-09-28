GENERATION_PROFILES = {

    "fast": {
        "9:16": (576, 1024),
        "16:9": (1024, 576),
        "1:1": (768, 768),
        "4:5": (768, 960),
    },

    "standard": {
        "9:16": (768, 1365),
        "16:9": (1365, 768),
        "1:1": (1024, 1024),
        "4:5": (1024, 1280),
    },

    "premium": {
        "9:16": (1024, 1820),
        "16:9": (1820, 1024),
        "1:1": (1440, 1440),
        "4:5": (1440, 1800),
    },

}


def get_generation_profile(
    project
):
    ratio = str(
        getattr(
            project,
            "aspect_ratio",
            "9:16",
        )
        or "9:16"
    ).strip()

    if ratio not in {
        "9:16",
        "16:9",
        "1:1",
        "4:5",
    }:
        ratio = "9:16"


    quality = str(
        getattr(
            project,
            "quality_tier",
            "standard",
        )
        or "standard"
    ).strip().lower()

    if quality not in GENERATION_PROFILES:
        quality = "standard"


    width, height = (
        GENERATION_PROFILES[
            quality
        ][
            ratio
        ]
    )


    return {
        "aspect_ratio":
            ratio,

        "quality_tier":
            quality,

        "width":
            width,

        "height":
            height,
    }
