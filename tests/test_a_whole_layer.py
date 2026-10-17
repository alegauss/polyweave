"""A whole layer added from outside, touching no kernel file (§PW512).

Each seam has its own fixture beside its own test. This one is every seam at once, in a
layer that stands for the next medium: `tests/fixtures/layers/tone/`, a sine tone
made from a declaration. The layer search is pointed at that folder, the way a
project's own layers will be found, and each surface is asked whether the layer is in
it. A kernel file the next medium has to open shows up here first, as a test that
cannot pass without one.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

import polyweave
import polyweave.layers
from polyweave.kernel import codes as K
from polyweave.kernel import config as C
from polyweave.kernel import layer as L
from polyweave.kernel import provenance
from polyweave.kernel.describe import _REGISTRY, describe
from polyweave.kernel.errors import PolyweaveError, explain
from polyweave.loop import accept, review, search, verdict
from polyweave.surface import brief, census, project, server
from polyweave.surface.report import report

SHELF = Path(__file__).parent / "fixtures" / "layers"

#: What the layer is named by anywhere: its package, its operation, its tool, its code.
NAMES = ("layers.tone", "tone.make", "tone_make", "tone.bad-pitch")

ACCEPT = '''
asset = "bell"

[[predicate]]
id = "pitched"
measure = "pitch_hz"
min = 400
max = 480

[[predicate]]
id = "short"
measure = "tone_seconds"
max = 1
'''

SEARCH = ACCEPT + '''
[search.pitch]
min = 300
max = 600
'''


def _clear():
    L.layers.cache_clear()
    K._every.cache_clear()
    C._schema.cache_clear()


@pytest.fixture
def shelve(tmp_path, monkeypatch):
    """Put the tone layer found at `shelf` beside the real ones, then take it away."""

    def put(shelf: Path = SHELF) -> Path:
        monkeypatch.setattr(
            polyweave.layers, "__path__", [*polyweave.layers.__path__, str(shelf)]
        )
        _clear()
        game = tmp_path / "game"
        game.mkdir()
        (game / C.FILENAME).write_text('[project]\nname = "bells"\n', encoding="utf-8")
        (game / "bell.tone.toml").write_text("pitch = 440\n", encoding="utf-8")
        (game / "bell.accept.toml").write_text(ACCEPT, encoding="utf-8")
        (game / "sweep.accept.toml").write_text(SEARCH, encoding="utf-8")
        return game

    yield put
    monkeypatch.undo()
    _clear()
    _REGISTRY.pop("tone.make", None)
    for name in [m for m in sys.modules if m.startswith("polyweave.layers.tone")]:
        del sys.modules[name]


def _called(tool: str, **arguments) -> dict:
    said = server.call(tool, arguments)
    assert not said["isError"], said["structuredContent"]
    return said["structuredContent"]


def proved(game: Path) -> None:
    """Every surface a layer reaches, asked whether the tone layer is in it."""
    root = str(game)
    # describe, explain and tools/list
    assert describe("tone.make")["layer"] == "tone"
    assert explain("tone.bad-pitch")["layer"] == "tone"
    listed = server.tools(blender=False, root=game)
    assert "tone_make" in {one["name"] for one in listed}
    assert server.shares()["tone"]["size"] <= server.budgets()["tone"]
    # the operation, through the tool a session calls, and its own refusal
    made = _called("tone_make", declaration="bell.tone.toml", out="bell.wav", root=root)
    assert made["pitch"] == 440.0 and made["seconds"] == 0.25
    (game / "low.tone.toml").write_text("pitch = 5\n", encoding="utf-8")
    refused = server.call(
        "tone_make", {"declaration": "low.tone.toml", "out": "low.wav", "root": root})
    assert refused["structuredContent"]["refused"]["code"] == "tone.bad-pitch"
    (game / "low.tone.toml").unlink()
    # project.check reads the layer's table, and refuses a word outside its choices
    assert not [one for one in project.check(root)["findings"]
                if one["code"].startswith("config.")]
    named = '[project]\nname = "bells"\n[tone]\nwave = "{}"\n'
    (game / C.FILENAME).write_text(named.format("saw"), encoding="utf-8")
    assert "config.bad-type" in {one["code"] for one in project.check(root)["findings"]}
    (game / C.FILENAME).write_text(named.format("square"), encoding="utf-8")
    assert C.load(game).get("tone.wave") == "square"
    assert C.load(game).get("tone.pitch") == 440.0
    # accept.check measures the tone off its file
    checked = accept.checked("bell.accept.toml", "bell.wav", root=root)
    assert checked["failed"] == [], checked
    assert 400 <= checked["predicates"][0]["value"] <= 480
    # search.sweep turns the layer's producer
    found = search.sweep("sweep.accept.toml", out="swept.wav", root=root,
                         producer="tone", budget=16)
    assert found["passed"] is True, found
    # verdict.judge hands the tone to the layer's judge, which keeps it in its own file
    said = verdict.judge([{"name": "bell", "new": "bell.wav", "hz": 440}], "accept",
                         "it rings true", root=root)
    assert said["members"][0]["tone"] == {"hz": 440, "accepted": True,
                                          "why": "it rings true"}
    assert (game / "tone.verdicts.json").exists()
    # provenance: the kind, the source the layer checks itself, and its own section
    assert "tone" in provenance.kinds()
    (game / "hum.tone.toml").write_text("pitch = 220\n", encoding="utf-8")
    assert provenance.outdated(root=root)["tone"] == ["hum.tone.toml"]
    (game / "bell.tone.toml").write_text("# the same bell\npitch = 440\n",
                                         encoding="utf-8")
    assert provenance.outdated(root=root)["outdated"] == []
    (game / "bell.tone.toml").write_text("pitch = 880\n", encoding="utf-8")
    assert [one["moved"] for one in provenance.outdated(root=root)["outdated"]] == [
        ["bell.tone.toml"]]
    # asset.brief, loop.report and the review page each carry the layer's part
    assert brief.brief("bell", root=root)["tone"] == {"declared": 2}
    assert report(root=root)["tone"]["declared"] == 2
    assert {"tone": "bell.wav"} in review.state(root=root)["tone"]
    # the census classifies its helper with no census edit
    counted = census.census()
    assert "polyweave.layers.tone.wave:write" in counted["internal"]
    assert not [one for one in counted["unclassified"] if ".tone." in one]


def test_a_layer_added_from_outside_is_in_every_surface(shelve):
    proved(shelve())


def test_no_kernel_loop_or_surface_file_names_the_layer():
    package = Path(polyweave.__file__).parent
    naming = [
        f"{path.relative_to(package)}: {name}"
        for area in ("kernel", "loop", "surface", "services")
        for path in (package / area).rglob("*.py")
        for name in NAMES
        if name in path.read_text(encoding="utf-8")
    ]
    assert naming == [], "a new layer is a folder, never a kernel edit"


@pytest.mark.parametrize(
    ("cut", "into"),
    [
        ('    codes="polyweave.layers.tone.codes",\n', ""),
        ('    config="polyweave.layers.tone.settings",\n', ""),
        ('"report:tone"', '"report:hum"'),
        ('name="tone",\n            about="a tone at a pitch"',
         'name="hum",\n            about="a tone at a pitch"'),
        ('claims=lambda member: "hz" in member', "claims=lambda member: False"),
        ('.tone.wave": ("internal"', '.tone.wave": ("pending"'),
    ],
    ids=["codes", "config", "report part", "producer", "judge", "census"],
)
def test_a_seam_broken_in_the_fixture_fails_the_proof(shelve, tmp_path, cut, into):
    shelf = tmp_path / "shelf"
    shutil.copytree(SHELF / "tone", shelf / "tone",
                    ignore=shutil.ignore_patterns("__pycache__"))
    declared = shelf / "tone" / "layer.py"
    text = declared.read_text(encoding="utf-8")
    assert text.count(cut) == 1
    declared.write_text(text.replace(cut, into), encoding="utf-8")
    with pytest.raises((AssertionError, PolyweaveError, KeyError)):
        proved(shelve(shelf))
