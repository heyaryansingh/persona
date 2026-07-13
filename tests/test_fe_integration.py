"""Guard: the flagship (field.js) + Lane-4 modules are wired into index.html (Lane 4 / S3).
Structural check only — live render/interaction is S2's browser smoke (ui_research_smoke.cjs)."""
from pathlib import Path

HTML = (Path(__file__).resolve().parents[1] / "persona/api/static/index.html").read_text(encoding="utf-8")


def test_field_surface_wired():
    assert 'id="surf-field"' in HTML and 'id="fieldmount"' in HTML
    assert "function openField(" in HTML
    assert 'if(name==="field"){ openField(); }' in HTML   # setSurface dispatch
    assert "['field','Field rests on']" in HTML           # Map subtab
    assert "field:'map'" in HTML                          # SURF_DEST


def test_lane4_modules_linked():
    for src in ["/static/js/ui.js", "/static/js/focus.js", "/static/js/field.js", "/static/js/verdict.js"]:
        assert f'src="{src}"' in HTML, src
    assert 'href="/static/css/focus.css"' in HTML
