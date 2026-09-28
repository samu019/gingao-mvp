from pathlib import Path
import os
import sys
import io

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)

import django
django.setup()

from django.db import transaction

from projects.models import Project, Scene
from assets_app.models import Asset

from generations.audio_services import (
    generate_project_audio,
    project_narration_text,
    project_duration,
)

import generations.audio_providers as audio_providers


print()
print("=" * 108)
print("GINGAO V45C - SIMULATED ELEVENLABS SERVICE PIPELINE")
print("=" * 108)


base_projects = Project.objects.count()
base_assets = Asset.objects.count()

print()
print("BASE COUNTS")
print("-" * 108)
print("Projects:", base_projects)
print("Assets:", base_assets)


# =============================================================================
# FAKE HTTP RESPONSE
# =============================================================================

FAKE_MP3 = (
    b"ID3"
    + b"\x04\x00\x00\x00\x00\x00\x00"
    + b"GINGAO_V45C_FAKE_MP3"
    + (b"\x00" * 512)
)

calls = []


class FakeResponse:

    def __init__(
        self,
        data,
    ):
        self.data = data

    def read(self):
        return self.data

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ):
        return False


def fake_urlopen(
    request,
    timeout=None,
):

    calls.append({
        "request": request,
        "timeout": timeout,
    })

    return FakeResponse(
        FAKE_MP3
    )


# =============================================================================
# TRANSACTIONAL TEST
# =============================================================================

generated_path = None

