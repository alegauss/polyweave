"""Line endings that survive a checkout (§PW228).

Found adopting polyweave in Spinhold: text written on Windows came out CRLF, the
record's digest was taken over those bytes, and a checkout that normalises to LF handed
back a file `provenance.verify` called changed although nothing had changed it.
"""

from __future__ import annotations

import hashlib
import json

from polyweave import cli, files, provenance

VOXEL = """name = "box"
output = "box"

[voxels]
cell = 1
mesh = false

[[nodes]]
id = "box"
op = "primitive"
kind = "cube"
size = 3
"""


def test_every_text_a_build_writes_has_no_carriage_return(tmp_path):
    (tmp_path / "box.toml").write_text(VOXEL, encoding="utf-8")
    built = cli.build_one("box.toml", root=str(tmp_path))
    written = [tmp_path / "box.voxels.json", tmp_path / "box.voxels.json.prov.json",
               tmp_path / "box.build.json"]
    assert built["status"] == "built"
    for one in written:
        assert b"\r" not in one.read_bytes(), one.name


def test_the_atomic_writer_writes_lf(tmp_path):
    where = tmp_path / "state.json"
    files.write_atomic(where, "one\ntwo\n")
    assert where.read_bytes() == b"one\ntwo\n"


def test_a_build_still_verifies_after_a_checkout_normalises_to_lf(tmp_path):
    (tmp_path / "box.toml").write_text(VOXEL, encoding="utf-8")
    cli.build_one("box.toml", root=str(tmp_path))
    cells = tmp_path / "box.voxels.json"
    cells.write_bytes(cells.read_bytes().replace(b"\r\n", b"\n"))  # what git hands back
    assert provenance.verify(str(tmp_path))["changed"] == []


def test_a_record_taken_over_crlf_is_said_as_such_rather_than_as_a_change(tmp_path):
    cells = tmp_path / "old.json"
    cells.write_bytes(b'{\n "a": 1\n}\n')  # the checkout's LF
    crlf = hashlib.sha256(b'{\r\n "a": 1\r\n}\r\n').hexdigest()
    record = provenance.build("mesh", cells, root=tmp_path)
    record["artefact"]["sha256"] = crlf  # as a Windows build recorded it
    provenance.write(record, tmp_path)
    (changed,) = provenance.verify(str(tmp_path))["changed"]
    assert changed["why"].startswith("recorded over CRLF")


def test_a_real_change_is_still_a_change(tmp_path):
    cells = tmp_path / "old.json"
    cells.write_bytes(b'{\n "a": 1\n}\n')
    provenance.write(provenance.build("mesh", cells, root=tmp_path), tmp_path)
    cells.write_bytes(b'{\n "a": 2\n}\n')
    (changed,) = provenance.verify(str(tmp_path))["changed"]
    assert "why" not in changed
    assert json.loads(cells.read_text("utf-8")) == {"a": 2}
