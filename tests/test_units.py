"""The scale an asset is baked at, against the one the engine draws it at.

§PW24's case: Cottony's board tray renders at one unit per pixel because somebody set
the render rectangle to match a cell size the game holds separately. The two numbers
agree because a person made them agree, and nothing fails if either moves.
"""

from __future__ import annotations

import pytest

from polyweave import units
from polyweave.errors import PolyweaveError


def project(tmp_path, body):
    (tmp_path / "polyweave.toml").write_text(body, encoding="utf-8")
    return tmp_path


def game(tmp_path, body, *, name="board.gd"):
    (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "scripts" / name).write_text(body, encoding="utf-8")
    return f"scripts/{name}"


# -- reading the number the engine already has --------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        "const CELL_PX := 64",
        "const CELL_PX = 64",
        "const CELL_PX: int = 64",
        "@export var CELL_PX := 64",
        "var CELL_PX = 64",
    ],
)
def test_a_constant_is_read_however_the_game_spells_it(tmp_path, line):
    where = game(tmp_path, f"extends Node\n\n{line}\n")
    assert units.read_number(f"{where}:CELL_PX", root=tmp_path) == 64.0


def test_a_key_in_a_json_file_is_read_too(tmp_path):
    (tmp_path / "board.json").write_text('{"cell_px": 48}', encoding="utf-8")
    assert units.read_number("board.json:cell_px", root=tmp_path) == 48.0


def test_so_is_one_in_an_ini_shaped_file(tmp_path):
    (tmp_path / "project.godot").write_text(
        "[display]\n\nwindow/size/viewport_width=1920\n", encoding="utf-8"
    )
    found = units.read_number("project.godot:window/size/viewport_width", root=tmp_path)
    assert found == 1920.0


def test_a_constant_that_moved_is_the_refusal_rather_than_a_wrong_sprite(tmp_path):
    """Reading it from the engine's own file is what turns a rename into this."""
    where = game(tmp_path, "extends Node\n\nconst TILE := 64\n")
    with pytest.raises(PolyweaveError) as caught:
        units.read_number(f"{where}:CELL_PX", root=tmp_path)
    assert caught.value.code == "units.unreadable"
    assert "misaligned sprite" in caught.value.remedy