try:

    with transaction.atomic():

        # ---------------------------------------------------------------------
        # Create Project using only fields that exist.
        # ---------------------------------------------------------------------

        project_fields = {
            field.name
            for field
            in Project._meta.fields
        }

        project_kwargs = {}

        if "owner" in project_fields:
            project_kwargs["owner_id"] = 3

        if "user" in project_fields:
            project_kwargs["user_id"] = 3

        if "title" in project_fields:
            project_kwargs[
                "title"
            ] = "V45C TEMP TTS PROJECT"

        if "name" in project_fields:
            project_kwargs[
                "name"
            ] = "V45C TEMP TTS PROJECT"

        if (
            "target_duration_seconds"
            in project_fields
        ):
            project_kwargs[
                "target_duration_seconds"
            ] = 5

        if (
            "duration_seconds"
            in project_fields
        ):
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
            ] = True

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


        # ---------------------------------------------------------------------
        # Create Scene using existing fields only.
        # ---------------------------------------------------------------------

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
                "Hola. Esta es una prueba de "
                "narracion real simulada de Gingao."
            )

        if "video_prompt" in scene_fields:
            scene_kwargs[
                "video_prompt"
            ] = "V45C temporary scene"

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


        # ---------------------------------------------------------------------
        # Validate narration input.
        # ---------------------------------------------------------------------

        narration = project_narration_text(
            project
        )

        duration = project_duration(
            project
        )

        print()
        print("PROJECT AUDIO INPUT")
        print("-" * 108)
        print("Narration:", narration)
        print("Duration:", duration)

        assert narration
        assert "prueba" in narration.lower()
        assert duration == 5

        print(
            "PROJECT NARRATION TEXT: OK"
        )

        print(
            "PROJECT DURATION: OK"
        )


        # ---------------------------------------------------------------------
        # Fake credentials and HTTP transport.
        # ---------------------------------------------------------------------

        old_provider = os.environ.get(
            "GINGAO_AUDIO_PROVIDER"
        )

        old_key = os.environ.get(
            "ELEVENLABS_API_KEY"
        )

        old_voice = os.environ.get(
            "GINGAO_ELEVENLABS_VOICE_ID"
        )

        old_model = os.environ.get(
            "GINGAO_ELEVENLABS_MODEL"
        )

        old_urlopen = (
            audio_providers
            .urllib
            .request
            .urlopen
        )


        os.environ[
            "GINGAO_AUDIO_PROVIDER"
        ] = "elevenlabs"

        os.environ[
            "ELEVENLABS_API_KEY"
        ] = "V45C_FAKE_KEY"

        os.environ[
            "GINGAO_ELEVENLABS_VOICE_ID"
        ] = "V45C_FAKE_VOICE"

        os.environ[
            "GINGAO_ELEVENLABS_MODEL"
        ] = "eleven_multilingual_v2"


        audio_providers.urllib.request.urlopen = (
            fake_urlopen
        )


        try:

            result = generate_project_audio(
                project=project,
                user=project.owner,
                provider_code="elevenlabs",
            )

        finally:

            audio_providers.urllib.request.urlopen = (
                old_urlopen
            )

            if old_provider is None:
                os.environ.pop(
                    "GINGAO_AUDIO_PROVIDER",
                    None,
                )
            else:
                os.environ[
                    "GINGAO_AUDIO_PROVIDER"
                ] = old_provider

            if old_key is None:
                os.environ.pop(
                    "ELEVENLABS_API_KEY",
                    None,
                )
            else:
                os.environ[
                    "ELEVENLABS_API_KEY"
                ] = old_key

            if old_voice is None:
                os.environ.pop(
                    "GINGAO_ELEVENLABS_VOICE_ID",
                    None,
                )
            else:
                os.environ[
                    "GINGAO_ELEVENLABS_VOICE_ID"
                ] = old_voice

            if old_model is None:
                os.environ.pop(
                    "GINGAO_ELEVENLABS_MODEL",
                    None,
                )
            else:
                os.environ[
                    "GINGAO_ELEVENLABS_MODEL"
                ] = old_model


        # ---------------------------------------------------------------------
        # Service result.
        # ---------------------------------------------------------------------

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
            "Duration:",
            result["duration"],
        )

        print(
            "Is mock:",
            result["is_mock"],
        )


        assert (
            result["provider"]
            == "elevenlabs"
        )

        assert (
            result["url"]
            .endswith(
                ".mp3"
            )
        )

        assert (
            result["duration"]
            == 5
        )

        assert (
            result["is_mock"]
            is False
        )


        print(
            "SERVICE PROVIDER: OK"
        )

        print(
            "SERVICE MP3 URL: OK"
        )

        print(
            "SERVICE DURATION: OK"
        )


        # ---------------------------------------------------------------------
        # HTTP request inspection.
        # ---------------------------------------------------------------------

        assert len(
            calls
        ) == 1


        request = calls[0][
            "request"
        ]

        request_url = (
            request.full_url
        )

        request_headers = dict(
            request.header_items()
        )

        request_body = (
            request.data
            .decode(
                "utf-8"
            )
        )


        print()
        print("FAKE ELEVENLABS REQUEST")
        print("-" * 108)

        print(
            "URL:",
            request_url,
        )

        print(
            "Timeout:",
            calls[0]["timeout"],
        )

        print(
            "Body:",
            request_body,
        )


        assert (
            "/v1/text-to-speech/"
            in request_url
        )

        assert (
            "V45C_FAKE_VOICE"
            in request_url
        )

        assert (
            "output_format="
            in request_url
        )

        assert (
            "xi-api-key"
            in {
                key.lower()
                for key
                in request_headers
            }
        )

        assert (
            "eleven_multilingual_v2"
            in request_body
        )

        assert (
            "narracion"
            in request_body.lower()
        )


        print(
            "TTS ENDPOINT: OK"
        )

        print(
            "VOICE ID PROPAGATION: OK"
        )

        print(
            "MODEL PROPAGATION: OK"
        )

        print(
            "NARRATION TEXT PROPAGATION: OK"
        )

        print(
            "API KEY HEADER: OK"
        )


        # ---------------------------------------------------------------------
        # Physical MP3.
        # ---------------------------------------------------------------------

        prefix = "/static/"

        assert result[
            "url"
        ].startswith(
            prefix
        )


        generated_path = (
            ROOT
            / "static"
            / result["url"][
                len(prefix):
            ]
        )


        print()
        print("PHYSICAL AUDIO")
        print("-" * 108)

        print(
            "Path:",
            generated_path,
        )


        assert (
            generated_path.exists()
        )

        assert (
            generated_path.stat().st_size
            == len(
                FAKE_MP3
            )
        )

        content = (
            generated_path
            .read_bytes()
        )

        assert (
            content
            == FAKE_MP3
        )


        print(
            "PHYSICAL MP3 EXISTS: OK"
        )

        print(
            "PHYSICAL MP3 CONTENT: OK"
        )


        # ---------------------------------------------------------------------
        # Asset.
        # ---------------------------------------------------------------------

        asset = result[
            "asset"
        ]

        if asset is None:

            raise RuntimeError(
                "Audio Asset was not created."
            )


        print()
        print("AUDIO ASSET")
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
            "AUDIO ASSET RECORD: OK"
        )

        print(
            "ASSET URL: OK"
        )

        print()
        print(
            "SERVICE URL = ASSET URL: OK"
        )

        print(
            "NO REAL NETWORK REQUEST EXECUTED: OK"
        )

        print(
            "NO PAID TTS CALL EXECUTED: OK"
        )


        transaction.set_rollback(
            True
        )


finally:

    if (
        generated_path is not None
        and generated_path.exists()
    ):

        try:
            generated_path.unlink()
        except OSError:
            pass


# =============================================================================
# ROLLBACK
# =============================================================================

final_projects = Project.objects.count()
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
    final_assets
    == base_assets
)


print()
print(
    "DATABASE ROLLBACK: OK"
)

print(
    "TEMP MP3 CLEANUP: OK"
)

print()
print("=" * 108)
print("GINGAO V45C: OK")
print("=" * 108)
