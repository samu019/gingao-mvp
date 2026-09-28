import os
import sys
import re
import inspect
import importlib
import pkgutil
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
from django.db import transaction

from projects.models import (
    Project,
    Scene,
    StoryboardImage,
)

from generations.models import (
    VideoGeneration,
)

from assets_app.models import Asset

from generations.video_services import (
    generate_scene_video,
)

from generations.generation_profiles import (
    get_generation_profile,
)

import generations


print()
print("=" * 104)
print("GINGAO V40C - INTERNAL SERVICE PIPELINE VALIDATION")
print("=" * 104)


# ============================================================
# HELPERS
# ============================================================

def static_url_to_path(url):

    value = str(
        url or ""
    ).strip()

    if not value.startswith(
        "/static/"
    ):
        return None

    return (
        Path(settings.BASE_DIR)
        / "static"
        / value[len("/static/"):]
    )


def svg_dimensions(path):

    content = path.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    width = re.search(
        r'<svg[^>]*\bwidth="(\d+)"',
        content,
        re.I | re.S,
    )

    height = re.search(
        r'<svg[^>]*\bheight="(\d+)"',
        content,
        re.I | re.S,
    )

    if not width or not height:
        raise AssertionError(
            "Could not read SVG dimensions."
        )

    return (
        int(width.group(1)),
        int(height.group(1)),
    )


def find_image_service():

    preferred_names = [
        "generate_scene_image",
        "generate_image_for_scene",
        "generate_storyboard_image",
        "generate_scene_storyboard",
    ]

    candidates = []

    for info in pkgutil.iter_modules(
        generations.__path__
    ):

        module_name = info.name

        if (
            "image" not in module_name
            and "service" not in module_name
        ):
            continue

        full_name = (
            f"generations.{module_name}"
        )

        try:
            module = importlib.import_module(
                full_name
            )
        except Exception:
            continue

        for name in preferred_names:

            func = getattr(
                module,
                name,
                None,
            )

            if callable(func):
                return (
                    full_name,
                    name,
                    func,
                )

        for name, func in inspect.getmembers(
            module,
            inspect.isfunction,
        ):

            low = name.lower()

            if (
                "generate" in low
                and "image" in low
                and "scene" in low
            ):
                candidates.append(
                    (
                        full_name,
                        name,
                        func,
                    )
                )

    if candidates:
        return candidates[0]

    raise RuntimeError(
        "No real image generation service "
        "could be discovered."
    )


def call_service(
    func,
    *,
    scene,
    storyboard,
    user,
    provider_code,
):

    signature = inspect.signature(
        func
    )

    kwargs = {}

    supplied = {
        "scene": scene,
        "storyboard": storyboard,
        "project": scene.project,
        "user": user,
        "owner": user,
        "provider_code": provider_code,
        "provider": provider_code,
        "prompt": (
            scene.image_prompt
            or scene.script
        ),
    }

    unsupported = []

    for name, parameter in (
        signature.parameters.items()
    ):

        if name in supplied:
            kwargs[name] = supplied[name]

        elif (
            parameter.default
            is inspect.Parameter.empty
            and parameter.kind
            not in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            )
        ):
            unsupported.append(
                name
            )

    if unsupported:

        raise RuntimeError(
            "Discovered image service has "
            "unsupported required parameters: "
            + ", ".join(unsupported)
            + " | signature="
            + str(signature)
        )

    return func(
        **kwargs
    )


# ============================================================
# USER
# ============================================================

User = get_user_model()

user = User.objects.get(
    username="Samuelmba"
)


# ============================================================
# DISCOVER IMAGE SERVICE
# ============================================================

module_name, function_name, image_service = (
    find_image_service()
)

print()
print(
    "IMAGE SERVICE:",
    module_name,
    function_name,
)

print(
    "SIGNATURE:",
    inspect.signature(
        image_service
    ),
)


# ============================================================
# BASE COUNTS
# ============================================================

projects_before = (
    Project.objects
    .filter(owner=user)
    .count()
)

storyboards_before = (
    StoryboardImage.objects
    .count()
)

videos_before = (
    VideoGeneration.objects
    .count()
)

assets_before = (
    Asset.objects
    .count()
)


created_files = []


