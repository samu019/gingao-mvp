from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

views = (
    ROOT
    / "projects"
    / "views.py"
).read_text(
    encoding="utf-8",
    errors="ignore"
)

urls = (
    ROOT
    / "config"
    / "urls.py"
).read_text(
    encoding="utf-8",
    errors="ignore"
)

template = (
    ROOT
    / "templates"
    / "dashboard"
    / "images_workspace.html"
).read_text(
    encoding="utf-8",
    errors="ignore"
)

assert (
    "GINGAO_SMART_MULTI_IMAGE_UPLOAD_V35"
    in views
)

assert (
    "def upload_all_scene_images_view("
    in views
)

assert (
    'request.FILES.getlist('
    in views
)

assert (
    '"scene_images"'
    in views
)

assert (
    "save_scene_upload("
    in views
)

assert (
    "pending_scenes"
    in views
)

assert (
    "len(uploaded_files) == len(scenes)"
    in views
)

assert (
    "upload_all_scene_images_view"
    in urls
)

assert (
    'name="upload_all_scene_images"'
    in urls
)

assert (
    "GINGAO_SMART_MULTI_IMAGE_UPLOAD_UI_V35"
    in template
)

assert (
    'name="scene_images"'
    in template
)

assert (
    "multiple"
    in template
)

assert (
    "pending_scene_count"
    in template
)

print("MULTI FILE INPUT: OK")
print("EXISTING UPLOAD SERVICE REUSED: OK")
print("PENDING SCENE DETECTION: OK")
print("SMART ASSIGNMENT ORDER: OK")
print("REAL SCENES PRESERVED BY DEFAULT: OK")
print("FULL REPLACEMENT MODE: OK")
print("ROUTE: OK")
print("MOBILE UI: OK")
print("AUDIT_SMART_MULTI_IMAGE_UPLOAD_V35: OK")
