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

from django.contrib.auth import get_user_model
from django.db import transaction

from projects.models import (
    Project,
    Scene,
    StoryboardImage,
)

from generations.image_services import (
    generate_storyboard_image,
)

from generations.video_services import (
    generate_scene_video,
)

from generations.models import (
    VideoGeneration,
)

from assets_app.models import (
    Asset,
)


print()
print("=" * 104)
print("GINGAO V40D.1 - VIDEO GENERATION + ASSET VALIDATION")
print("=" * 104)


User = get_user_model()

user = User.objects.get(
    username="Samuelmba"
)


projects_before = (
    Project.objects
    .filter(owner=user)
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


def static_to_path(url):

    if not url:
        return None

    prefix = "/static/"

    if not url.startswith(prefix):
        return None

    return (
        ROOT
        / "static"
        / url[len(prefix):]
    )


try:

    with transaction.atomic():

        # ====================================================
        # TEMP PROJECT
        # ====================================================

        project = Project.objects.create(
            owner=user,
            title="V40D1 TEMP",
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
            script="Temporary service validation.",
            image_prompt="Temporary storyboard mock.",
            video_prompt="Temporary video mock.",
            duration_seconds=3,
        )


        storyboard = (
            StoryboardImage.objects.create(
                scene=scene,
                status="pending",
                image_url="",
            )
        )


        # ====================================================
        # IMAGE SERVICE
        # ====================================================

        generate_storyboard_image(
            storyboard=storyboard,
            user=user,
            provider_code="mock",
        )


        storyboard.refresh_from_db()


        assert storyboard.status == "ready"
        assert storyboard.image_url


        image_path = static_to_path(
            storyboard.image_url
        )

        if image_path:
            created_files.append(
                image_path
            )


        print()
        print("STORYBOARD URL:")
        print(
            storyboard.image_url
        )


        # ====================================================
        # VIDEO SERVICE
        # ====================================================

        result = generate_scene_video(
            scene=scene,
            user=user,
            provider_code="mock",
        )


        print()
        print("=" * 104)
        print("VIDEO SERVICE RESULT")
        print("=" * 104)


        print(
            "Result type:",
            type(result).__name__,
        )

        print(
            "Result URL:",
            result["url"],
        )

        print(
            "Provider:",
            result["provider"],
        )

        print(
            "Is mock:",
            result["is_mock"],
        )


        generation = result[
            "generation"
        ]

        asset = result[
            "asset"
        ]


        assert generation is not None, (
            "VideoGeneration was not created."
        )

        assert asset is not None, (
            "Video Asset was not created."
        )


        generation.refresh_from_db()
        asset.refresh_from_db()


        # ====================================================
        # EXACT URL CHECK
        # ====================================================

        service_url = result["url"]

        generation_url = (
            generation.output_url
        )

        asset_url = (
            asset.source_url
        )


        print()
        print("=" * 104)
        print("URL CONSISTENCY")
        print("=" * 104)

        print(
            "Service URL:",
            service_url,
        )

        print(
            "Generation.output_url:",
            generation_url,
        )

        print(
            "Asset.source_url:",
            asset_url,
        )


        assert service_url, (
            "Service returned empty URL."
        )

        assert (
            generation_url
            == service_url
        ), (
            "VideoGeneration.output_url "
            "does not match service URL."
        )

        assert (
            asset_url
            == service_url
        ), (
            "Asset.source_url "
            "does not match service URL."
        )


        # ====================================================
        # VIDEO GENERATION RECORD
        # ====================================================

        print()
        print("=" * 104)
        print("VIDEO GENERATION")
        print("=" * 104)


        print(
            "ID:",
            generation.id,
        )

        print(
            "Status:",
            generation.status,
        )

        print(
            "Scene ID:",
            generation.scene_id,
        )

        print(
            "Project ID:",
            generation.project_id,
        )

        print(
            "Output URL:",
            generation.output_url,
        )


        assert (
            generation.status
            == "ready"
        )

        assert (
            generation.scene_id
            == scene.id
        )

        assert (
            generation.project_id
            == project.id
        )


        # ====================================================
        # ASSET RECORD
        # ====================================================

        print()
        print("=" * 104)
        print("VIDEO ASSET")
        print("=" * 104)


        print(
            "Asset ID:",
            asset.id,
        )

        print(
            "Owner:",
            asset.owner_id,
        )

        print(
            "Kind:",
            asset.kind,
        )

        print(
            "Name:",
            asset.name,
        )

        print(
            "Source URL:",
            asset.source_url,
        )


        assert (
            asset.owner_id
            == user.id
        )

        assert (
            asset.kind
            == "video"
        )

        assert (
            asset.source_url
            == service_url
        )


        # ====================================================
        # PHYSICAL VIDEO MOCK
        # ====================================================

        video_path = static_to_path(
            service_url
        )

        assert video_path is not None

        assert (
            video_path.exists()
        ), (
            f"Video mock file missing: "
            f"{video_path}"
        )


        created_files.append(
            video_path
        )


        print()
        print(
            "Physical video file:",
            video_path,
        )

        print(
            "Physical file exists: OK"
        )


        # ====================================================
        # IMPORTANT DIFFERENCE
        # ====================================================

        assert (
            service_url
            != storyboard.image_url
        ), (
            "Video URL unexpectedly equals "
            "storyboard image URL."
        )


        print()
        print(
            "VIDEO URL != IMAGE URL: OK"
        )

        print(
            "SERVICE URL = GENERATION URL: OK"
        )

        print(
            "SERVICE URL = ASSET URL: OK"
        )

        print(
            "VIDEO GENERATION RECORD: OK"
        )

        print(
            "VIDEO ASSET RECORD: OK"
        )


        # ====================================================
        # ROLLBACK
        # ====================================================

        transaction.set_rollback(
            True
        )


finally:

    deleted = 0

    for path in set(
        created_files
    ):

        try:

            if (
                path
                and path.exists()
            ):

                path.unlink()

                deleted += 1

        except Exception as exc:

            print(
                "Cleanup warning:",
                exc,
            )


    print()
    print("=" * 104)
    print("FILE CLEANUP")
    print("=" * 104)

    print(
        "Temporary files deleted:",
        deleted,
    )


# ============================================================
# VERIFY DB ROLLBACK
# ============================================================

projects_after = (
    Project.objects
    .filter(owner=user)
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
print("DATABASE ROLLBACK")
print("=" * 104)


print(
    "Projects:",
    projects_before,
    "->",
    projects_after,
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
    projects_before
    == projects_after
)

assert (
    videos_before
    == videos_after
)

assert (
    assets_before
    == assets_after
)


print()
print("DATABASE ROLLBACK: OK")
print("NO TEMP PROJECT LEFT: OK")
print("NO TEMP VIDEO LEFT: OK")
print("NO TEMP ASSET LEFT: OK")

print()
print("=" * 104)
print("AUDIT_VIDEO_ASSET_FLOW_V40D1: OK")
print("=" * 104)
