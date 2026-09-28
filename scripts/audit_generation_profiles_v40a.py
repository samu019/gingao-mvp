import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT)
    )

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)

import django
django.setup()

from generations.generation_profiles import (
    get_generation_profile,
)


class DummyProject:

    def __init__(
        self,
        ratio,
        quality,
    ):
        self.aspect_ratio = ratio
        self.quality_tier = quality


expected = {

    ("9:16", "fast"):
        (576, 1024),

    ("16:9", "fast"):
        (1024, 576),

    ("1:1", "fast"):
        (768, 768),

    ("4:5", "fast"):
        (768, 960),


    ("9:16", "standard"):
        (768, 1365),

    ("16:9", "standard"):
        (1365, 768),

    ("1:1", "standard"):
        (1024, 1024),

    ("4:5", "standard"):
        (1024, 1280),


    ("9:16", "premium"):
        (1024, 1820),

    ("16:9", "premium"):
        (1820, 1024),

    ("1:1", "premium"):
        (1440, 1440),

    ("4:5", "premium"):
        (1440, 1800),
}


print()
print("=" * 96)
print("GINGAO V40A GENERATION PROFILE AUDIT")
print("=" * 96)


for key, dimensions in expected.items():

    ratio, quality = key

    spec = get_generation_profile(
        DummyProject(
            ratio,
            quality,
        )
    )

    actual = (
        spec["width"],
        spec["height"],
    )

    print(
        f"{quality:8} "
        f"{ratio:4} -> "
        f"{actual[0]}x{actual[1]}"
    )

    assert (
        actual == dimensions
    )


fallback = get_generation_profile(
    DummyProject(
        "bad",
        "bad",
    )
)

assert (
    fallback["aspect_ratio"]
    == "9:16"
)

assert (
    fallback["quality_tier"]
    == "standard"
)

assert (
    fallback["width"],
    fallback["height"],
) == (
    768,
    1365,
)


image_source = (
    ROOT
    / "generations"
    / "image_providers.py"
).read_text(
    encoding="utf-8",
    errors="ignore"
)

video_source = (
    ROOT
    / "generations"
    / "video_providers.py"
).read_text(
    encoding="utf-8",
    errors="ignore"
)


assert (
    "get_generation_profile"
    in image_source
)

assert (
    '"width": width'
    in image_source
)

assert (
    '"height": height'
    in image_source
)

assert (
    "width * height"
    in image_source
    or
    "width\n                    * height"
    in image_source
)

assert (
    'width="{width}"'
    in image_source
)

assert (
    'height="{height}"'
    in image_source
)


assert (
    "get_generation_profile"
    in video_source
)

assert (
    'width="{width}"'
    in video_source
)

assert (
    'height="{height}"'
    in video_source
)


print()
print("ECONOMICA GENERATION SIZE: OK")
print("STANDARD GENERATION SIZE: OK")
print("PREMIUM GENERATION SIZE: OK")
print("ALL ASPECT RATIOS: OK")
print("MOCK IMAGE FORMAT: OK")
print("FAL IMAGE FORMAT: OK")
print("FAL COST USES REAL PIXELS: OK")
print("MOCK VIDEO FORMAT: OK")
print("INVALID VALUE FALLBACK: OK")

print()
print("=" * 96)
print("AUDIT_GENERATION_PROFILES_V40A: OK")
print("=" * 96)
