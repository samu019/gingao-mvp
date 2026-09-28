import os
import re
import sys
import subprocess
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

import imageio_ffmpeg

from django.contrib.auth import get_user_model

from projects.models import Project

from generations.final_services import (
    create_local_final_mp4,
    get_project_video_timeline,
)


print()
print("=" * 100)
print("GINGAO V39B - REAL FFMPEG 16:9 / NO VOICE VALIDATION")
print("=" * 100)


User = get_user_model()

user = User.objects.get(
    username="Samuelmba"
)


# ============================================================
# FIND A USABLE PROJECT
# ============================================================

selected = None

print()
print("SEARCHING USABLE PROJECT")
print("-" * 100)


for project in (
    Project.objects
    .filter(owner=user)
    .order_by("id")
):

    timeline, duration = (
        get_project_video_timeline(
            project
        )
    )

    ready = [
        item
        for item in timeline
        if item.get("ready")
    ]

    print(
        f"Project {project.id}: "
        f"{project.title!r} | "
        f"scenes={len(timeline)} | "
        f"ready={len(ready)}"
    )

    if (
        timeline
        and len(ready) == len(timeline)
    ):
        selected = project
        break


if selected is None:
    raise RuntimeError(
        "No se encontro un proyecto con "
        "timeline completamente preparado "
        "para la prueba real."
    )


project = selected

print()
print(
    "SELECTED PROJECT:",
    project.id,
    project.title,
)


# ============================================================
# SAVE ORIGINAL SETTINGS
# ============================================================

original_ratio = project.aspect_ratio
original_voice = project.voice_enabled

print()
print("ORIGINAL SETTINGS")
print("-" * 100)

print(
    "Aspect ratio:",
    original_ratio
)

print(
    "Voice enabled:",
    original_voice
)


result = None
generated_path = None


try:

    # ========================================================
    # TEMPORARY TEST CONFIGURATION
    # ========================================================

    project.aspect_ratio = "16:9"
    project.voice_enabled = False

    project.save(
        update_fields=[
            "aspect_ratio",
            "voice_enabled",
            "updated_at",
        ]
    )


    project.refresh_from_db()


    print()
    print("TEMPORARY TEST SETTINGS")
    print("-" * 100)

    print(
        "Aspect ratio:",
        project.aspect_ratio
    )

    print(
        "Voice enabled:",
        project.voice_enabled
    )


    # ========================================================
    # REAL EXPORT
    # ========================================================

    print()
    print("=" * 100)
    print("RENDERING REAL MP4")
    print("=" * 100)


    result = create_local_final_mp4(
        project=project,
        user=user,
    )


    generated_path = Path(
        result["path"]
    )


    print()
    print(
        "URL:",
        result["url"]
    )

    print(
        "PATH:",
        generated_path
    )

    print(
        "RESULT WIDTH:",
        result["width"]
    )

    print(
        "RESULT HEIGHT:",
        result["height"]
    )

    print(
        "RESULT ASPECT:",
        result["aspect_ratio"]
    )

    print(
        "RESULT HAS AUDIO:",
        result["has_audio"]
    )


    assert (
        result["width"] == 1920
    ), result

    assert (
        result["height"] == 1080
    ), result

    assert (
        result["aspect_ratio"] == "16:9"
    ), result

    assert (
        result["has_audio"] is False
    ), (
        "El pipeline indico que el MP4 "
        "todavia tiene audio."
    )

    assert generated_path.exists(), (
        "El archivo final no existe."
    )


    # ========================================================
    # FFMPEG FILE INSPECTION
    # ========================================================

    ffmpeg = (
        imageio_ffmpeg
        .get_ffmpeg_exe()
    )


    process = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-i",
            str(generated_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


    metadata = (
        process.stderr
        or process.stdout
        or ""
    )


    print()
    print("=" * 100)
    print("FFMPEG MEDIA INSPECTION")
    print("=" * 100)


    relevant = []

    for line in metadata.splitlines():

        if (
            "Duration:" in line
            or "Video:" in line
            or "Audio:" in line
        ):
            relevant.append(
                line.strip()
            )


    for line in relevant:
        print(line)


    resolution_match = re.search(
        r"\b1920x1080\b",
        metadata,
    )

    has_audio_stream = bool(
        re.search(
            r"Stream\s+#[^\n]*Audio:",
            metadata,
            re.IGNORECASE,
        )
    )


    assert resolution_match, (
        "FFmpeg no detecto 1920x1080 "
        "en el MP4 real."
    )

    assert not has_audio_stream, (
        "FFmpeg detecto una pista de audio "
        "aunque voice_enabled=False."
    )


    print()
    print("REAL FILE RESOLUTION 1920x1080: OK")
    print("REAL FILE AUDIO STREAM ABSENT: OK")
    print("RESULT METADATA: OK")


finally:

    # ========================================================
    # RESTORE PROJECT SETTINGS
    # ========================================================

    project.aspect_ratio = (
        original_ratio
    )

    project.voice_enabled = (
        original_voice
    )

    project.save(
        update_fields=[
            "aspect_ratio",
            "voice_enabled",
            "updated_at",
        ]
    )


    print()
    print("=" * 100)
    print("PROJECT RESTORE")
    print("=" * 100)

    print(
        "Aspect ratio restored:",
        project.aspect_ratio
    )

    print(
        "Voice restored:",
        project.voice_enabled
    )


print()
print("=" * 100)
print("AUDIT_REAL_RENDER_V39B: OK")
print("=" * 100)
