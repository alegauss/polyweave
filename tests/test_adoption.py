"""Whether a real project can be configured rather than forked.

§PW36's question. Cottony is the first consumer and not the specification, so anything
it needs that a second project would not is configuration — and a default that cannot be
overridden is a defect. The way to find out is to write that project's config against
the constants it actually has and see what has nowhere to go.

`tests/fixtures/cottony.toml` is that config, every value read off a constant in
D:\\Git\\viglet\\cottony. This file is the gate on it: a key renamed inside the plugin
turns these red, which is a real consumer noticing before the consumer does.

What the audit came to is in docs/specs/adoption.md. The short version is that paths,
binaries, the sample ladder, the seed, the service, the units source and the capture
environment all had a key already, and two things did not: the render rig's parameter
*names*, which turned out to be a silent mismatch rather than a missing key, and the
shell-based fluff, which is a technique and not a number.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

from polyweave import accept, config, render, search
from polyweave.errors import PolyweaveError

FIXTURE = Path(__file__).parent / "fixtures" / "cottony.toml"


@pytest.fixture
def cottony(tmp_path):
    """Cottony's config, in a tree the loader will accept."""
    (tmp_path / "polyweave.toml").write_text(
        FIXTURE.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return tmp_path


# -- the config boundary ---------------------------------------------------------------


def test_a_real_project_loads_with_no_unknown_key(cottony):
    """The test of the boundary: no key Cottony needs is one the plugin refuses."""
    assert config.load(cottony).get("project.name") == "cottony"


def test_every_constant_it_had_resolves_to_the_value_it_had(cottony):
    """Read off Cottony's own files, so a wrong answer here is a wrong mapping."""
    found = config.load(cottony)
    assert found.get("render.seed") == 7, "bake_model.py SEED"
    assert found.get("render.samples")["final"] == 320, "bake_model.py SAMPLES"
    assert found.get("paths.meshes") == "tools/art/3d", "MODELS_DIR"
    assert found.get("paths.renders") == "docs/design/art", "ART"
    assert found.get("units.source") == "scripts/board.gd:CELL"
    assert found.get("capture.resolution") == [1080, 1920], "project.godot viewport"


def test_the_ladder_top_matches_what_the_old_pipeline_rendered_at(cottony):
    """Or the two ways are not comparable, and §PW35's measurement means nothing."""
    found = config.load(cottony)
    assert found.get("render.samples")[found.get("render.rungs")[-1]] == 320


def test_a_project_that_buys_nothing_more_says_so_with_a_zero(cottony):
    """The meshes are bought and in the lock file; adoption does not re-buy them."""
    found = config.load(cottony)
    assert found.get("budget.credits") == 0
    assert found.get("service.base"), "it still names where the lock file came from"


def test_it_states_the_language_because_the_project_ships_two(cottony):
    """§PW25: one script on two machines gave two pictures, and nothing said why."""
    found = config.load(cottony)
    assert "locale" in found.get("capture.declared")
    assert found.get("capture.locale") == "pt_BR"


def test_no_palette_reaches_the_config(cottony):
    """The non-goal, checked rather than trusted: 41 colours stayed in Cottony."""
    text = FIXTURE.read_text(encoding="utf-8")
    assert re.findall(r"#[0-9A-Fa-f]{3,8}\b", text) == [], "a colour leaking in"


# -- what the adoption found: the names do not survive ---------------------------------


def test_a_spec_axis_the_renderer_has_no_knob_for_is_refused(cottony, tmp_path):
    """`light` and `form` are Cottony's names for its rig. Neither is a parameter here.

    Before §PW36 this loaded, `ranges` returned the axis, and the search died on the
    first sample with a bare TypeError — after the setup was paid for.
    """
    spec = _spec(tmp_path, "light")
    with pytest.raises(PolyweaveError) as caught:
        search.renderer(spec, out="r.png", root=tmp_path)
    assert caught.value.code == "search.unknown-parameter"


def test_it_is_refused_before_a_single_render_is_spent(cottony, tmp_path):
    """The cost of finding out late is the whole reason the check sits here."""
    spent = []

    def draw(report, out, rung, root, inline, key=0.0):
        spent.append(key)  # pragma: no cover - never reached, which is the point

    spec = _spec(tmp_path, "form")
    with pytest.raises(PolyweaveError):
        search.renderer(spec, out="r.png", root=tmp_path, bake=draw)
    assert spent == []


def test_a_near_miss_is_named(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        search.renderer(_spec(tmp_path, "fil"), out="r.png", root=tmp_path)
    assert "fill" in caught.value.remedy


def test_a_parameter_the_renderer_does_take_is_searchable(tmp_path):
    assert search.renderer(_spec(tmp_path, "key"), out="r.png", root=tmp_path)


def test_a_fixed_value_is_checked_the_same_way(tmp_path):
    """It reaches the renderer by the same splat, so it fails the same way."""
    with pytest.raises(PolyweaveError) as caught:
        search.renderer(
            _spec(tmp_path, "key"), out="r.png", root=tmp_path, fixed={"light": 1.18}
        )
    assert caught.value.code == "search.unknown-parameter"


def test_a_renderer_that_takes_anything_is_not_second_guessed(tmp_path):
    """A stand-in written for a test has said it accepts anything, and it does."""

    def anything(report, **values):  # pragma: no cover - never called here
        return {}

    assert search.renderer(
        _spec(tmp_path, "light"), out="r.png", root=tmp_path, bake=anything
    )


def test_the_spec_worked_example_names_parameters_that_exist(tmp_path):
    """The example in docs/specs/acceptance-spec.md used to name two that did not."""
    doc = Path(__file__).parents[1] / "docs" / "specs" / "acceptance-spec.md"
    named = [
        line.split(".", 1)[1].rstrip("]")
        for line in doc.read_text(encoding="utf-8").splitlines()
        if line.startswith("[search.")
    ]
    takes = inspect.signature(render.bake).parameters
    assert named, "the example still shows how a range is written"
    assert [n for n in named if n not in takes] == []


def _spec(root: Path, axis: str):
    """One predicate and one search range, which is the least a search needs."""
    where = root / f"{axis}.accept.toml"
    where.write_text(
        "asset = 'mascot'\n"
        "rung = 'preview'\n"
        "[[predicate]]\n"
        "id = 'reads-cream'\n"
        "measure = 'delta_e'\n"
        "target = '#E8D5C4'\n"
        "max = 2.0\n"
        f"[search.{axis}]\n"
        "min = 0.5\n"
        "max = 4.0\n",
        encoding="utf-8",
    )
    return accept.read(where)
