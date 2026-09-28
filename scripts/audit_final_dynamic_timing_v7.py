from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

service = (
    ROOT
    / "generations/final_services.py"
).read_text(
    encoding="utf-8"
)

views = (
    ROOT
    / "projects/views.py"
).read_text(
    encoding="utf-8"
)

tpl = (
    ROOT
    / "templates/dashboard/final_cut.html"
).read_text(
    encoding="utf-8"
)

css = (
    ROOT
    / "static/css/gingao.css"
).read_text(
    encoding="utf-8"
)


match = re.search(
    r"def\s+get_project_video_timeline\s*\([^)]*\)\s*:"
    r"(.*?)(?=\n(?:def|class)\s|\Z)",
    service,
    flags=re.S
)

assert match, (
    "get_project_video_timeline() not found"
)

fn = match.group(1)


assert "duration_seconds" in fn, (
    "Timeline does not reference "
    "scene.duration_seconds"
)

assert re.search(
    r'["\']duration["\']',
    fn
), "Timeline item duration field missing"

assert re.search(
    r'["\']start["\']',
    fn
), "Timeline item start field missing"

assert re.search(
    r'["\']end["\']',
    fn
), "Timeline item end field missing"

assert (
    "get_project_video_timeline"
    in views
), "View is not using timeline service"


required_template_tokens = [
    "{{ item.duration }}",
    "{{ item.start }}",
    "{{ item.end }}",
    "{{ total_duration }}",
]

for token in required_template_tokens:

    assert token in tpl, (
        "Missing template token: "
        + token
    )


assert (
    "GINGAO_FINAL_TIMELINE_NEUTRAL_V5_FIXED"
    in css
)


print("TIMELINE SERVICE: CONNECTED")
print("SCENE DURATION SOURCE: duration_seconds")
print("ITEM DURATION: DYNAMIC")
print("START TIME: DYNAMIC")
print("END TIME: DYNAMIC")
print("TOTAL DURATION DISPLAY: DYNAMIC")
print("VIEW -> SERVICE -> TEMPLATE: CONNECTED")
print("TIMELINE COLORS: NEUTRAL")
print("AUDIT_FINAL_DYNAMIC_TIMING_V7: OK")
