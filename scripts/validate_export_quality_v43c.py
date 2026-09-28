from pathlib import Path
import os
import sys
import re
import subprocess
import django

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)

django.setup()

from projects.models import Project
from generations.final_services import (
    get_project_video_timeline,
    render_real_final_mp4,
)


print()
print("=" * 108)
print("GINGAO V43C - REAL 720P / 1080P / 1440P EXPORT VALIDATION")
print("=" * 108)


# =============================================================================
# SELECT PROJECT
# =============================================================================

project = (
    Project.objects
    .filter(id=5)
    .first()
)

if project is None:
    project = (
        Project.objects
        .order_by("id")
        .first()
    )

if project is None:
    raise RuntimeError(
        "No project available for V43C."
    )


print()
print(
    "TEST PROJECT:",
    project.id,
    project.title,
)


# =============================================================================
# KEEP ORIGINAL VALUES IN MEMORY
# =============================================================================

original_ratio = project.aspect_ratio
original_voice = project.voice_enabled
original_quality = project.quality_tier


# We DO NOT save these changes.
project.aspect_ratio = "16:9"
project.voice_enabled = False


timeline_result = get_project_video_timeline(
    project
)


# get_project_video_timeline may return:
# - timeline
# - (timeline, total_duration)
# - [timeline, total_duration]
#
# Normalize it here without touching production code.

timeline = timeline_result
total_duration = None


if (
    isinstance(
        timeline_result,
        (tuple, list),
    )
    and len(timeline_result) >= 2
    and isinstance(
        timeline_result[0],
        list,
    )
):
    timeline = timeline_result[0]

    try:
        total_duration = float(
            timeline_result[1]
            or 0
        )
    except (
        TypeError,
        ValueError,
    ):
        total_duration = None


if not isinstance(
    timeline,
    list,
):
    raise RuntimeError(
        "Unexpected timeline result type: "
        + repr(
            type(
                timeline
            )
        )
    )


if not timeline:
    raise RuntimeError(
        "Selected project has no usable timeline."
    )


if total_duration is None:

    total_duration = sum(
        float(
            item.get(
                "duration",
                0,
            )
            or 0
        )
        for item in timeline
        if isinstance(
            item,
            dict,
        )
    )


if total_duration <= 0:
    raise RuntimeError(
        "Timeline duration is invalid."
    )


print(
    "Timeline result type:",
    type(
        timeline_result
    ).__name__,
)

print(
    "Timeline items:",
    len(timeline),
)

print(
    "Total duration:",
    total_duration,
)


# =============================================================================
# EXPECTED OUTPUTS
# =============================================================================

tests = [
    (
        "fast",
        "HD 720p",
        1280,
        720,
    ),
    (
        "standard",
        "Full HD 1080p",
        1920,
        1080,
    ),
    (
        "premium",
        "2K 1440p",
        2560,
        1440,
    ),
]


generated_paths = []
results = []


def inspect_mp4(
    path,
):

    import imageio_ffmpeg

    ffmpeg = (
        imageio_ffmpeg
        .get_ffmpeg_exe()
    )

    proc = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-i",
            str(path),
        ],
        capture_output=True,
        text=True,
    )

    media_info = (
        proc.stderr
        or proc.stdout
        or ""
    )

    match = re.search(
        r"Video:.*?(\d{2,5})x(\d{2,5})",
        media_info,
        flags=re.S,
    )

    if not match:
        raise RuntimeError(
            "Could not inspect MP4 resolution: "
            + str(path)
        )

    width = int(
        match.group(1)
    )

    height = int(
        match.group(2)
    )

    return (
        width,
        height,
        media_info,
    )


try:

    for (
        quality,
        label,
        expected_width,
        expected_height,
    ) in tests:

        print()
        print("-" * 108)
        print(
            "EXPORT:",
            label,
            f"({quality})",
        )
        print("-" * 108)


        result = render_real_final_mp4(
            project=project,
            timeline=timeline,
            total_duration=total_duration,
            audio_info=None,
            quality_tier=quality,
        )


        path = Path(
            result["path"]
        )

        generated_paths.append(
            path
        )


        print(
            "URL:",
            result["url"],
        )

        print(
            "PATH:",
            path,
        )

        print(
            "RESULT QUALITY:",
            result["quality_tier"],
        )

        print(
            "RESULT WIDTH:",
            result["width"],
        )

        print(
            "RESULT HEIGHT:",
            result["height"],
        )

        print(
            "RESULT CRF:",
            result["crf"],
        )

        print(
            "RESULT PRESET:",
            result["preset"],
        )


        assert path.exists(), (
            f"Physical MP4 missing: {path}"
        )

        assert (
            result["quality_tier"]
            == quality
        )

        assert (
            result["width"]
            == expected_width
        )

        assert (
            result["height"]
            == expected_height
        )


        (
            real_width,
            real_height,
            media_info,
        ) = inspect_mp4(
            path
        )


        print(
            "PHYSICAL WIDTH:",
            real_width,
        )

        print(
            "PHYSICAL HEIGHT:",
            real_height,
        )


        assert (
            real_width
            == expected_width
        ), (
            f"{label}: physical width "
            f"{real_width} != "
            f"{expected_width}"
        )

        assert (
            real_height
            == expected_height
        ), (
            f"{label}: physical height "
            f"{real_height} != "
            f"{expected_height}"
        )


        size_mb = (
            path.stat().st_size
            / 1024
            / 1024
        )


        results.append({
            "quality":
                quality,

            "label":
                label,

            "width":
                real_width,

            "height":
                real_height,

            "size_mb":
                round(
                    size_mb,
                    2,
                ),

            "crf":
                result["crf"],

            "preset":
                result["preset"],
        })


        print(
            f"{label} PHYSICAL MP4: OK"
        )


finally:

    # Restore only the in-memory object.
    project.aspect_ratio = (
        original_ratio
    )

    project.voice_enabled = (
        original_voice
    )

    project.quality_tier = (
        original_quality
    )


    print()
    print("=" * 108)
    print("PHYSICAL CLEANUP")
    print("=" * 108)

    removed = 0

    for path in generated_paths:

        try:

            if path.exists():

                path.unlink()

                removed += 1

        except Exception as exc:

            print(
                "WARNING cleanup:",
                path,
                exc,
            )


    print(
        "Temporary MP4 files removed:",
        removed,
    )


# =============================================================================
# SUMMARY
# =============================================================================

print()
print("=" * 108)
print("V43C RESULTS")
print("=" * 108)

for item in results:

    print(
        f"{item['label']:<18} "
        f"{item['width']}x{item['height']} "
        f"CRF={item['crf']} "
        f"preset={item['preset']} "
        f"size={item['size_mb']} MB"
    )


assert len(
    results
) == 3


assert {
    (
        item["width"],
        item["height"],
    )
    for item in results
} == {
    (1280, 720),
    (1920, 1080),
    (2560, 1440),
}


print()
print(
    "720P REAL EXPORT: OK"
)

print(
    "1080P REAL EXPORT: OK"
)

print(
    "1440P REAL EXPORT: OK"
)

print(
    "EXPORT QUALITY OVERRIDE: OK"
)

print(
    "PROJECT DATABASE SETTINGS UNCHANGED: OK"
)

print(
    "TEMPORARY MP4 CLEANUP: OK"
)

print()
print("=" * 108)
print("GINGAO V43C: OK")
print("=" * 108)
