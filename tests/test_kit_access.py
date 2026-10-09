"""The access kit the plugin carries, proved in its own fixture (§PW355).

Its proof is a script, since whether text still fits at the largest scale and a camera
keeps still with shake off is something only the running game can say; it runs where
$GODOT is set and is said skipped where not.
"""

from __future__ import annotations

import os
import shutil

import pytest

from polyweave import kits


def test_the_access_kit_contributes_the_accessibility_tab_after_options():
    found = kits.every()["access"]
    assert found["requires"] == ["options"]
    assert found["tab"] == "accessibility"
    assert found["proves"] == {"fixture": "fixture", "script": "core/proof.gd"}


def test_the_access_kit_is_skipped_without_an_engine(monkeypatch):
    monkeypatch.delenv("GODOT", raising=False)
    [said] = kits.prove("access")["kits"]
    assert said["status"] == "skipped"


def _installed(tmp_path):
    game = tmp_path / "game"
    shutil.copytree(kits.KITS / "access" / "fixture", game)
    return game, kits.install("access", root=str(game))


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
def test_the_access_kit_lands_after_options_and_holds_in_its_fixture(tmp_path):
    _, said = _installed(tmp_path)
    assert said["order"] == ["prompts", "menus", "options", "access"]
    assert said["proved"]["passed"] is True, said["proved"]


ACCESS = "addons/polyweave/access/access.gd"


@pytest.mark.skipif(not os.environ.get("GODOT"), reason="no $GODOT on this machine")
@pytest.mark.parametrize(("where", "before", "after", "said"), [
    (ACCESS, "_theme.default_font_size = int(round(_base * scale))", "pass",
     "the text scale never reaches it"),
    ("main.tscn", 'text = "Star Garden"\n',
     'text = "Star Garden"\ntheme_override_font_sizes/font_size = 16\n',
     "Title draws at 16 px at 200%"),
    ("main.tscn", 'text = "Star Garden"\n',
     'text = "Star Garden: The Long Night of the Lanterns"\nclip_text = true\n',
     "at 200% /root/Main/Box/Title is"),
    (ACCESS, "return amount if shaking else amount * 0", "return amount",
     "with shake off, /root/Shake/Camera moved"),
    (ACCESS, "_toggled[action] = not _toggled.get(action, false)", "pass",
     "with toggle on, an action does not turn on"),
    ("shake.gd", "offset = Access.shared().shake(", "offset = Vector2.ZERO * (",
     "the shake run never moved a camera"),
    ("addons/polyweave/access/filters.gd",
     "return _colour(lin + _rows(SHIFT, error))", "return c",
     ".polyweave/kits/access/deuteranopia.png delta_e_min"),
    (ACCESS, "\t\t_caption.get_parent().visible = false\n", "\t\tpass\n",
     "still shows after its line ended"),
    (ACCESS, "if not subtitles or player == null:", "if player == null:",
     "with subtitles off, a line still showed its subtitle"),
    ("polyweave_access.gd", "const PAIR_DELTA_E := 15.0",
     'const PAIR_DELTA_E := 15.0\nconst SUBTITLE_KEYS := ["' + "and on " * 60 + '"]',
     "lines, over the 3 a subtitle may"),
    ("polyweave_access.gd", "const PAIR_DELTA_E := 15.0",
     "const PAIR_DELTA_E := 15.0\nconst SUBTITLE_LINES := 99\n"
     'const SUBTITLE_KEYS := ["' + "and on " * 1000 + '"]',
     "leaves the screen"),
    (ACCESS, "return strength if flashing else 0.0", "return strength",
     "flash_run-flashes=off flashes 7"),
    ("flash.gd", "Access.shared().flash(1.0 if on else 0.0)", "0.0",
     "flash_run-flashes=on flashes 0"),
])
def test_a_broken_access_option_fails_the_proof_by_name(tmp_path, where, before, after,
                                                        said):
    game, _ = _installed(tmp_path)
    broken = game / where
    text = broken.read_text(encoding="utf-8")
    assert before in text
    broken.write_text(text.replace(before, after), encoding="utf-8")
    [found] = kits._scripts(["access"], kits.every(), game)
    assert found["status"] == "failed"
    assert said in found["said"]


def test_a_capture_with_no_screen_to_draw_on_is_skipped_and_said(tmp_path, monkeypatch):
    from polyweave import capture
    from polyweave.errors import PolyweaveError

    def no_screen(*_, **__):
        raise PolyweaveError("engine.no-offscreen-route",
                             "no route draws real pixels on this machine", "use one")

    monkeypatch.setattr(capture, "movie", no_screen)
    [said] = kits._captures("KIT CAPTURE core/run.gd flashes 0 3 flashes=off\n",
                            tmp_path)
    assert said["held"] is True
    assert "no route draws" in said["skipped"]
    assert said["args"] == ["flashes=off"]
