"""A refused name says which names would have worked (§PW128)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from polyweave import describe, loop
from polyweave.errors import PolyweaveError, near
from polyweave.render import ladder

SOURCE = Path(__file__).parents[1] / "src" / "polyweave"

#: Raises under an unknown-name code that do not yet pass `allowed`. It may only fall:
#: a site converted lowers it, and a new site must pass `allowed` from the start.
UNCONVERTED = 0


def unknown_name_raises() -> list[tuple[str, int, bool]]:
    found = []
    for path in sorted(SOURCE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and getattr(node.func, "id", None) == "PolyweaveError"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and ".unknown" in str(node.args[0].value)
            ):
                passes = any(k.arg == "allowed" for k in node.keywords)
                found.append((f"{path.name}:{node.lineno}", node.args[0].value, passes))
    return found


def test_the_unconverted_unknown_name_raises_only_shrink():
    left = [where for where, _, passes in unknown_name_raises() if not passes]
    assert len(left) <= UNCONVERTED, "a new unknown-name raise must pass allowed="
    assert len(left) == UNCONVERTED, f"it shrank to {len(left)}: lower UNCONVERTED"


@pytest.mark.parametrize(
    ("given", "allowed", "meant"),
    [
        ("Luma_P99", ["luma_p99", "luma_p50"], "luma_p99"),
        ("exposur", ["exposure", "elevation", "azimuth"], "exposure"),
        ("sphere-rung", ["sphere_rung", "final"], "sphere_rung"),
        ("zzz", ["exposure", "elevation"], None),
        ("final", ["final", "preview"], None),
    ],
)
def test_the_nearest_name_is_found_or_none_is_offered(given, allowed, meant):
    assert near(given, allowed) == meant


def test_a_tie_is_broken_the_same_way_every_time():
    assert near("cat", ["cot", "cut"]) == near("cat", ["cut", "cot"])


def test_a_refused_rung_carries_the_names_and_the_nearest():
    with pytest.raises(PolyweaveError) as refused:
        ladder.check_rung("Preveiw")
    wire = refused.value.as_dict()
    assert wire["allowed"] == sorted(ladder.RUNGS)
    assert wire["did_you_mean"] == "preview"


def test_every_example_a_refusal_prints_is_accepted_fed_back():
    for call, bad in ((ladder.check_rung, "draft"), (ladder.rung_for, "lumaa")):
        with pytest.raises(PolyweaveError) as refused:
            call(bad)
        assert call(refused.value.example)


def test_an_unknown_argument_names_the_ones_the_operation_takes():
    with pytest.raises(PolyweaveError) as refused:
        describe.validate("render.plan", {"asknig": ["luma_p99"]})
    assert refused.value.did_you_mean == "asking"
    assert "floor" in refused.value.allowed


def test_a_misspelt_config_key_names_the_one_meant_and_where(tmp_path):
    from polyweave import config

    (tmp_path / "polyweave.toml").write_text(
        "[render]\npreveiw_size = 128\n", encoding="utf-8"
    )
    with pytest.raises(PolyweaveError) as refused:
        config.load(tmp_path)
    assert refused.value.did_you_mean == "preview_size"
    assert refused.value.at == "render.preveiw_size"


def test_the_fields_are_left_out_when_empty_and_survive_the_wire(tmp_path):
    bare = PolyweaveError("op.unknown", "m", "r")
    assert set(bare.as_dict()) == {"code", "message", "remedy"}
    with pytest.raises(PolyweaveError) as refused:
        loop.start("star", "sideways", root=tmp_path)
    back = PolyweaveError.from_dict(refused.value.as_dict())
    assert back.allowed == ["after", "before"]
