"""A draft level from a transcription a person accepted row by row (§PW609)."""

from __future__ import annotations

import json
import tomllib

import pytest

from polyweave.kernel import provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.reference import reference_draft

SHEET = {"frames": "refs/p1", "columns": ["kind", "count"], "rows": [
    {"id": "opening", "from": 3.5, "to": 5.0, "kind": "pod", "count": 4,
     "frames": ["t00003500.png"]},
    {"id": "right", "from": 5.5, "to": 6.5, "kind": "dart", "count": 3,
     "frames": ["t00005500.png"]},
]}

MAPPING = """level  = "waves/base.waves.toml"
into   = "stage.0.wave.0.group"
offset = 3.0

[row]
enemy = "{kind}"
count = "{count}"
at    = "{from}"
note  = "read {from} to {to}"

[names.kind]
pod  = "mote"
dart = "diver"
"""

BASE = """[line]
speed = 24.0

[[stage]]
[[stage.wave]]
time_limit = 12.0
"""


def _project(tmp_path, answers=("opening", "right"), corrected=(), schema=None):
    table = ""
    if schema is not None:
        (tmp_path / "level.schema.json").write_text(json.dumps(schema),
                                                    encoding="utf-8")
        table = '[levels]\nschema = "level.schema.json"\n'
    (tmp_path / "polyweave.toml").write_text(table, encoding="utf-8")
    (tmp_path / "waves").mkdir()
    (tmp_path / "waves" / "base.waves.toml").write_text(BASE, encoding="utf-8")
    (tmp_path / "p1.sheet.json").write_text(json.dumps(SHEET), encoding="utf-8")
    (tmp_path / "p1.mapping.toml").write_text(MAPPING, encoding="utf-8")
    lines = [{"row": r, "choice": "right", "accepted": True, "why": "",
              "when": "2026-11-04"} for r in answers]
    lines += [{"row": r, "choice": "wrong", "accepted": False, "why": "five, not four",
               "when": "2026-11-04"} for r in corrected]
    (tmp_path / "p1.sheet.answers.jsonl").write_text(
        "".join(json.dumps(one) + "\n" for one in lines), encoding="utf-8")
    return tmp_path


def test_accepted_rows_become_the_level_s_items_through_the_mapping(tmp_path):
    root = _project(tmp_path)
    made = reference_draft.draft("p1.sheet.json", "p1.mapping.toml",
                                 "waves/phase_1.draft.toml", root=str(root))
    assert made["draft"] == "waves/phase_1.draft.toml" and made["rows"] == 2
    level = tomllib.loads((root / "waves" / "phase_1.draft.toml").read_text("utf-8"))
    assert level["line"] == {"speed": 24.0}
    wave = level["stage"][0]["wave"][0]
    assert wave["time_limit"] == 12.0
    assert wave["group"] == [
        {"enemy": "mote", "count": 4, "at": 0.5, "note": "read 0.5 to 2.0"},
        {"enemy": "diver", "count": 3, "at": 2.5, "note": "read 2.5 to 3.5"}]
    record = provenance.read("waves/phase_1.draft.toml", root=str(root))
    assert record["params"]["draft"] is True
    assert {one["role"] for one in record["inputs"]} == {
        "transcription", "mapping", "answers"}


def test_a_json_draft_and_its_schema_findings(tmp_path):
    schema = {"type": "object", "properties": {"stage": {"type": "array", "items": {
        "type": "object", "properties": {"wave": {"type": "array", "items": {
            "type": "object", "properties": {"group": {"type": "array", "items": {
                "type": "object", "properties": {
                    "count": {"type": "integer", "maximum": 3}}}}}}}}}}}}
    root = _project(tmp_path, schema=schema)
    made = reference_draft.draft("p1.sheet.json", "p1.mapping.toml",
                                 "waves/phase_1.draft.json", root=str(root))
    assert json.loads((root / "waves" / "phase_1.draft.json").read_text("utf-8"))[
        "stage"][0]["wave"][0]["group"][1]["enemy"] == "diver"
    assert [one["at"] for one in made["findings"]] == [
        "stage[0].wave[0].group[0].count"]


@pytest.mark.parametrize("answers, corrected", [(("opening",), ()),
                                                (("opening",), ("right",))])
def test_a_sheet_not_accepted_is_never_drafted(tmp_path, answers, corrected):
    root = _project(tmp_path, answers=answers, corrected=corrected)
    with pytest.raises(PolyweaveError) as refused:
        reference_draft.draft("p1.sheet.json", "p1.mapping.toml", "waves/d.toml",
                              root=str(root))
    assert refused.value.code == "capture.not-accepted"
    assert not (root / "waves" / "d.toml").exists()


@pytest.mark.parametrize("mapping", [
    'into = "stage.0.wave.0.group"\n',
    'into = "stage.0.wave.0.group"\n[row]\nside = "{side}"\n',
    'into = "line.speed"\n[row]\nx = 1\n',
])
def test_a_mapping_that_says_no_way_in_is_refused(tmp_path, mapping):
    root = _project(tmp_path)
    (root / "p1.mapping.toml").write_text('level = "waves/base.waves.toml"\n' + mapping,
                                          encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        reference_draft.draft("p1.sheet.json", "p1.mapping.toml", "waves/d.toml",
                              root=str(root))
    assert refused.value.code == "capture.bad-mapping"