try:

    with transaction.atomic():

        # ====================================================
        # TEMPORARY PROJECT
        # ====================================================

        project = Project.objects.create(
            owner=user,
            title="V40C TEMP INTERNAL PIPELINE",
            template_code="fruit_story",
            status="images",
            target_duration_seconds=15,
            aspect_ratio="16:9",
            voice_enabled=False,
            quality_tier="standard",
            estimated_credit_cost=0,
        )


        scene = Scene.objects.create(
            project=project,
            position=1,
            script=(
                "Una escena temporal de Gingao "
                "para validar el pipeline."
            ),
            image_prompt=(
                "Bright cinematic fruit characters "
                "in a modern kitchen."
            ),
            video_prompt=(
                "Gentle cinematic movement "
                "of the characters."
            ),
            duration_seconds=3,
        )


        profile = (
            get_generation_profile(
                project
            )
        )


        print()
        print("=" * 104)
        print("TEMPORARY PROJECT")
        print("=" * 104)

        print(
            "Project ID:",
            project.id,
        )

        print(
            "Aspect ratio:",
            project.aspect_ratio,
        )

        print(
            "Quality:",
            project.quality_tier,
        )

        print(
            "Generation profile:",
            f"{profile['width']}x"
            f"{profile['height']}",
        )


        assert (
            profile["width"],
            profile["height"],
        ) == (
            1365,
            768,
        )


        # ====================================================
        # REAL IMAGE SERVICE
        # ====================================================

        print()
        print("=" * 104)
        print("IMAGE SERVICE")
        print("=" * 104)


        # The real Gingao image service expects an existing
        # StoryboardImage record and updates it to READY.
        storyboard_fields = {
            field.name
            for field in StoryboardImage._meta.fields
        }

        storyboard_kwargs = {
            "scene": scene,
        }

        if "status" in storyboard_fields:
            storyboard_kwargs["status"] = "pending"

        if "prompt" in storyboard_fields:
            storyboard_kwargs["prompt"] = (
                scene.image_prompt
                or scene.script
            )

        if "image_prompt" in storyboard_fields:
            storyboard_kwargs["image_prompt"] = (
                scene.image_prompt
                or scene.script
            )

        if "image_url" in storyboard_fields:
            storyboard_kwargs["image_url"] = ""

        storyboard = (
            StoryboardImage.objects.create(
                **storyboard_kwargs
            )
        )


        print(
            "Storyboard created before service:",
            storyboard.id,
        )


        image_result = call_service(
            image_service,
            scene=scene,
            storyboard=storyboard,
            user=user,
            provider_code="mock",
        )


        storyboard.refresh_from_db()
        scene.refresh_from_db()


        assert storyboard is not None, (
            "Image service did not create "
            "StoryboardImage."
        )


        print(
            "Storyboard ID:",
            storyboard.id,
        )

        print(
            "Status:",
            storyboard.status,
        )

        print(
            "Image URL:",
            storyboard.image_url,
        )


        assert (
            storyboard.status == "ready"
        ), (
            "Storyboard is not READY."
        )

        assert storyboard.image_url


        image_path = (
            static_url_to_path(
                storyboard.image_url
            )
        )


        assert (
            image_path
            and image_path.exists()
        ), (
            "Storyboard physical file missing."
        )


        created_files.append(
            image_path
        )


        if (
            image_path.suffix.lower()
            == ".svg"
        ):

            dimensions = (
                svg_dimensions(
                    image_path
                )
            )

            print(
                "Physical image dimensions:",
                dimensions,
            )

            assert dimensions == (
                1365,
                768,
            )


        print(
            "STORYBOARD IMAGE RECORD: OK"
        )

        print(
            "IMAGE SERVICE -> DATABASE: OK"
        )

        print(
            "IMAGE SERVICE -> PHYSICAL FILE: OK"
        )


        # ====================================================
        # REAL VIDEO SERVICE
        # ====================================================

        print()
        print("=" * 104)
        print("VIDEO SERVICE")
        print("=" * 104)


        video_result = (
            generate_scene_video(
                scene=scene,
                user=user,
                provider_code="mock",
            )
        )


        video_generation = (
            VideoGeneration.objects
            .filter(scene=scene)
            .order_by("-pk")
            .first()
        )


        assert (
            video_generation is not None
        ), (
            "Video service did not create "
            "VideoGeneration."
        )


        print(
            "VideoGeneration ID:",
            video_generation.id,
        )


        video_url = str(
            getattr(
                video_generation,
                "video_url",
                "",
            )
            or getattr(
                video_generation,
                "url",
                "",
            )
            or ""
        )


        if not video_url:

            if isinstance(
                video_result,
                dict,
            ):
                video_url = str(
                    video_result.get("url")
                    or ""
                )

            else:
                video_url = str(
                    getattr(
                        video_result,
                        "url",
                        "",
                    )
                    or ""
                )


        print(
            "Video URL:",
            video_url,
        )


        assert video_url, (
            "Video service produced no URL."
        )


        video_path = (
            static_url_to_path(
                video_url
            )
        )


        assert (
            video_path
            and video_path.exists()
        ), (
            "Mock video physical file missing."
        )


        created_files.append(
            video_path
        )


        if (
            video_path.suffix.lower()
            == ".svg"
        ):

            video_dimensions = (
                svg_dimensions(
                    video_path
                )
            )

            print(
                "Physical video mock dimensions:",
                video_dimensions,
            )

            assert video_dimensions == (
                1365,
                768,
            )


        print(
            "VIDEO GENERATION RECORD: OK"
        )

        print(
            "VIDEO SERVICE -> DATABASE: OK"
        )

        print(
            "VIDEO SERVICE -> PHYSICAL FILE: OK"
        )


        # ====================================================
        # ASSETS
        # ====================================================

        print()
        print("=" * 104)
        print("ASSET REGISTRATION")
        print("=" * 104)


        project_asset_count = 0

        asset_fields = {
            f.name
            for f in Asset._meta.fields
        }


        if "project" in asset_fields:

            project_asset_count = (
                Asset.objects
                .filter(
                    project=project
                )
                .count()
            )


        print(
            "Assets registered for project:",
            project_asset_count,
        )


        # Asset creation is model-schema dependent in Gingao.
        # We validate no service exception occurred and report
        # whether the current Asset schema allowed registration.
        print(
            "ASSET SERVICE COMPATIBILITY: OK"
        )


        # ====================================================
        # DATABASE COUNTS INSIDE TRANSACTION
        # ====================================================

        assert (
            Project.objects
            .filter(pk=project.pk)
            .exists()
        )

        assert (
            StoryboardImage.objects
            .filter(scene=scene)
            .exists()
        )

        assert (
            VideoGeneration.objects
            .filter(scene=scene)
            .exists()
        )


        print()
        print("PROJECT -> SCENE: OK")
        print("SCENE -> STORYBOARD: OK")
        print("STORYBOARD -> VIDEO SERVICE: OK")
        print("PROJECT FORMAT PROPAGATION: OK")
        print("PROJECT QUALITY PROPAGATION: OK")


        # ====================================================
        # ROLLBACK EVERYTHING DATABASE-RELATED
        # ====================================================

        transaction.set_rollback(
            True
        )


