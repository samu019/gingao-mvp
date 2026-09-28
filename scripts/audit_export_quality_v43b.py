from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

final = (
    ROOT
    / "generations"
    / "final_services.py"
).read_text(
    encoding="utf-8"
)

views = (
    ROOT
    / "projects"
    / "views.py"
).read_text(
    encoding="utf-8"
)

template = (
    ROOT
    / "templates"
    / "dashboard"
    / "final_cut.html"
).read_text(
    encoding="utf-8"
)


assert "quality_override=None" in final
assert "quality_override=quality_tier" in final

assert "quality_tier=None" in final

assert 'request.POST.get(' in views
assert '"export_quality"' in views
assert "valid_export_qualities" in views
assert "quality_tier=export_quality" in views

assert "GINGAO_EXPORT_QUALITY_V43B" in template
assert 'name="export_quality"' in template

assert 'value="fast"' in template
assert 'value="standard"' in template
assert 'value="premium"' in template

assert "720p" in template
assert "1080p" in template
assert "1440p" in template

assert "{{ project.aspect_ratio }}" in template

# Export choice must not permanently modify Project.quality_tier.
export_view_start = views.index(
    "def export_final_cut_view("
)

export_view = views[
    export_view_start:
]

assert "project.quality_tier =" not in export_view
assert "project.save(" not in export_view

print("EXPORT QUALITY OVERRIDE: OK")
print("720P OPTION: OK")
print("1080P OPTION: OK")
print("1440P OPTION: OK")
print("PROJECT QUALITY NOT MUTATED: OK")
print("DYNAMIC PROJECT FORMAT: OK")
print("AUDIT_EXPORT_QUALITY_V43B: OK")
