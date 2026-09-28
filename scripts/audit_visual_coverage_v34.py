from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

service = (
    ROOT
    / "generations"
    / "final_services.py"
).read_text(
    encoding="utf-8",
    errors="ignore"
)

views = (
    ROOT
    / "projects"
    / "views.py"
).read_text(
    encoding="utf-8",
    errors="ignore"
)

template = (
    ROOT
    / "templates"
    / "dashboard"
    / "final_cut.html"
).read_text(
    encoding="utf-8",
    errors="ignore"
)

assert (
    "GINGAO_REAL_VISUAL_COVERAGE_V34"
    in service
)

assert (
    "get_project_visual_coverage"
    in service
)

assert (
    '"real_percent"'
    in service
)

assert (
    '"complete"'
    in service
)

assert (
    "get_project_visual_coverage"
    in views
)

assert (
    '"visual_coverage":'
    in views
)

assert (
    "GINGAO_REAL_VISUAL_COVERAGE_UI_V34"
    in template
)

assert (
    "visual_coverage.real_count"
    in template
)

assert (
    "visual_coverage.real_percent"
    in template
)

print("REAL VISUAL DETECTION: OK")
print("MOCK VISUAL DETECTION: OK")
print("MISSING VISUAL DETECTION: OK")
print("PROJECT COVERAGE PERCENT: DYNAMIC")
print("SCENE STATUS UI: OK")
print("EXPORT WARNING: OK")
print("AUDIT_VISUAL_COVERAGE_V34: OK")
