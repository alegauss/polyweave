"""The specs as a gate, with no render (§PW111)."""

from __future__ import annotations

import json

import pytest
from PIL import Image

from polyweave import accept, cli
from polyweave.errors import PolyweaveError

SPEC = """asset = "{name}"
{anchor}
[[predicate]]
id      = "no-hot-facet"
measure = "luma_p99"
region  = "frame"
max     = 0.37
"""

#: Flat greys by byte: 200 reads 0.578 in linear luma and 102 reads 0.133.
BRIGHT, DARK = 200, 102


def spec(tmp_path, name, *, artefact=None, byte=None):
    specs = tmp_path / "docs" / "accept"
    specs.mkdir(parents=True, exist_ok=True)
    anchor = f'artefact = "{artefact}"\n' if artefact else ""
    (specs / f"{name}.accept.toml").write_text(
        SPEC.format(name=name, anchor=anchor), encoding="utf-8"
    )
    if artefact and byte is not None:
        where = tmp_path / artefact
        where.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGBA", (16, 16), (byte, byte, byte, 255)).save(where)


def test_a_spec_can_name_the_file_it_holds_to_its_bar(tmp_path):
    spec(tmp_path, "star", artefact="sprites/star.png")
    read = accept.read(tmp_path / "docs" / "accept" / "star.accept.toml")
    assert read.artefact == "sprites/star.png"


def test_each_spec_is_checked_against_its_artefact_as_it_sits(tmp_path):
    spec(tmp_path, "star_dim", artefact="sprites/star_dim.png", byte=DARK)
    spec(tmp_path, "star_hot", artefact="sprites/star_hot.png", byte=BRIGHT)
    found = accept.verify(tmp_path)
    by = {one["asset"]: one for one in found["specs"]}
    assert by["star_dim"]["status"] == "passed"
    assert by["star_hot"]["status"] == "failed"
    assert by["star_hot"]["failed"][0].startswith("no-hot-facet: luma_p99 is 0.57")
    assert found["passed"] is False
    assert found["counts"]["failed"] == 1


def test_a_spec_naming_no_artefact_is_said_and_not_guessed(tmp_path):
    spec(tmp_path, "cloud")
    found = accept.verify(tmp_path)
    assert found["specs"][0]["status"] == "unanchored"
    assert found["passed"] is True


def test_a_missing_artefact_and_a_broken_spec_both_fail_the_gate(tmp_path):
    spec(tmp_path, "gone", artefact="sprites/gone.png")
    (tmp_path / "docs" / "accept" / "bad.accept.toml").write_text(
        "asset = 'bad'\nwho = 'me'\n", encoding="utf-8"
    )
    found = accept.verify(tmp_path)
    assert {one["status"] for one in found["specs"]} == {"missing", "refused"}
    assert found["passed"] is False


def test_the_command_fails_ci_on_a_spec_that_fails(tmp_path, capsys):
    spec(tmp_path, "star_hot", artefact="sprites/star_hot.png", byte=BRIGHT)
    assert cli.main(["verify", "--root", str(tmp_path)]) == 1
    printed = capsys.readouterr().out
    assert "failed     docs/accept/star_hot.accept.toml" in printed
    assert "1 failed" in printed


def test_the_command_passes_and_speaks_json(tmp_path, capsys):
    spec(tmp_path, "star_dim", artefact="sprites/star_dim.png", byte=DARK)
    assert cli.main(["verify", "--root", str(tmp_path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["counts"]["passed"] == 1


def test_an_unknown_top_level_field_is_still_refused(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        accept.parse({"asset": "a", "artefacts": "x", "predicate": []})
    assert refused.value.code == "spec.unknown-field"