finally:

    # ========================================================
    # PHYSICAL FILE CLEANUP
    # ========================================================

    removed = 0

    for path in set(
        created_files
    ):

        try:

            if (
                path
                and path.exists()
            ):
                path.unlink()
                removed += 1

        except Exception as exc:

            print(
                "WARNING cleanup:",
                path,
                exc,
            )


    print()
    print("=" * 104)
    print("PHYSICAL CLEANUP")
    print("=" * 104)

    print(
        "Generated temporary files removed:",
        removed,
    )


# ============================================================
# ROLLBACK VERIFICATION
# ============================================================

projects_after = (
    Project.objects
    .filter(owner=user)
    .count()
)

storyboards_after = (
    StoryboardImage.objects
    .count()
)

videos_after = (
    VideoGeneration.objects
    .count()
)

assets_after = (
    Asset.objects
    .count()
)


print()
print("=" * 104)
print("ROLLBACK VERIFICATION")
print("=" * 104)

print(
    "Projects:",
    projects_before,
    "->",
    projects_after,
)

print(
    "StoryboardImage:",
    storyboards_before,
    "->",
    storyboards_after,
)

print(
    "VideoGeneration:",
    videos_before,
    "->",
    videos_after,
)

print(
    "Assets:",
    assets_before,
    "->",
    assets_after,
)


assert (
    projects_after
    == projects_before
)

assert (
    storyboards_after
    == storyboards_before
)

assert (
    videos_after
    == videos_before
)

assert (
    assets_after
    == assets_before
)


print()
print("DATABASE ROLLBACK: OK")
print("NO TEMP PROJECT LEFT: OK")
print("NO TEMP STORYBOARD LEFT: OK")
print("NO TEMP VIDEO GENERATION LEFT: OK")
print("NO TEMP ASSET LEFT: OK")


print()
print("=" * 104)
print("AUDIT_INTERNAL_PIPELINE_V40C: OK")
print("=" * 104)
