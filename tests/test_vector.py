"""A vector logo drawn whole and in layers, with its record (§PW315)."""

from __future__ import annotations

import os
import shutil

import numpy as np
import pytest
from PIL import Image

from polyweave import provenance, vector
from polyweave.errors import PolyweaveError

LOGO = """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50"
  viewBox="0 0 100 50">
  <defs>
    <filter id="soft" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="4"/>
    </filter>
  </defs>
  <g><circle cx="25" cy="25" r="12" fill="#ff00ff" filter="url(#soft)"/></g>
  <g id="ring">
    <circle cx="70" cy="25" r="15" fill="none" stroke="#00ffff" stroke-width="4"/>
  </g>
  <g><rect x="5" y="40" width="20" height="5" fill="#ffffff"/></g>
</svg>
"""


@pytest.fixture
def logo(tmp_path):
    (tmp_path / "brand").mkdir()
    (tmp_path / "brand" / "logo.svg").write_text(LOGO, encoding="utf-8")
    return tmp_path


def needs_godot():
    if not (os.environ.get("GODOT") or shutil.which("godot")):
        pytest.skip("no $GODOT on this machine: the engine draws a vector")


def test_a_layer_naming_nothing_is_refused_with_the_choices(logo):
    with pytest.raises(PolyweaveError) as refused:
        vector.vector(
            "brand/logo.svg", "out/logo.png", 400, layers={"halo": "#glow"},
            root=str(logo),
        )
    assert refused.value.code == "compose.no-layer"
    assert set(refused.value.as_dict()["allowed"]) == {"1", "2", "3", "#ring"}


@pytest.mark.parametrize(
    ("sweep", "said"),
    [
        ({"element": "#orbit", "attribute": "r", "from": 0, "to": 1, "frames": 4},
         "no element #orbit"),
        ({"element": "#ring", "attribute": "r", "from": 0, "to": 1}, "no frames"),
        ({"element": "#ring", "attribute": "r", "from": 0, "to": 1, "frames": 1},
         "2 to 256"),
        ({"element": "#ring", "attribute": "r", "from": "a", "to": 1, "frames": 4},
         "as numbers"),
    ],
)
def test_a_sweep_that_cannot_be_drawn_is_refused(logo, sweep, said):
    with pytest.raises(PolyweaveError) as refused:
        vector.vector("brand/logo.svg", "out/logo.png", 400, sweep=sweep,
                      root=str(logo))
    assert refused.value.code == "compose.bad-sweep"
    assert said in refused.value.message + refused.value.remedy


def test_nothing_to_draw_is_refused(logo):
    with pytest.raises(PolyweaveError) as refused:
        vector.vector("brand/logo.svg", "out/logo.png", 400, whole=False,
                      root=str(logo))
    assert refused.value.code == "compose.no-layer"


def test_a_layer_swept_over_frames_is_one_loop_with_one_source(logo):
    """§PW476: a turning ring is one source and one sweep, not eight hand-made SVGs."""
    needs_godot()
    made = vector.vector(
        "brand/logo.svg", "out/logo.png", 200, layers={"ring": "#ring"},
        sweep={"element": "#ring", "attribute": "opacity", "from": 1.0, "to": 0.0,
               "frames": 4},
        strip=True, whole=False, root=str(logo),
    )
    # Layers alone: the whole picture the game never draws is not written.
    assert "whole" not in made
    assert not (logo / "out" / "logo.png").exists()
    ring = made["layers"]["ring"]
    assert ring["frames"] == [f"out/logo.ring.{k:02d}.png" for k in range(4)]
    # The end is left out, so the fourth frame steps back into the first.
    assert made["sweep"]["values"] == [1.0, 0.75, 0.5, 0.25]
    record = provenance.read(str(logo / ring["frames"][2]), root=logo)
    assert record["inputs"][0]["path"] == "brand/logo.svg"
    assert record["params"]["frame"] == 2
    assert record["params"]["sweep"]["attribute"] == "opacity"

    def alpha(name):
        with Image.open(logo / name) as opened:
            return np.asarray(opened.convert("RGBA"))[..., 3].astype(float)

    peaks = [alpha(name).max() for name in ring["frames"]]
    assert peaks == sorted(peaks, reverse=True) and peaks[0] > peaks[-1] + 100
    strip = alpha(ring["strip"])
    assert strip.shape == (100, 800)
    assert provenance.read(str(logo / ring["strip"]), root=logo)["params"][
        "frames"] == ring["frames"]


