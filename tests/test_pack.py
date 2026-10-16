"""What an exported pack carries, listed (§PW470)."""

from __future__ import annotations

import struct

import pytest

from polyweave import engine, pack
from polyweave.errors import PolyweaveError


def write_pack(path, files, *, flags=0, version=4):
    """A format-4 pack: header, file data, then the table at the end, as Godot does."""
    header = bytearray(b"GDPC")
    header += struct.pack("<iiii", version, 4, 4, 0) + struct.pack("<I", flags)
    header += struct.pack("<qq", 0, 0)  # where files start, where the table is
    header += b"\0" * 64
    body = bytearray()
    for _, size in files:
        body += b"x" * size
    table = len(header) + len(body)
    struct.pack_into("<q", header, 32, table)
    listing = bytearray(struct.pack("<i", len(files)))
    offset = len(header)
    for name, size in files:
        raw = name.encode() + b"\0" * (4 - len(name) % 4)
        listing += struct.pack("<i", len(raw)) + raw
        listing += struct.pack("<QQ", offset, size) + b"\0" * 16 + struct.pack("<I", 0)
        offset += size
    path.write_bytes(bytes(header + body + listing))


FILES = [("res://scenes/main.tscn.remap", 40),
         (".godot/imported/sky.png-3f9a.ctex", 2048),
         ("res://project.binary", 512)]


@pytest.fixture
def game(tmp_path, monkeypatch):
    (tmp_path / "project.godot").write_text("[application]\n", encoding="utf-8")
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    monkeypatch.setattr(engine, "find", lambda root: "godot")
    asked = {}

    def export(argv, **how):
        asked["argv"] = argv
        if argv[argv.index("--export-pack") + 1] == "Web":
            write_pack(type(tmp_path)(argv[-1]), FILES)
        return "exported", 0

    monkeypatch.setattr(engine, "_launch", export)
    return tmp_path, asked


def test_a_preset_is_exported_as_a_pack_and_its_files_listed(game):
    root, asked = game
    found = pack.pack("Web", root=str(root))
    assert asked["argv"][1:4] == ["--headless", "--path", str(root)]
    assert found["pack"] == ".polyweave/pack/web.pck"
    assert [one["path"] for one in found["files"]] == [name for name, _ in FILES]
    imported = found["files"][1]
    assert imported["bytes"] == 2048 and imported["source"] == "sky.png"
    assert "source" not in found["files"][0]


def test_a_ceiling_says_when_the_pack_is_over_it(game):
    root, _ = game
    assert pack.pack("Web", root=str(root), ceiling_mb=1.0)["over"] is False
    found = pack.pack("Web", root=str(root), ceiling_mb=0.001)
    assert found["over"] is True and "over the" in found["says"]


def test_a_preset_that_wrote_no_pack_is_refused_with_what_godot_said(game):
    root, _ = game
    with pytest.raises(PolyweaveError) as refused:
        pack.pack("Switch", root=str(root))
    assert refused.value.code == "game.pack-unwritten"


def test_an_encrypted_or_foreign_pack_is_refused_not_misread(tmp_path):
    sealed = tmp_path / "sealed.pck"
    write_pack(sealed, FILES, flags=1)
    with pytest.raises(PolyweaveError) as refused:
        pack.files_in(sealed)
    assert "encrypted" in refused.value.message
    (tmp_path / "other.pck").write_bytes(b"PK\x03\x04")
    with pytest.raises(PolyweaveError):
        pack.files_in(tmp_path / "other.pck")
