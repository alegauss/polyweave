"""A level played by the game's own probe, and what it measured read back (§PW202).

The handshake is checked everywhere; the run itself needs `$GODOT`.
"""

from __future__ import annotations

import json
import os

import pytest

from polyweave.kernel import provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.engine import levels

MEASURES = {"won": {"unit": "0 or 1", "direction": "higher"},
            "stars": {"unit": "stars", "direction": "higher"}}


def _said(*lines):
    return "Godot Engine v4.7.1.stable\n" + "\n".join(f"level: {one}" for one in lines)


def test_each_seed_s_line_is_read_in_seed_order():
    read = levels._read_lines(
        _said("seed=2 won=0 stars=0", "seed=1 won=1 stars=3", "seed=3 won=1 stars=1.5"),
        MEASURES, 3)
    assert read == {"won": [1.0, 0.0, 1.0], "stars": [3.0, 0.0, 1.5]}


@pytest.mark.parametrize("lines, said", [
    (["seed=1 won=1", "seed=2 won=1 stars=2"], "misses stars"),
    (["seed=1 won=1 stars=2 lives=3", "seed=2 won=1 stars=2"], "carries lives"),
    (["seed=1 won=1 stars=two", "seed=2 won=1 stars=2"], "is not name=number"),
    (["won=1 stars=2", "seed=2 won=1 stars=2"], "names no whole seed"),
    (["seed=1 won=1 stars=2", "seed=1 won=0 stars=0"], "a second time"),
    (["seed=1 won=1 stars=2"], "1 of 2 seeds"),
])
def test_a_line_that_does_not_say_what_was_declared_is_refused(lines, said):
    with pytest.raises(PolyweaveError) as refused:
        levels._read_lines(_said(*lines), MEASURES, 2)
    assert refused.value.code == "level.bad-line"
    assert said in refused.value.message


def test_a_measure_is_read_at_its_percentiles_and_its_mean():
    held = levels._aggregate({"won": [1, 1, 1, 0]}, [10, 50, 90])
    assert held == {"won": {"mean": 0.75, "p10": 0.3, "p50": 1.0, "p90": 1.0}}
    moved = levels._moved(held, {"won": {"mean": 0.95, "p10": 0.3}})
    assert moved == {"won": {"mean": {"was": 0.95, "now": 0.75}}}
    assert levels._moved(held, None) == {}


@pytest.mark.parametrize("declared", [
    {}, {"seed": {"unit": "n"}}, {"won": {"direction": "higher"}},
    {"won": {"unit": "0 or 1", "direction": "up"}}])
def test_measures_declared_without_their_terms_are_refused(declared):
    with pytest.raises(PolyweaveError) as refused:
        levels._measures(declared)
    assert refused.value.code == "level.bad-measures"


def _project(tmp_path, table=""):
    (tmp_path / "polyweave.toml").write_text(table, encoding="utf-8")
    (tmp_path / "project.godot").write_text("config_version=5\n", encoding="utf-8")
    (tmp_path / "levels").mkdir()
    (tmp_path / "levels" / "one.json").write_text('{"moves": 20}', encoding="utf-8")
    return tmp_path


DECLARED = ('[levels]\nprobe = "res://probe.gd"\nseeds = 4\n\n[levels.measures]\n'
            'won = { unit = "0 or 1", direction = "higher" }\n'
            'stars = { unit = "stars", direction = "higher" }\n')


def test_a_project_with_no_probe_or_no_level_is_refused(tmp_path):
    root = _project(tmp_path)
    with pytest.raises(PolyweaveError) as refused:
        levels.probe("levels/one.json", root=str(root))
    assert refused.value.code == "level.no-probe"
    (root / "polyweave.toml").write_text(DECLARED, encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        levels.probe("levels/none.json", root=str(root))
    assert refused.value.code == "level.no-level"


#: A probe that plays nothing: its numbers follow from the seed and the level's moves,
#: so two runs agree and a changed level moves them.
PROBE = """extends SceneTree

func _initialize() -> void:
\tvar level := ""
\tvar seeds := 0
\tfor arg in OS.get_cmdline_user_args():
\t\tif arg.begins_with("level="):
\t\t\tlevel = arg.substr(6)
\t\telif arg.begins_with("seeds="):
\t\t\tseeds = int(arg.substr(6))
\tvar moves := int(JSON.parse_string(FileAccess.get_file_as_string(level))["moves"])
\tfor n in range(1, seeds + 1):
\t\tvar won := 1 if n % 4 != 0 else 0
\t\tprint("level: seed=%d won=%d stars=%d" % [n, won, won * int(moves / 10.0)])
\tquit()
"""


def test_the_game_s_probe_plays_a_level_and_a_change_is_reported(tmp_path):
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    root = _project(tmp_path, DECLARED)
    (root / "probe.gd").write_text(PROBE, encoding="utf-8")
    first = levels.probe("levels/one.json", root=str(root))
    assert first["probe"] == "levels/one.probe.json"
    assert first["measured"]["won"]["mean"] == 0.75
    assert first["measured"]["stars"]["p90"] == 2.0
    assert first["moved"] == {}
    record = provenance.read(first["probe"], root=str(root))
    assert {one["role"] for one in record["inputs"]} == {"level", "probe"}
    assert record["engine"]["version"].startswith("v4")
    (root / "levels" / "one.json").write_text('{"moves": 30}', encoding="utf-8")
    again = levels.probe("levels/one.json", root=str(root))
    assert again["moved"]["stars"]["p90"] == {"was": 2.0, "now": 3.0}
    written = json.loads((root / "levels" / "one.probe.json").read_text("utf-8"))
    assert written["seeds"] == 4 and written["measures"]["won"]["unit"] == "0 or 1"