HALO = """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50"
  viewBox="0 0 100 50">
  <defs>
    <filter id="halo"><feGaussianBlur stdDeviation="4"/></filter>
  </defs>
  <g id="halo" filter="url(#halo)"><circle cx="25" cy="25" r="12" fill="#ff00ff"/></g>
  <g id="ring"><circle cx="70" cy="25" r="15" fill="#00ffff"/></g>
  <g id="hidden" opacity="0"><rect x="5" y="40" width="20" height="5"/></g>
</svg>
"""


def test_an_id_two_elements_share_is_refused_naming_both(logo):
    """§PW478: Spinhold's halo group and its blur filter were both #halo."""
    (logo / "brand" / "halo.svg").write_text(HALO, encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        vector.vector("brand/halo.svg", "out/halo.png", 200, layers={"ring": "#ring"},
                      root=str(logo))
    assert refused.value.code == "compose.ambiguous-id"
    assert '<filter id="halo">' in refused.value.message
    assert '<g id="halo">' in refused.value.message


def test_a_filter_that_points_at_no_filter_is_refused(logo):
    body = HALO.replace('<filter id="halo">', '<filter id="soft">').replace(
        'filter="url(#halo)"', 'filter="url(#ring)"')
    (logo / "brand" / "halo.svg").write_text(body, encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        vector.vector("brand/halo.svg", "out/halo.png", 200, root=str(logo))
    assert refused.value.code == "compose.ambiguous-id"
    assert "not a filter" in refused.value.message


def test_a_layer_that_draws_nothing_is_refused(logo):
    needs_godot()
    body = HALO.replace('<filter id="halo">', '<filter id="soft">').replace(
        'url(#halo)', 'url(#soft)')
    (logo / "brand" / "halo.svg").write_text(body, encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        vector.vector("brand/halo.svg", "out/halo.png", 200,
                      layers={"ring": "#ring", "hidden": "#hidden"}, root=str(logo))
    assert refused.value.code == "compose.empty-layer"
    assert "layer hidden (#hidden)" in refused.value.message


def test_a_sweep_frame_that_draws_nothing_is_said(logo):
    needs_godot()
    made = vector.vector(
        "brand/logo.svg", "out/logo.png", 200, layers={"ring": "#ring"},
        sweep={"element": "#ring", "attribute": "opacity", "from": 0.0, "to": 1.0,
               "frames": 4},
        whole=False, root=str(logo))
    assert made["empty_frames"] == {"ring": [0]}


def test_a_missing_vector_is_refused(logo):
    with pytest.raises(PolyweaveError) as refused:
        vector.vector("brand/none.svg", "out/logo.png", 400, root=str(logo))
    assert refused.value.code == "compose.no-vector"


def test_the_whole_and_its_layers_are_drawn_on_one_canvas(logo):
    needs_godot()
    made = vector.vector(
        "brand/logo.svg",
        "out/logo.png",
        400,
        layers={"halo": 1, "ring": "#ring", "letters": "3"},
        root=str(logo),
    )
    assert made["whole"]["size"] == [400, 200]
    assert set(made["layers"]) == {"halo", "ring", "letters"}
    assert made["layers"]["ring"]["file"] == "out/logo.ring.png"
    record = provenance.read(str(logo / "out" / "logo.ring.png"), root=logo)
    assert record["inputs"][0]["role"] == "vector"
    assert record["inputs"][0]["path"] == "brand/logo.svg"
    assert record["params"]["layer"] == "ring"

    def alpha(name):
        with Image.open(logo / name) as opened:
            return np.asarray(opened.convert("RGBA"))[..., 3].astype(float)

    # The blur came through: the halo's edge ramps rather than stepping.
    halo = alpha("out/logo.halo.png")
    edge = halo[100, :100]
    assert ((edge > 10) & (edge < 245)).sum() > 10
    # Each layer holds only its own part, and together they cover the whole.
    ring = alpha("out/logo.ring.png")
    assert ring[:, :180].max() == 0 and ring.max() > 0
    whole = alpha("out/logo.png")
    stacked = np.maximum.reduce(
        [halo, ring, alpha("out/logo.letters.png")]
    )
    assert np.abs(stacked - whole).max() <= 2
