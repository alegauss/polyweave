"""A look declares its asks and writes itself to each target (§PW515)."""

from __future__ import annotations

import inspect
import re
import sys
from pathlib import Path

import pytest

from polyweave.layers.geometry import looks
from polyweave.layers.geometry.render import blender
from polyweave.layers.geometry.representations import mesh

TOON = '''
from pathlib import Path

from . import Look


def _bake(material):
    out = {key: value for key, value in material.items() if key != "toon"}
    if "toon" in material:
        out["toon_bands"] = int(material["toon"])
    return out


def _godot(material, name, folder, stem, root):
    where = Path(folder) / f"{stem}.{name}.toon.tres"
    where.write_text(f"bands = {material['toon']}", encoding="utf-8")
    return [where]


LOOK = Look(
    name="toon",
    asks=("toon",),
    asked=lambda material: isinstance(material, dict) and "toon" in material,
    says=lambda material: f"a toon of {material['toon']} bands"
    if isinstance(material, dict) and "toon" in material else "",
    bake=_bake,
    godot=_godot,
)
'''


def test_neither_the_bake_nor_write_names_a_look():
    reaching = re.compile(r"finish\.|surface\.|import [\w ,]*(finish|surface)")
    for function in (blender.as_inputs, mesh.write):
        assert not reaching.search(inspect.getsource(function)), function.__name__


def test_the_finish_and_the_fuzz_are_the_first_two_looks():
    found = looks.every()
    assert list(found) == ["fuzz", "finish"]
    assert found["finish"].targets == ("bake", "godot")
    # A fuzz reaches neither target yet, and says so rather than being dropped.
    assert found["fuzz"].targets == ()


def test_a_finish_is_still_expanded_for_the_shader():
    said = looks.baked({"colour": "#ffffff", "sheen": 0.4})
    assert said["sheen_weight"] == 0.4 and "sheen" not in said


@pytest.fixture
def toon(tmp_path, monkeypatch):
    (tmp_path / "shelf").mkdir()
    (tmp_path / "shelf" / "toon.py").write_text(TOON, encoding="utf-8")
    monkeypatch.setattr(looks, "__path__", [*looks.__path__, str(tmp_path / "shelf")])
    looks.every.cache_clear()
    yield tmp_path
    monkeypatch.undo()
    looks.every.cache_clear()
    sys.modules.pop("polyweave.layers.geometry.looks.toon", None)


def test_a_new_look_reaches_both_targets_from_one_file(toon):
    material = {"colour": "#ff0000", "toon": 3}
    assert looks.baked(material)["toon_bands"] == 3
    [written] = looks.godot(material, "red", toon, "box", toon)
    assert Path(written).read_text(encoding="utf-8") == "bands = 3"
    assert "a toon of 3 bands" in looks.says(material)
