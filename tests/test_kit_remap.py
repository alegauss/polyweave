"""The remap kit the plugin carries, proved in its own fixture (§PW345).

It lands with the prompts kit it draws its icons from; its script, which rebinds, swaps,
restarts and resets in the running game, runs where $GODOT is set and is said skipped
where it is not.
"""

from __future__ import annotations

import os
import shutil

import pytest

from polyweave.layers import kits


@pytest.mark.parametrize("layout", ["xbox", "playstation", "switch"])
def test_each_pad_s_spots_table_is_where_its_drawing_puts_each_place(layout):
    """The screen reads core/pads/<layout>.json and the picture is drawn from
    pads/<layout>.svg, so the table is held to the drawing's spots group (§PW428)."""
    import json
    import xml.etree.ElementTree as ET

    kit = kits.KITS / "remap"
    root = ET.parse(kit / "pads" / f"{layout}.svg").getroot()
    left, top, width, height = (float(v) for v in root.get("viewBox").split())
    group = next(g for g in root.iter() if g.get("id") == "spots")
    drawn = [
        {
            "code": spot.get("data-code"),
            "at": [round((float(spot.get("cx")) - left) / width, 3),
                   round((float(spot.get("cy")) - top) / height, 3)],
            "side": -1 if float(spot.get("cx")) - left < width / 2 else 1,
        }
        for spot in group
    ]
    table = json.loads((kit / "core" / "pads" / f"{layout}.json").read_text("utf-8"))
    assert table["slots"] == drawn
    # what picture.vector drew from it holds to the kit's spec for a pad
    from polyweave.loop import accept

    said = accept.checked(
        str(kit / "pads" / "pads.accept.toml"),
        str(kit / "core" / "pads" / f"{layout}.png"),
    )
    assert said["passed"], said["failed"]


def test_the_remap_kit_needs_the_prompts_kit():
    found = kits.every()["remap"]
    assert found["requires"] == ["prompts"]
    assert found["proves"]["script"] == "core/proof.gd"
    assert found["declares"]["conflict"] == "swap"


def test_the_remap_kit_lands_after_prompts_and_proves_in_its_fixture(tmp_path):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "remap" / "fixture", game)
    said = kits.install("remap", root=str(game))
    assert said["order"] == ["prompts", "remap"]
    assert said["proved"]["passed"] is True, said["proved"]
    expected = "held" if os.environ.get("GODOT") else "skipped"
    assert [s["status"] for s in said["proved"]["scripts"]] == [expected, expected]
    assert (game / "addons" / "polyweave" / "remap" / "bindings.gd").is_file()
    assert (game / "kits" / "remap" / "remap_menu.tscn").is_file()
    # The pad screen and its layout's spots table land with the core (§PW428).
    assert (game / "addons" / "polyweave" / "remap" / "pad_screen.gd").is_file()
    assert (game / "addons" / "polyweave" / "remap" / "pads" / "xbox.json").is_file()


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_a_clash_shared_instead_of_swapped_fails_the_proof(tmp_path):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "remap" / "fixture", game)
    kits.install("remap", root=str(game))
    store = game / "addons" / "polyweave" / "remap" / "bindings.gd"
    text = store.read_text(encoding="utf-8")
    store.write_text(text.replace("\t\tout[each] = theirs\n", "\t\tpass\n"),
                     encoding="utf-8")
    [found] = kits._scripts(["remap"], kits.every(), game)
    assert found["status"] == "failed"
    assert "fire still shares its key with jump" in found["said"]


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_a_screen_on_a_store_of_its_own_fails_the_proof(tmp_path):
    # its own store left the shared one stale and the players kit unknowing (§PW540)
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "remap" / "fixture", game)
    kits.install("remap", root=str(game))
    screen = game / "addons" / "polyweave" / "remap" / "remap_menu.gd"
    text = screen.read_text(encoding="utf-8")
    shared = "\t\tbindings = _PwBindings.shared()\n"
    assert shared in text
    screen.write_text(text.replace(shared, "\t\tbindings = _PwBindings.new(actions)\n"),
                      encoding="utf-8")
    [found] = kits._scripts(["remap"], kits.every(), game)
    assert found["status"] == "failed"
    assert "keeps a store of its own" in found["said"]


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
@pytest.mark.parametrize(("before", "after", "said"), [
    ("\t_paint()\n\tif was != \"\":", "\tfor row in _rows.get_children():\n"
     "\t\trow.free()\n\t_buttons.clear()\n\t_draw_rows()\n\tif was != \"\":",
     "binding jump lost the focus on its button"),
    ("\tif was != \"\":\n\t\tlistened.emit(was)\n", "",
     "did not say it listened for jump and stopped"),
])
def test_a_screen_that_loses_focus_or_says_nothing_fails_the_proof(
        tmp_path, before, after, said):
    # a host game read the screen's private field and put focus back itself (§PW541)
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "remap" / "fixture", game)
    kits.install("remap", root=str(game))
    screen = game / "addons" / "polyweave" / "remap" / "remap_menu.gd"
    text = screen.read_text(encoding="utf-8")
    assert before in text
    screen.write_text(text.replace(before, after), encoding="utf-8")
    [found] = kits._scripts(["remap"], kits.every(), game)
    assert found["status"] == "failed"
    assert said in found["said"]


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
@pytest.mark.parametrize(("script", "before", "after", "said"), [
    ("pad_screen.gd",
     "\treturn bindings.label(action) if bindings.labels.has(action) \\\n",
     "\treturn action if false \\\n", "not its declared label"),
    ("pad_screen.gd", "\treturn _PwPrompts.shared().fill(line)\n", "\treturn line\n",
     "help names no confirm button"),
    ("pad_screen.gd", "\tif move == \"\" and bindings.pressed_on_screen(event):\n",
     "\tif move == \"\" and false:\n",
     "declared confirm did not choose"),
    ("remap_menu.gd", "\t\t\tand confirm_focused():\n", "\t\t\tand false:\n",
     "declared confirm did not press the focused button"),
])
def test_screens_on_raw_names_or_ui_actions_alone_fail_the_proof(
        tmp_path, script, before, after, said):
    # Spinhold's pad read "move_left", named no button and bound pads to ui_* (§PW542)
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "remap" / "fixture", game)
    kits.install("remap", root=str(game))
    screen = game / "addons" / "polyweave" / "remap" / script
    text = screen.read_text(encoding="utf-8")
    assert before in text
    screen.write_text(text.replace(before, after), encoding="utf-8")
    [found] = kits._scripts(["remap"], kits.every(), game)
    assert found["status"] == "failed"
    assert said in found["said"]


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_the_remap_proof_holds_in_a_game_with_none_of_its_actions(tmp_path):
    # a kit that requires remap lands it in a game of its own actions (§PW392)
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "presence" / "fixture", game)
    said = kits.install("remap", root=str(game))
    assert said["proved"]["passed"] is True, said["proved"]


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_a_rebound_pad_binding_that_answers_pad_0_alone_fails_the_proof(tmp_path):
    # a decoded event keeps device 0 unless the store says otherwise (§PW391)
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "remap" / "fixture", game)
    kits.install("remap", root=str(game))
    broken = game / "addons" / "polyweave" / "remap" / "bindings.gd"
    text = broken.read_text(encoding="utf-8")
    assert "\t\t\tbutton.device = -1\n" in text
    broken.write_text(text.replace("\t\t\tbutton.device = -1\n", ""), encoding="utf-8")
    [found] = kits._scripts(["remap"], kits.every(), game)
    assert found["status"] == "failed"
    assert "answers pad 0 alone" in found["said"]