def test_a_file_that_is_not_there_says_so(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        units.read_number("scripts/gone.gd:CELL_PX", root=tmp_path)
    assert caught.value.code == "units.unreadable"


def test_an_address_with_no_name_in_it_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        units.read_number("scripts/board.gd", root=tmp_path)
    assert caught.value.code == "units.unreadable"
    assert "path/to/file.gd:NAME" in caught.value.remedy


# -- what the engine draws at ---------------------------------------------------------


def test_the_engine_s_scale_comes_from_where_the_engine_keeps_it(tmp_path):
    where = game(tmp_path, "extends Node\n\nconst CELL_PX := 64\n")
    project(tmp_path, f'[units]\nsource = "{where}:CELL_PX"\n')
    found = units.engine_scale(tmp_path)
    assert found["pixels_per_unit"] == 64.0
    assert found["source"].endswith("CELL_PX")


def test_stating_it_here_is_the_weaker_half_and_still_works(tmp_path):
    project(tmp_path, "[units]\npixels_per_unit = 32.0\n")
    assert units.engine_scale(tmp_path)["pixels_per_unit"] == 32.0


def test_a_project_that_declares_neither_is_said_so(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        units.engine_scale(tmp_path)
    assert caught.value.code == "units.undeclared"
    assert "by accident" in caught.value.remedy


# -- the arithmetic --------------------------------------------------------------------


def test_a_rectangle_at_a_scale_gives_a_size():
    assert units.for_size([4.0, 2.5], 64) == (256, 160)


def test_a_rectangle_that_lands_between_two_pixels_is_refused():
    with pytest.raises(PolyweaveError) as caught:
        units.for_size([4.0, 2.51], 64)
    assert caught.value.code == "units.not-whole"
    assert "160.64" in caught.value.message


def test_a_picture_and_a_rectangle_give_back_the_scale():
    assert units.implied([4.0, 2.0], [256, 128]) == (64.0, 64.0)


def test_a_rectangle_that_covers_nothing_is_not_a_rectangle():
    with pytest.raises(PolyweaveError) as caught:
        units.for_size([0.0, 2.0], 64)
    assert caught.value.code == "units.undeclared"


# -- an asset's own declaration --------------------------------------------------------


def test_a_declaration_can_be_a_mapping(tmp_path):
    found = units.declared({"covers": [4, 2], "pixels_per_unit": 64})
    assert found == {"covers": [4.0, 2.0], "pixels_per_unit": 64.0}


def test_or_a_toml_file_beside_the_asset(tmp_path):
    (tmp_path / "tray.toml").write_text(
        "[units]\ncovers = [4.0, 2.0]\npixels_per_unit = 64\n", encoding="utf-8"
    )
    found = units.declared("tray.toml", root=tmp_path)
    assert found["covers"] == [4.0, 2.0]
    assert found["pixels_per_unit"] == 64.0


def test_or_a_json_one(tmp_path):
    (tmp_path / "tray.json").write_text(
        '{"covers": [1, 1], "pixels_per_unit": 16}', encoding="utf-8"
    )
    assert units.declared("tray.json", root=tmp_path)["pixels_per_unit"] == 16.0


def test_a_declaration_with_no_rectangle_in_it_is_not_one():
    with pytest.raises(PolyweaveError) as caught:
        units.declared({"pixels_per_unit": 64})
    assert caught.value.code == "units.undeclared"


# -- the check that replaces two people agreeing ---------------------------------------


def test_the_two_scales_agreeing_is_what_holds(tmp_path):
    project(tmp_path, "[units]\npixels_per_unit = 64.0\n")
    found = units.check({"covers": [4, 2], "pixels_per_unit": 64}, root=tmp_path)
    assert found["holds"] is True
    assert found["size"] == [256, 128]


def test_an_asset_that_says_nothing_takes_the_engine_s_scale(tmp_path):
    project(tmp_path, "[units]\npixels_per_unit = 64.0\n")
    found = units.check({"covers": [1, 1]}, root=tmp_path)
    assert found["pixels_per_unit"] == 64.0
    assert found["size"] == [64, 64]


def test_the_engine_moving_is_a_refusal_with_both_numbers_in_it(tmp_path):
    """Not a misalignment found on a screen three commits later."""
    where = game(tmp_path, "extends Node\n\nconst CELL_PX := 48\n")
    project(tmp_path, f'[units]\nsource = "{where}:CELL_PX"\n')
    found = units.check({"covers": [4, 2], "pixels_per_unit": 64}, root=tmp_path)
    assert found["holds"] is False
    assert "64" in found["why"] and "48" in found["why"]
    assert "CELL_PX" in found["why"], "and where the engine's number came from"


def test_a_picture_of_the_wrong_size_is_caught_against_the_declaration(tmp_path):
    project(tmp_path, "[units]\npixels_per_unit = 64.0\n")
    found = units.check(
        {"covers": [4, 2], "pixels_per_unit": 64}, size=(256, 256), root=tmp_path
    )
    assert found["holds"] is False
    assert found["rendered"] == [256, 256]
    assert "256 x 128 pixels" in found["why"]


def test_the_right_size_holds(tmp_path):
    project(tmp_path, "[units]\npixels_per_unit = 64.0\n")
    found = units.check(
        {"covers": [4, 2], "pixels_per_unit": 64}, size=(256, 128), root=tmp_path
    )
    assert found["holds"] is True
    assert found["rendered"] == [256, 128]


def test_a_tolerance_the_project_sets_is_what_close_enough_means(tmp_path):
    project(tmp_path, "[units]\npixels_per_unit = 64.0\ntolerance = 0.5\n")
    found = units.check({"covers": [5, 5], "pixels_per_unit": 64.4}, root=tmp_path)
    assert found["holds"] is True


# -- as a gate -------------------------------------------------------------------------


def test_a_scale_disagreement_stops_the_work(tmp_path):
    project(tmp_path, "[units]\npixels_per_unit = 48.0\n")
    with pytest.raises(PolyweaveError) as caught:
        units.require({"covers": [4, 2], "pixels_per_unit": 64}, root=tmp_path)
    assert caught.value.code == "units.mismatch"
    assert "agreeing by hand" in caught.value.remedy


def test_a_size_disagreement_names_the_size_to_render_at(tmp_path):
    project(tmp_path, "[units]\npixels_per_unit = 64.0\n")
    with pytest.raises(PolyweaveError) as caught:
        units.require(
            {"covers": [4, 2], "pixels_per_unit": 64}, size=(256, 256), root=tmp_path
        )
    assert caught.value.code == "units.wrong-size"
    assert "render at 256 x 128" in caught.value.remedy


def test_what_holds_passes_straight_through(tmp_path):
    project(tmp_path, "[units]\npixels_per_unit = 64.0\n")
    assert units.require({"covers": [2, 2]}, size=(128, 128), root=tmp_path)["holds"]


# -- at bake time, which is the point --------------------------------------------------


class Quiet:
    def stage(self, stage, *, progress=None, note=None):
        pass

    def progress(self, value, *, note=None):
        pass

    def note(self, text):
        pass


def baking(tmp_path, body):
    from polyweave import render

    project(tmp_path, f"[render]\npreview_size = 48\nfinal_size = 64\n\n{body}")
    return render


def test_a_scale_that_disagrees_stops_before_anything_is_rendered(tmp_path):
    """The refusal costs nothing, which is why it happens first rather than after."""
    render = baking(tmp_path, "[units]\npixels_per_unit = 64.0\n")
    with pytest.raises(PolyweaveError) as caught:
        render.bake(
            Quiet(),
            out="tray.png",
            rung="sphere",
            covers=[1.0, 1.0],
            pixels_per_unit=48.0,
            root=tmp_path,
        )
    assert caught.value.code == "units.mismatch"
    assert not (tmp_path / "tray.png").exists(), "nothing was rendered to find this"


def test_a_rectangle_the_rung_cannot_render_is_refused_with_the_size_it_needs(tmp_path):
    render = baking(tmp_path, "[units]\npixels_per_unit = 64.0\n")
    with pytest.raises(PolyweaveError) as caught:
        render.bake(
            Quiet(), out="tray.png", rung="sphere", covers=[4.0, 2.0], root=tmp_path
        )
    assert caught.value.code == "units.wrong-size"
    assert "256 x 128" in caught.value.remedy
    assert not (tmp_path / "tray.png").exists()


def test_a_bake_that_declares_nothing_is_not_asked_about_scale(tmp_path):
    """Most renders are a preview of a thing, not a sprite on somebody's grid."""
    render = baking(tmp_path, "[units]\npixels_per_unit = 64.0\n")
    assert render.plan("sphere", root=tmp_path)["size"] == 48


def test_a_declaration_the_rung_does_match_is_carried_into_the_answer(tmp_path):
    pytest.importorskip("bpy", reason="Blender is not importable in this interpreter")
    render = baking(
        tmp_path, "samples = { sphere = 4 }\n\n[units]\npixels_per_unit = 16.0\n"
    )
    out = render.bake(
        Quiet(), out="tray.png", rung="sphere", covers=[3.0, 3.0], root=tmp_path
    )
    assert out["covers"] == [3.0, 3.0]
    assert out["pixels_per_unit"] == 16.0
    assert out["size"] == 48, "3 units at 16 px/unit, and the rung agrees"
