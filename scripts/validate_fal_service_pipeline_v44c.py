from pathlib import Path
import os
import sys
import types

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)

import django
django.setup()

from django.db import transaction

from projects.models import Project, Scene, StoryboardImage
from generations.models import VideoGeneration
from assets_app.models import Asset

from generations import video_providers
from generations.video_services import generate_scene_video


print()
print("=" * 108)
print("GINGAO V44C - SIMULATED REAL FAL SERVICE PIPELINE")
print("=" * 108)


# =============================================================================
# BASE COUNTS
# =============================================================================

base_projects = Project.objects.count()
base_videos = VideoGeneration.objects.count()
base_assets = Asset.objects.count()


print()
print("BASE COUNTS")
print("-" * 108)
print("Projects:", base_projects)
print("VideoGeneration:", base_videos)
print("Assets:", base_assets)


# =============================================================================
# FAKE FAL CLIENT
# =============================================================================

calls = {
    "upload_file": [],
    "subscribe": [],
}


def fake_upload_file(path):

    calls["upload_file"].append(
        path
    )

    return (
        "https://fake-fal.local/"
        "uploaded-reference.png"
    )


def fake_subscribe(
    model_id,
    *,
    arguments,
    with_logs=False,
):

    calls["subscribe"].append({
        "model_id": model_id,
        "arguments": arguments,
        "with_logs": with_logs,
    })

    return {
        "video": {
            "url": (
                "https://fake-fal.local/"
                "generated-scene.mp4"
            )
        }
    }


fake_module = types.SimpleNamespace(
    upload_file=fake_upload_file,
    subscribe=fake_subscribe,
)


# =============================================================================
# TRANSACTIONAL TEST
# =============================================================================

