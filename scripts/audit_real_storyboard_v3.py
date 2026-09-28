from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

tpl = (
    ROOT
    / "templates/dashboard/images_workspace.html"
).read_text(
    encoding="utf-8"
)

css = (
    ROOT
    / "static/css/gingao.css"
).read_text(
    encoding="utf-8"
)

assert "storyboard-grid" in tpl

assert (
    "GINGAO_REAL_STORYBOARD_GRID_V3"
    in css
)

assert ".storyboard-grid > *" in css
assert "repeat(" in css
assert "aspect-ratio:" in css
assert "translateY(-6px)" in css
assert "max-width: 699px" in css

print("REAL GRID SELECTOR: OK")
print("DIRECT CARD SELECTOR: OK")
print("UNIFORM IMAGE RATIO: OK")
print("PREMIUM HOVER: OK")
print("MOBILE TWO COLUMNS: OK")
print("RESPONSIVE: OK")
print("AUDIT_REAL_STORYBOARD_V3: OK")
