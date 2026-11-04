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


SPEC = """asset = "one"
artefact = "levels/one.json"

[[predicate]]
id = "wins"
measure = "level"
probed = "won"
at = "mean"
min = 0.45
max = 0.70

[[predicate]]
id = "three-stars"
measure = "level"
probed = "stars"
at = "p90"
min = 3
"""


def _probed(root, won=0.6, stars=3.0):
    """A level as level.probe leaves it: its record beside it, the level an input."""
    target = root / "levels" / "one.probe.json"
    target.write_text(json.dumps({"measured": {
        "won": {"mean": won, "p50": 1.0}, "stars": {"mean": 2.0, "p90": stars}}}),
        encoding="utf-8")
    provenance.write(provenance.build(
        "capture", target, root=root,
        inputs=[provenance.source("level", root / "levels" / "one.json", root=root)]),
        root=root)
    (root / "one.accept.toml").write_text(SPEC, encoding="utf-8")


def test_a_level_spec_is_checked_off_the_probe_s_record(tmp_path):
    from polyweave.loop import accept

    root = _project(tmp_path, DECLARED)
    _probed(root)
    said = accept.checked("one.accept.toml", "levels/one.json", root=str(root))
    assert said["passed"] is True
    assert [(one["id"], one["value"]) for one in said["predicates"]] == [
        ("wins", 0.6), ("three-stars", 3.0)]
    _probed(root, won=0.9, stars=2.0)
    said = accept.checked("one.accept.toml", "levels/one.json", root=str(root))
    assert said["failed"] == ["wins", "three-stars"]


def test_a_level_changed_since_its_probe_or_never_probed_is_refused(tmp_path):
    from polyweave.loop import accept

    root = _project(tmp_path, DECLARED)
    (root / "one.accept.toml").write_text(SPEC, encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        accept.checked("one.accept.toml", "levels/one.json", root=str(root))
    assert refused.value.code == "level.unprobed"
    _probed(root)
    (root / "levels" / "one.json").write_text('{"moves": 12}', encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        accept.checked("one.accept.toml", "levels/one.json", root=str(root))
    assert refused.value.code == "level.unprobed"
    assert "changed since it was probed" in refused.value.message


def test_a_measure_the_probe_did_not_record_is_refused(tmp_path):
    from polyweave.loop import accept

    root = _project(tmp_path, DECLARED)
    _probed(root)
    (root / "one.accept.toml").write_text(SPEC.replace('probed = "won"',
                                                       'probed = "lives"'),
                                          encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        accept.checked("one.accept.toml", "levels/one.json", root=str(root))
    assert refused.value.code == "level.bad-measures"


def _set(root, wins, **shape):
    """Levels one by one with the win rate each was probed at, and a set spec over
    them in that order."""
    names = []
    for n, won in enumerate(wins, start=1):
        level = root / "levels" / f"l{n}.json"
        level.write_text(json.dumps({"n": n}), encoding="utf-8")
        target = root / "levels" / f"l{n}.probe.json"
        target.write_text(json.dumps({"measured": {"won": {"mean": won}}}),
                          encoding="utf-8")
        provenance.write(provenance.build(
            "capture", target, root=root,
            inputs=[provenance.source("level", level, root=root)]), root=root)
        names.append(f"levels/l{n}.json")
    lines = [f"levels = {json.dumps(names)}", 'probed = "won"', 'at = "mean"']
    lines += [f"{key} = {json.dumps(value)}" for key, value in shape.items()]
    (root / "all.levels.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return "all.levels.toml"


def test_a_set_whose_difficulty_rises_holds_its_curve(tmp_path):
    root = _project(tmp_path, DECLARED)
    said = levels.curve(_set(root, [0.95, 0.9, 0.92, 0.7], step=0.05,
                             regions=[[1, 4]]), root=str(root))
    assert said["ok"] is True
    assert said["values"] == {"l1": 0.95, "l2": 0.9, "l3": 0.92, "l4": 0.7}


def test_each_break_of_the_curve_is_the_pair_that_broke_it(tmp_path):
    root = _project(tmp_path, DECLARED)
    said = levels.curve(_set(root, [0.9, 0.7, 0.95, 0.6, 0.65], step=0.05,
                             regions=[[1, 3]], dips=[4]), root=str(root))
    found = {(one["rule"], tuple(one["pair"])) for one in said["findings"]}
    assert found == {("step", ("l2", "l3")), ("region", ("l1", "l3"))}
    # the dip after l4 is easier than l4, as declared, so it is no break
    dipless = levels.curve(_set(root, [0.9, 0.7, 0.6, 0.5, 0.4], dips=[4]),
                           root=str(root))
    assert [one["rule"] for one in dipless["findings"]] == ["dip"]


@pytest.mark.parametrize("shape", [{"regions": [[3, 1]]}, {"dips": [9]},
                                   {"step": -1}])
def test_a_set_that_says_no_shape_is_refused(tmp_path, shape):
    root = _project(tmp_path, DECLARED)
    with pytest.raises(PolyweaveError) as refused:
        levels.curve(_set(root, [0.9, 0.8, 0.7], **shape), root=str(root))
    assert refused.value.code == "level.bad-set"


def test_a_searched_value_goes_to_its_dotted_path_and_keeps_its_type():
    level = {"moves": 20, "goals": [{"count": 8, "share": 0.5}]}
    levels._set_at(level, "moves", 33.6)
    levels._set_at(level, "goals.0.share", 0.75)
    levels._set_at(level, "goals.0.count", 11.0)
    assert level == {"moves": 34, "goals": [{"count": 11, "share": 0.75}]}
    assert isinstance(level["goals"][0]["count"], int)
    with pytest.raises(PolyweaveError) as refused:
        levels._set_at(level, "goals.3.count", 1)
    assert refused.value.code == "level.bad-set"


SEARCHED = """asset = "one"

[[predicate]]
id = "three-stars"
measure = "level"
probed = "stars"
at = "p90"
min = 3

[search.moves]
min = 10
max = 40
step = 10
"""


def test_a_search_turns_a_level_until_its_probe_passes(tmp_path):
    if not os.environ.get("GODOT"):
        pytest.skip("no $GODOT on this machine")
    from polyweave.loop import search

    root = _project(tmp_path, DECLARED)
    (root / "probe.gd").write_text(PROBE, encoding="utf-8")
    (root / "one.accept.toml").write_text(SEARCHED, encoding="utf-8")
    found = search.sweep("one.accept.toml", out="work/one.json", producer="level",
                         fixed={"level": "levels/one.json"}, budget=6, points=4,
                         root=str(root))
    assert found["best"]["moves"] >= 30
    assert (root / "work" / "one.probe.json").is_file()


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
