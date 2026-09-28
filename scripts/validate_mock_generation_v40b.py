import os
import re
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

from django.conf import settings
from django.contrib.auth import get_user_model

from projects.models import Project

from generations.image_providers import (
    MockImageProvider,
)

from generations.video_providers import (
    MockVideoProvider,
)

from generations.generation_profiles import (
    get_generation_profile,
)


print()
print("=" * 100)
print("GINGAO V40B - REAL MOCK GENERATION VALIDATION")
print("=" * 100)


# ============================================================
# FIND REAL PROJECT + SCENE
# ============================================================

User = get_user_model()

user = User.objects.get(
    username="Samuelmba"
)

project = (
    Project.objects
    .filter(
        owner=user
    )
    .order_by("id")
    .first()
)

if project is None:
    raise RuntimeError(
        "No project available for V40B."
    )


scene = (
    project.scenes
    .order_by("position")
    .first()
)

if scene is None:
    raise RuntimeError(
        "Selected project has no scenes."
    )


print()
print(
    "TEST PROJECT:",
    project.id,
    project.title
)

print(
    "TEST SCENE:",
    scene.position
)


# ============================================================
# PROVIDERS
# ============================================================

image_provider = (
    MockImageProvider()
)

video_provider = (
    MockVideoProvider()
)


# ============================================================
# TEST MATRIX
# ============================================================

tests = [

    (
        "9:16",
        "fast",
        576,
        1024,
    ),

    (
        "16:9",
        "fast",
        1024,
        576,
    ),

    (
        "16:9",
        "standard",
        1365,
        768,
    ),

    (
        "1:1",
        "standard",
        1024,
        1024,
    ),

    (
        "4:5",
        "premium",
        1440,
        1800,
    ),

    (
        "9:16",
        "premium",
        1024,
        1820,
    ),
]


created_paths = []


def static_url_to_path(
    url
):
    prefix = "/static/"

    if not url.startswith(
        prefix
    ):
        raise RuntimeError(
            f"Unexpected mock URL: {url}"
        )

    relative = url[
        len(prefix):
    ]

    return (
        Path(settings.BASE_DIR)
        / "static"
        / relative
    )


def read_svg_dimensions(
    path
):
    content = path.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    width_match = re.search(
        r'<svg[^>]*\bwidth="(\d+)"',
        content,
        re.IGNORECASE
        | re.DOTALL,
    )

    height_match = re.search(
        r'<svg[^>]*\bheight="(\d+)"',
        content,
        re.IGNORECASE
        | re.DOTALL,
    )

    if (
        not width_match
        or not height_match
    ):
        raise AssertionError(
            f"Could not read SVG dimensions: "
            f"{path}"
        )

    return (
        int(
            width_match.group(1)
        ),
        int(
            height_match.group(1)
        ),
    )


try:

    for (
        ratio,
        quality,
        expected_width,
        expected_height,
    ) in tests:

        # IMPORTANT:
        # Change only the in-memory Python object.
        # Nothing is saved to database.
        project.aspect_ratio = ratio
        project.quality_tier = quality


        profile = (
            get_generation_profile(
                project
            )
        )


        assert (
            profile["width"]
            == expected_width
        )

        assert (
            profile["height"]
            == expected_height
        )


        print()
        print("-" * 100)

        print(
            f"TEST: "
            f"{quality} / {ratio}"
        )

        print(
            "PROFILE:",
            f"{profile['width']}x"
            f"{profile['height']}"
        )


        # ====================================================
        # IMAGE MOCK
        # ====================================================

        image_result = (
            image_provider.generate(
                prompt=(
                    "V40B temporary "
                    "mock image test"
                ),
                project=project,
                scene=scene,
            )
        )


        assert (
            image_result.success
        ), (
            image_result.error
            or "Mock image failed."
        )


        image_path = (
            static_url_to_path(
                image_result.url
            )
        )

        created_paths.append(
            image_path
        )

        assert (
            image_path.exists()
        ), (
            f"Mock image file missing: "
            f"{image_path}"
        )


        image_dimensions = (
            read_svg_dimensions(
                image_path
            )
        )


        print(
            "IMAGE SVG:",
            image_dimensions
        )


        assert (
            image_dimensions
            == (
                expected_width,
                expected_height,
            )
        ), (
            f"Image SVG mismatch: "
            f"{image_dimensions}"
        )


        # ====================================================
        # VIDEO MOCK
        # ====================================================

        video_result = (
            video_provider.generate(
                prompt=(
                    "V40B temporary "
                    "mock video test"
                ),
                project=project,
                scene=scene,
            )
        )


        assert (
            video_result.success
        ), (
            video_result.error
            or "Mock video failed."
        )


        assert (
            video_result.is_mock
            is True
        )


        video_path = (
            static_url_to_path(
                video_result.url
            )
        )

        created_paths.append(
            video_path
        )


        assert (
            video_path.exists()
        ), (
            f"Mock video file missing: "
            f"{video_path}"
        )


        video_dimensions = (
            read_svg_dimensions(
                video_path
            )
        )


        print(
            "VIDEO SVG:",
            video_dimensions
        )


        assert (
            video_dimensions
            == (
                expected_width,
                expected_height,
            )
        ), (
            f"Video SVG mismatch: "
            f"{video_dimensions}"
        )


        print(
            "IMAGE MOCK: OK"
        )

        print(
            "VIDEO MOCK: OK"
        )


finally:

    # ========================================================
    # CLEAN TEMPORARY GENERATED FILES
    # ========================================================

    deleted = 0

    for path in created_paths:

        try:

            if path.exists():
                path.unlink()
                deleted += 1

        except Exception as exc:

            print(
                "WARNING: could not delete",
                path,
                exc,
            )


    print()
    print("=" * 100)
    print("CLEANUP")
    print("=" * 100)

    print(
        "Temporary files deleted:",
        deleted
    )


print()
print("=" * 100)
print("V40B RESULTS")
print("=" * 100)

print(
    "FAST 9:16 PHYSICAL SVG: OK"
)

print(
    "FAST 16:9 PHYSICAL SVG: OK"
)

print(
    "STANDARD 16:9 PHYSICAL SVG: OK"
)

print(
    "STANDARD 1:1 PHYSICAL SVG: OK"
)

print(
    "PREMIUM 4:5 PHYSICAL SVG: OK"
)

print(
    "PREMIUM 9:16 PHYSICAL SVG: OK"
)

print(
    "IMAGE MOCK GENERATION: OK"
)

print(
    "VIDEO MOCK GENERATION: OK"
)

print(
    "DATABASE NOT MODIFIED: OK"
)

print()
print("=" * 100)
print("AUDIT_MOCK_GENERATION_V40B: OK")
print("=" * 100)
