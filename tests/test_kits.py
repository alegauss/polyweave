"""The kit contract: what a kit is, checked before any project receives it (§PW340)."""

from __future__ import annotations

import json

import pytest

from polyweave import kits
from polyweave.errors import PolyweaveError

KIT = """name = "{name}"
version = "0.1.0"
summary = "rebindable controls, read from the project's InputMap"
requires = {requires}

[installs]
core = "core"
scene = "scene/controls.tscn"

[declares]
layouts = ["xbox", "playstation", "switch", "generic", "keyboard"]

[proves]
spec = "proof.accept.toml"
fixture = "fixture"
"""


def kit(under, name, *, requires=(), body=None):
    folder = under / name
    (folder / "core").mkdir(parents=True)
    (folder / "scene").mkdir()
    (folder / "scene" / "controls.tscn").write_text("[gd_scene format=3]\n", "utf-8")
    (folder / "proof.accept.toml").write_text(f'asset = "{name}"\n', "utf-8")
    (folder / "fixture").mkdir()
    text = body or KIT.format(name=name, requires=json.dumps(list(requires)))
    (folder / "kit.toml").write_text(text, encoding="utf-8")
    return folder


def test_a_kit_that_keeps_the_contract_is_read_whole(tmp_path):
    kit(tmp_path, "input")
    found = kits.every(tmp_path)
    assert list(found) == ["input"]
    one = found["input"]
    assert one["version"] == "0.1.0"
    assert one["installs"] == {"core": "core", "scene": "scene/controls.tscn"}
    assert one["proves"] == {"spec": "proof.accept.toml", "fixture": "fixture"}
    assert one["declares"]["layouts"][2] == "switch"


def test_the_plugin_lists_the_kits_it_carries():
    said = kits.listed()
    assert said["kits"] == [
        {k: one[k] for k in ("name", "version", "summary", "requires")}
        for one in kits.every().values()
    ]


@pytest.mark.parametrize("change", [
    ('name = "input"', 'name = "controls"'),
    ('version = "0.1.0"', 'version = "1"'),
    ('spec = "proof.accept.toml"', 'spec = "missing.accept.toml"'),
    ('[proves]\nspec = "proof.accept.toml"\n', ""),
    ('core = "core"', 'core = "core"\ntheme = "dark"'),
    ('summary = ', 'palette = "warm"\nsummary = '),
])
def test_a_kit_that_breaks_the_contract_is_refused(tmp_path, change):
    body = KIT.format(name="input", requires="[]").replace(*change)
    kit(tmp_path, "input", body=body)
    with pytest.raises(PolyweaveError) as refused:
        kits.every(tmp_path)
    assert refused.value.code == "kits.bad"


def test_a_kit_requires_only_kits_there_are_and_never_in_a_loop(tmp_path):
    kit(tmp_path, "settings", requires=["input"])
    with pytest.raises(PolyweaveError) as missing:
        kits.every(tmp_path)
    assert "requires input" in missing.value.message
    kit(tmp_path, "input", requires=["settings"])
    with pytest.raises(PolyweaveError) as looped:
        kits.every(tmp_path)
    assert "loop" in looped.value.message
