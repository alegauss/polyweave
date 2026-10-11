"""A style that takes its palette from code, or from another project (§PW387).

Spinhold's Quilt is drawn in Cottony's colours, and Cottony keeps its palette in
tools/art/palette.py, so Spinhold held a hand copy of the hex values that nothing told
it had drifted. Here a sister project declares its palette from code, and another
borrows it, shifted for dusk, and hears when it moves.
"""

from __future__ import annotations

import pytest

from polyweave import style
from polyweave.config import _shifted, load
from polyweave.errors import PolyweaveError

PALETTE_PY = '''"""The sister game's palette."""

PIPING = "#FFFAEE"  # the white rope
CARD = "#F7E8CB"
HEART: str = "#ff7fac"
NOT_A_COLOUR = "cotton"
'''


@pytest.fixture
def sister(tmp_path):
    cottony = tmp_path / "cottony"
    (cottony / "tools" / "art").mkdir(parents=True)
    (cottony / "tools" / "art" / "palette.py").write_text(PALETTE_PY, encoding="utf-8")
    (cottony / "polyweave.toml").write_text(
        '[style]\npalette_source = { file = "tools/art/palette.py", names = '
        '["HEART", "PIPING"] }\n', encoding="utf-8")
    return cottony


def test_a_palette_kept_in_code_is_read_as_the_style_s(sister):
    assert load(sister).style()[1]["palette"] == ["#FF7FAC", "#FFFAEE"]
    (sister / "polyweave.toml").write_text(
        '[style]\npalette_source = { file = "tools/art/palette.py" }\n',
        encoding="utf-8")
    assert load(sister).style()[1]["palette"] == ["#FFFAEE", "#F7E8CB", "#FF7FAC"]


def test_a_name_the_code_does_not_hold_is_refused(sister):
    (sister / "polyweave.toml").write_text(
        '[style]\npalette_source = { file = "tools/art/palette.py", names = '
        '["NOT_A_COLOUR"] }\n', encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        load(sister).style()
    assert refused.value.code == "config.bad-type"


def test_a_style_borrows_another_project_s_palette_shifted(sister, tmp_path):
    spinhold = tmp_path / "spinhold"
    spinhold.mkdir()
    (spinhold / "polyweave.toml").write_text(
        '[style.quilt]\nborrow = { root = "../cottony", lightness = -0.2 }\n'
        '[style.neon]\npalette = ["#0B0B1A"]\n', encoding="utf-8")
    found = style.read("quilt", root=str(spinhold))
    assert found["palette"] == [_shifted("#FF7FAC", -0.2, 0.0),
                                _shifted("#FFFAEE", -0.2, 0.0)]
    assert found["palette"][0] != "#FF7FAC"
    assert found["borrowed"]["moved"] is False
    assert found["borrowed"]["family"] == "default"


def test_a_source_that_moved_since_it_was_pinned_says_so(sister, tmp_path):
    spinhold = tmp_path / "spinhold"
    spinhold.mkdir()
    (spinhold / "polyweave.toml").write_text(
        '[style.quilt]\nborrow = { root = "../cottony" }\n', encoding="utf-8")
    digest = style.read("quilt", root=str(spinhold))["borrowed"]["digest"]
    (spinhold / "polyweave.toml").write_text(
        f'[style.quilt]\nborrow = {{ root = "../cottony", pinned = "{digest}" }}\n',
        encoding="utf-8")
    assert style.read("quilt", root=str(spinhold))["borrowed"]["moved"] is False
    text = (sister / "tools" / "art" / "palette.py").read_text("utf-8")
    (sister / "tools" / "art" / "palette.py").write_text(
        text.replace("#ff7fac", "#ff6fa0"), encoding="utf-8")
    assert style.read("quilt", root=str(spinhold))["borrowed"]["moved"] is True


def test_borrowing_from_a_root_with_no_project_is_refused(tmp_path):
    (tmp_path / "polyweave.toml").write_text(
        '[style]\nborrow = { root = "../nowhere" }\n', encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        load(tmp_path).style()
    assert refused.value.code == "config.bad-type"
