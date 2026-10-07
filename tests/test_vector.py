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