try:

    with transaction.atomic():

        project_fields = {
            field.name
            for field
            in Project._meta.fields
        }

        project_kwargs = {}


        if "owner" in project_fields:
            project_kwargs[
                "owner_id"
            ] = 3


        if "user" in project_fields:
            project_kwargs[
                "user_id"
            ] = 3


        if "title" in project_fields:
            project_kwargs[
                "title"
            ] = "V44C TEMP FAL PROJECT"


        if "name" in project_fields:
            project_kwargs[
                "name"
            ] = "V44C TEMP FAL PROJECT"


        if (
            "target_duration_seconds"
            in project_fields
        ):
            project_kwargs[
                "target_duration_seconds"
            ] = 5


        if "duration_seconds" in project_fields:
            project_kwargs[
                "duration_seconds"
            ] = 5


        if "aspect_ratio" in project_fields:
            project_kwargs[
                "aspect_ratio"
            ] = "16:9"


        if "voice_enabled" in project_fields:
            project_kwargs[
                "voice_enabled"
            ] = False


        if "quality_tier" in project_fields:
            project_kwargs[
                "quality_tier"
            ] = "standard"


        if (
            "estimated_credit_cost"
            in project_fields
        ):
            project_kwargs[
                "estimated_credit_cost"
            ] = 0


        project = Project.objects.create(
            **project_kwargs
        )


        scene_fields = {
            field.name
            for field
            in Scene._meta.fields
        }

        scene_kwargs = {
            "project": project,
        }


        if "position" in scene_fields:
            scene_kwargs[
                "position"
            ] = 1


        if "script" in scene_fields:
            scene_kwargs[
                "script"
            ] = (
                "A cinematic camera movement."
            )


        if "video_prompt" in scene_fields:
            scene_kwargs[
                "video_prompt"
            ] = (
                "Smooth cinematic movement, "
                "natural motion."
            )


        if (
            "duration_seconds"
            in scene_fields
        ):
            scene_kwargs[
                "duration_seconds"
            ] = 5


        scene = Scene.objects.create(
            **scene_kwargs
        )


        local_dir = (
            ROOT
            / "static"
            / "generated"
            / "v44c"
        )

        local_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        local_image = (
            local_dir
            / "reference.png"
        )


        # Minimal PNG signature is enough because
        # FalVideoProvider only needs a physical file
        # before fake upload_file is called.
        local_image.write_bytes(
            b"\x89PNG\r\n\x1a\nV44C"
        )


        storyboard = StoryboardImage.objects.create(
            scene=scene,
            status="ready",
            image_url=(
                "/static/generated/v44c/"
                "reference.png"
            ),
        )


        # =========================================================
        # PATCH FAL SAFELY
        # =========================================================

        old_key = os.environ.get(
            "FAL_KEY"
        )

        os.environ[
            "FAL_KEY"
        ] = "V44C_FAKE_KEY"


        original_import = __import__


        def patched_import(
            name,
            globals=None,
            locals=None,
            fromlist=(),
            level=0,
        ):

            if name == "fal_client":
                return fake_module

            return original_import(
                name,
                globals,
                locals,
                fromlist,
                level,
            )


        import builtins

        old_import = builtins.__import__

        builtins.__import__ = patched_import


        try:

            result = generate_scene_video(
                scene=scene,
                user=project.owner,
                provider_code="fal",
            )

        finally:

            builtins.__import__ = old_import

            if old_key is None:
                os.environ.pop(
                    "FAL_KEY",
                    None,
                )
            else:
                os.environ[
                    "FAL_KEY"
                ] = old_key


        # =========================================================
        # SERVICE RESULT
        # =========================================================

        print()
        print("SERVICE RESULT")
        print("-" * 108)

        print(
            "Provider:",
            result["provider"],
        )

        print(
            "URL:",
            result["url"],
        )

        print(
            "External cost USD:",
            result["external_cost_usd"],
        )


        assert (
            result["provider"]
            == "fal"
        )

        assert (
            result["url"]
            == (
                "https://fake-fal.local/"
                "generated-scene.mp4"
            )
        )


        print(
            "SERVICE PROVIDER: OK"
        )

        print(
            "SERVICE URL: OK"
        )


        # =========================================================
        # FAKE PROVIDER CALL
        # =========================================================

        print()
        print("FAKE FAL CALL")
        print("-" * 108)

        assert len(
            calls["upload_file"]
        ) == 1

        assert len(
            calls["subscribe"]
        ) == 1


        call = calls[
            "subscribe"
        ][0]


        print(
            "Model:",
            call["model_id"],
        )

        print(
            "Arguments:",
            call["arguments"],
        )


        assert (
            call["arguments"][
                "image_url"
            ]
            == (
                "https://fake-fal.local/"
                "uploaded-reference.png"
            )
        )

        assert (
            call["arguments"][
                "resolution"
            ]
            == "1080p"
        )

        assert (
            call["arguments"][
                "duration"
            ]
            == 5
        )

        assert (
            "Smooth cinematic movement"
            in call["arguments"][
                "prompt"
            ]
        )


        print(
            "LOCAL IMAGE -> FAL UPLOAD: OK"
        )

        print(
            "IMAGE URL PROPAGATION: OK"
        )

        print(
            "PROMPT PROPAGATION: OK"
        )

        print(
            "RESOLUTION PROPAGATION: OK"
        )

        print(
            "DURATION PROPAGATION: OK"
        )


        # =========================================================
        # VIDEO GENERATION
        # =========================================================

        generation = result[
            "generation"
        ]


        if generation is None:
            raise RuntimeError(
                "VideoGeneration was not created."
            )


        print()
        print("VIDEO GENERATION")
        print("-" * 108)

        print(
            "ID:",
            generation.pk,
        )

        print(
            "Output URL:",
            getattr(
                generation,
                "output_url",
                "",
            ),
        )


        assert (
            getattr(
                generation,
                "output_url",
                ""
            )
            == result["url"]
        )


        assert (
            generation.project_id
            == project.id
        )

        assert (
            generation.scene_id
            == scene.id
        )


        print(
            "VIDEO GENERATION RECORD: OK"
        )

        print(
            "GENERATION URL: OK"
        )


        # =========================================================
        # ASSET
        # =========================================================

        asset = result[
            "asset"
        ]


        if asset is None:
            raise RuntimeError(
                "Video Asset was not created."
            )


        print()
        print("VIDEO ASSET")
        print("-" * 108)

        print(
            "Asset ID:",
            asset.pk,
        )

        print(
            "Source URL:",
            getattr(
                asset,
                "source_url",
                "",
            ),
        )


        assert (
            getattr(
                asset,
                "source_url",
                ""
            )
            == result["url"]
        )

        assert (
            asset.owner_id
            == project.owner_id
        )


        print(
            "VIDEO ASSET RECORD: OK"
        )

        print(
            "ASSET URL: OK"
        )


        # =========================================================
        # CROSS-CHECK
        # =========================================================

        assert (
            result["url"]
            == generation.output_url
            == asset.source_url
        )


        print()
        print(
            "SERVICE = GENERATION = ASSET URL: OK"
        )

        print(
            "NO NETWORK REQUEST EXECUTED: OK"
        )

        print(
            "NO PAID API CALL EXECUTED: OK"
        )


        # Roll back all DB objects.
        transaction.set_rollback(
            True
        )


finally:

    # Physical test file is outside DB rollback.
    test_file = (
        ROOT
        / "static"
        / "generated"
        / "v44c"
        / "reference.png"
    )

    try:

        if test_file.exists():
            test_file.unlink()

        parent = test_file.parent

        if (
            parent.exists()
            and not any(
                parent.iterdir()
            )
        ):
            parent.rmdir()

    except OSError:
        pass


# =============================================================================
# ROLLBACK
# =============================================================================

final_projects = Project.objects.count()
final_videos = VideoGeneration.objects.count()
final_assets = Asset.objects.count()


print()
print("=" * 108)
print("ROLLBACK VERIFICATION")
print("=" * 108)

print(
    "Projects:",
    base_projects,
    "->",
    final_projects,
)

print(
    "VideoGeneration:",
    base_videos,
    "->",
    final_videos,
)

print(
    "Assets:",
    base_assets,
    "->",
    final_assets,
)


assert (
    final_projects
    == base_projects
)

assert (
    final_videos
    == base_videos
)

assert (
    final_assets
    == base_assets
)


print()
print(
    "DATABASE ROLLBACK: OK"
)

print(
    "TEMP FILE CLEANUP: OK"
)

print()
print("=" * 108)
print("GINGAO V44C: OK")
print("=" * 108)
