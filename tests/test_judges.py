"""A layer registers the judge for what it lays out (§PW501)."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

import polyweave.layers
from polyweave.kernel import layer as L
from polyweave.kernel.describe import describe
from polyweave.kernel.errors import PolyweaveError
from polyweave.loop import verdict

LAYER = '''
from polyweave.kernel.layer import Judge, Layer

LAYER = Layer(
    name="haptics",
    summary="A fixture medium a person judges by feel.",
    modules=(),
    judges=(
        Judge(
            name="felt",
            about="a buzz is kept in the fixture's own file",
            claims=lambda member: bool(member.get("buzz")),
            target="polyweave.layers.haptics.felt:judged",
        ),
    ),
)
'''

FELT = '''
import json
from pathlib import Path


def judged(member, *, accepted, choice, why, when, root):
    kept = {"buzz": member["buzz"], "accepted": accepted, "why": why}
    (Path(root) / "felt.json").write_text(json.dumps(kept), encoding="utf-8")
    return kept
'''


@pytest.fixture
def haptics(tmp_path, monkeypatch):
    """A layer declared outside the package, beside the real ones."""
    shelf = tmp_path / "shelf" / "haptics"
    shelf.mkdir(parents=True)
    (shelf / "__init__.py").write_text("", encoding="utf-8")
    (shelf / "layer.py").write_text(LAYER, encoding="utf-8")
    (shelf / "felt.py").write_text(FELT, encoding="utf-8")
    monkeypatch.setattr(
        polyweave.layers, "__path__", [*polyweave.layers.__path__, str(shelf.parent)]
    )
    L.layers.cache_clear()
    yield tmp_path
    monkeypatch.undo()
    L.layers.cache_clear()
    for name in [m for m in sys.modules if m.startswith("polyweave.layers.haptics")]:
        del sys.modules[name]


def test_verdict_imports_nothing_from_a_layer():
    source = Path(verdict.__file__).read_text(encoding="utf-8")
    imported = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
        elif isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
    assert [m for m in imported if m.startswith("polyweave.layers")] == []


def test_a_judge_a_layer_declares_receives_its_member(haptics):
    said = verdict.judge(
        [{"name": "buzz", "new": "buzz.png", "buzz": "short"}],
        "accept",
        "it feels right",
        root=haptics,
    )
    assert said["members"][0]["felt"] == {
        "buzz": "short", "accepted": True, "why": "it feels right"}
    assert json.loads((haptics / "felt.json").read_text(encoding="utf-8"))["buzz"]


def test_a_member_no_judge_claims_reports_nothing_beyond_the_shared_record(tmp_path):
    said = verdict.judge(
        [{"name": "plain", "new": "plain.png"}], "accept", "fine", root=tmp_path
    )
    assert set(said["members"][0]) == {
        "name", "tool_passed", "person_accepted", "named", "rewritten", "check"}


def test_two_judges_claiming_one_member_are_refused_before_anything_is_kept(
    tmp_path,
):
    member = {"name": "both", "new": "both.png", "canon": "characters", "line": "hi"}
    with pytest.raises(PolyweaveError) as refused:
        verdict.judge([member], "accept", "both at once", root=tmp_path)
    assert refused.value.code == "verdict.judged-twice"
    assert sorted(refused.value.allowed) == ["canon", "line"]
    assert list(tmp_path.iterdir()) == []


def test_a_spoken_take_is_the_sounds_verdict_by_the_words_layers_own_claim():
    take = {"name": "hello", "new": "hello.wav", "sound": True, "line": "Hello."}
    assert L.judge_of(take).name == "heard"


def test_describe_says_where_each_kind_of_verdict_lives():
    judges = describe("verdict.judge")["declares"]["judges"]
    assert set(judges) == {"canon", "heard", "line", "row"}
    assert all(about for about in judges.values())
