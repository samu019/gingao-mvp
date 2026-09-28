import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

final_path = (
    ROOT
    / "generations"
    / "final_services.py"
)

image_path = (
    ROOT
    / "generations"
    / "image_providers.py"
)

video_path = (
    ROOT
    / "generations"
    / "video_providers.py"
)

views_path = (
    ROOT
    / "projects"
    / "views.py"
)


files = [
    final_path,
    image_path,
    video_path,
    views_path,
]


print()
print("=" * 100)
print("GINGAO V41B CLEANUP AUDIT")
print("=" * 100)


for path in files:

    source = path.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    ast.parse(source)

    print(
        "SYNTAX OK:",
        path.relative_to(ROOT)
    )


final = final_path.read_text(
    encoding="utf-8",
    errors="ignore",
)


assert (
    "def _local_static_path("
    not in final
)

assert (
    "def _render_scene_segment("
    not in final
)

assert (
    "scale=1080:1920:"
    not in final
)

assert (
    "pad=1080:1920:"
    not in final
)

assert (
    "s=1080x1920:"
    not in final
)


# Current pipeline must remain present.

required = [
    "def get_project_output_spec(",
    "def _render_image_scene_clip(",
    "def _render_fallback_scene_clip(",
    "def _render_scene_visual_clip(",
    "def get_project_video_timeline(",
    "def create_mock_final_cut(",
    "def create_local_final_mp4(",
    "def render_real_final_mp4(",
    "def get_project_visual_coverage(",
]

for token in required:

    assert token in final, (
        f"Required pipeline function missing: "
        f"{token}"
    )


image = image_path.read_text(
    encoding="utf-8",
    errors="ignore",
)

video = video_path.read_text(
    encoding="utf-8",
    errors="ignore",
)


assert (
    "get_generation_profile"
    in image
)

assert (
    "get_generation_profile"
    in video
)

assert (
    "/static/generated/video_mock/"
    in video
)

assert (
    "if image_url:"
    not in video
)


print()
print("DEAD FINAL HELPERS REMOVED: OK")
print("HARDCODED LEGACY 1080x1920 REMOVED: OK")
print("CURRENT FINAL PIPELINE PRESERVED: OK")
print("DYNAMIC IMAGE PROFILE PRESERVED: OK")
print("DYNAMIC VIDEO PROFILE PRESERVED: OK")
print("SEPARATE MOCK VIDEO OUTPUT PRESERVED: OK")

print()
print("=" * 100)
print("AUDIT_CLEANUP_V41B: OK")
print("=" * 100)
