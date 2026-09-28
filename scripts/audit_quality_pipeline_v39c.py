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

from generations.final_services import (
    get_project_output_spec,
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
        (720, 1280, 25, "veryfast"),

    ("9:16", "standard"):
        (1080, 1920, 20, "medium"),

    ("9:16", "premium"):
        (1440, 2560, 17, "slow"),

    ("16:9", "fast"):
        (1280, 720, 25, "veryfast"),

    ("16:9", "standard"):
        (1920, 1080, 20, "medium"),

    ("16:9", "premium"):
        (2560, 1440, 17, "slow"),

    ("1:1", "fast"):
        (720, 720, 25, "veryfast"),

    ("1:1", "standard"):
        (1080, 1080, 20, "medium"),

    ("1:1", "premium"):
        (1440, 1440, 17, "slow"),

    ("4:5", "fast"):
        (720, 900, 25, "veryfast"),

    ("4:5", "standard"):
        (1080, 1350, 20, "medium"),

    ("4:5", "premium"):
        (1440, 1800, 17, "slow"),
}


print()
print("=" * 96)
print("GINGAO V39C QUALITY PIPELINE AUDIT")
print("=" * 96)


for (
    ratio,
    quality
), expected_values in expected.items():

    spec = get_project_output_spec(
        DummyProject(
            ratio,
            quality,
        )
    )

    actual = (
        spec["width"],
        spec["height"],
        spec["crf"],
        spec["preset"],
    )

    print(
        f"{quality:8} "
        f"{ratio:4} -> "
        f"{spec['width']}x{spec['height']} "
        f"CRF={spec['crf']} "
        f"preset={spec['preset']}"
    )

    assert (
        actual
        == expected_values
    )


fallback = get_project_output_spec(
    DummyProject(
        "bad-ratio",
        "bad-quality",
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
    fallback["crf"],
    fallback["preset"],
) == (
    1080,
    1920,
    20,
    "medium",
)


source = (
    ROOT
    / "generations"
    / "final_services.py"
).read_text(
    encoding="utf-8",
    errors="ignore",
)

assert (
    "QUALITY_RENDER_PROFILES"
    in source
)

assert (
    "preset=preset"
    in source
)

assert (
    "crf=crf"
    in source
)

assert (
    '"render_crf": result["crf"]'
    in source
)

assert (
    '"render_preset": result["preset"]'
    in source
)


print()
print("ECONOMICA QUALITY PROFILE: OK")
print("STANDARD QUALITY PROFILE: OK")
print("PREMIUM QUALITY PROFILE: OK")
print("ALL ASPECT RATIOS: OK")
print("CRF PROPAGATION: OK")
print("PRESET PROPAGATION: OK")
print("EXPORT METADATA: OK")
print("INVALID VALUE FALLBACK: OK")

print()
print("=" * 96)
print("AUDIT_QUALITY_PIPELINE_V39C: OK")
print("=" * 96)
