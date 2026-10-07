"""A menu panel built from a declaration, as nine-patch textures (§PW316)."""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from polyweave import panel, provenance
from polyweave.errors import PolyweaveError

HOLO = """\
[panel.holo]
size = [96, 64]
margin = 16
fill = "#0a1a2acc"
cut = 4
edge = { width = 2, colour = "#3fe0ff" }
brackets = { length = 10, width = 3, colour = "#ff4fd8" }
scan = { pitch = 3, colour = "#3fe0ff26" }

[panel.holo.states.focus]
edge = { colour = "#ffffff" }

[panel.holo.states.disabled]
fill = "#10101080"
"""


def panels(tmp_path, body: str = HOLO) -> str:
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "ui").mkdir(exist_ok=True)
    (tmp_path / "ui" / "kit.panel.toml").write_text(body, encoding="utf-8")
    return "ui/kit.panel.toml"


def pixels(tmp_path, name: str) -> np.ndarray:
    with Image.open(tmp_path / name) as opened:
        return np.asarray(opened.convert("RGBA")).astype(int)


def test_each_state_is_drawn_with_its_record_and_stylebox(tmp_path):
    made = panel.build(panels(tmp_path), root=str(tmp_path))["panels"]["holo"]
    assert set(made) == {"normal", "focus", "disabled"}
    normal = made["normal"]
    assert normal["file"] == "ui/holo.normal.png"
    assert normal["size"] == [96, 64]
    record = provenance.read(str(tmp_path / normal["file"]), root=tmp_path)
    assert record["inputs"][0] == {
        **record["inputs"][0], "role": "declaration", "path": "ui/kit.panel.toml"
    }
    assert record["params"]["state"] == "normal"
    style = (tmp_path / normal["stylebox"]).read_text("utf-8")
    assert 'path="res://ui/holo.normal.png"' in style
    assert "texture_margin_left = 16.0" in style
    # Scan lines tile, so their pitch holds at any height.
    assert "axis_stretch_vertical = 2" in style


def test_the_parts_land_where_they_are_declared(tmp_path):
    panel.build(panels(tmp_path), root=str(tmp_path))
    normal = pixels(tmp_path, "ui/holo.normal.png")
    focus = pixels(tmp_path, "ui/holo.focus.png")
    # The corner is cut off: transparent at the very corner pixel.
    assert normal[0, 0, 3] == 0
    # A bracket in its colour along the top, just past the cut.
    assert tuple(normal[1, 6, :3]) == (0xFF, 0x4F, 0xD8)
    # The edge on the side away from the brackets, and white once focused.
    assert tuple(normal[32, 0, :3]) == (0x3F, 0xE0, 0xFF)
    assert tuple(focus[32, 0, :3]) == (0xFF, 0xFF, 0xFF)
    # The scan lines alternate with the fill down the middle.
    middle = normal[20:29, 48, :3].tolist()
    assert len({tuple(p) for p in middle}) == 2


@pytest.mark.parametrize(
    ("change", "said"),
    [
        (("length = 10", "length = 20"), "stretching would bend it"),
        (("margin = 16", "margin = 50"), "leave no middle"),
        (('fill = "#0a1a2acc"', 'fill = "teal"'), "not a colour"),
        (("cut = 4", "cuts = 4"), "did you mean 'cut'"),
        (("[panel.holo.states.focus]", "[panel.holo.states.glow]"), "no key 'glow'"),
    ],
)
def test_a_panel_that_cannot_be_drawn_true_is_refused(tmp_path, change, said):
    with pytest.raises(PolyweaveError) as refused:
        panel.build(panels(tmp_path, HOLO.replace(*change)), root=str(tmp_path))
    assert refused.value.code == "compose.bad-panel"
    assert said in refused.value.message + refused.value.remedy
