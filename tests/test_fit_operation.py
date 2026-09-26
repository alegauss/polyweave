"""A voxel fit a project calls, rather than a script it writes (§PW230).

The fit itself is §PW98's and tested there; here it is reached as an operation, with
a known answer: a plate fitted to a drawing three times as wide as it is tall.
"""

from __future__ import annotations

import pytest
from PIL import Image

from polyweave import cli, describe
from polyweave.errors import PolyweaveError

SHIP = """name = "ship"
output = "hull"

[params]
w = 4.0   # the hull's width, fitted
d = 1.0

[voxels]
cell = 0.25
mesh = false

[search.w]
min = 1.0
max = 10.0

[[nodes]]
id = "hull"
op = "plate"
rect = [0, 0, "w", 2]
depth = "d"
"""


def project(tmp_path, body: str = SHIP) -> None:
    (tmp_path / "ship.toml").write_text(body, encoding="utf-8")
    picture = Image.new("RGBA", (300, 100), (0, 0, 0, 0))
    picture.paste((200, 60, 60, 255), (0, 0, 300, 100))
    picture.save(tmp_path / "ref.png")


def test_the_fit_is_an_operation_a_caller_can_find():
    describe.load()
    assert "geometry.fit" in {one["operation"] for one in describe.describe()}


def test_a_fit_answers_the_best_values_without_touching_the_declaration(tmp_path):
    project(tmp_path)
    found = cli.fit_one("ship.toml", "ref.png", root=str(tmp_path))
    assert found["best"]["w"] == pytest.approx(6.0, abs=0.3)
    assert found["views"]["front"] > 0.95
    assert found["written"] == []
    assert "model" not in found
    assert (tmp_path / "ship.toml").read_text("utf-8") == SHIP


def test_write_puts_the_best_values_into_params_and_keeps_the_rest(tmp_path):
    project(tmp_path)
    found = cli.fit_one("ship.toml", "ref.png", write=True, root=str(tmp_path))
    assert found["written"] == ["w"]
    text = (tmp_path / "ship.toml").read_text("utf-8")
    assert f"w = {found['best']['w']:.6g}   # the hull's width, fitted" in text
    assert "d = 1.0\n" in text
    assert text.replace(f"{found['best']['w']:.6g}", "4.0") == SHIP
    rebuilt = cli.build_one("ship.toml", root=str(tmp_path))
    assert rebuilt["says"] == found["says"]


def test_a_sheet_is_written_where_asked(tmp_path):
    project(tmp_path)
    found = cli.fit_one("ship.toml", "ref.png", sheet="fit.png", root=str(tmp_path))
    assert (tmp_path / "fit.png").is_file()
    assert found["sheet"].endswith("fit.png")


def test_a_drawing_cannot_stand_for_the_side(tmp_path):
    project(tmp_path)
    with pytest.raises(PolyweaveError) as refused:
        cli.fit_one("ship.toml", "ref.png", views=["side"], root=str(tmp_path))
    assert refused.value.code == "geom.bad-fit"


def test_it_runs_from_the_command_line(tmp_path, capsys):
    project(tmp_path)
    status = cli.main(["geometry.fit", "--source", "ship.toml", "--reference",
                       "ref.png", "--root", str(tmp_path)])
    assert status == 0
    assert "best.w: 6.0" in capsys.readouterr().out
