"""Every character a string table needs, held to the font that draws it (§PW335).

The fonts are built here, byte for byte: a font with a character map alone, format 4,
mapping exactly the characters a test chooses. So the check runs anywhere, with no font
file shipped and no font library installed.
"""

from __future__ import annotations

import struct

import pytest

from polyweave import words
from polyweave.errors import PolyweaveError


def font(chars: str) -> bytes:
    """A TrueType file whose only table is a format 4 cmap for `chars`."""
    codes = sorted({ord(c) for c in chars})
    segments = [(c, c, i + 1 - c) for i, c in enumerate(codes)] + [(0xFFFF, 0xFFFF, 1)]
    n = len(segments)
    body = struct.pack(">HHHHHHH", 4, 0, 0, 2 * n, 0, 0, 0)
    body += struct.pack(f">{n}H", *(end for _, end, _ in segments)) + b"\0\0"
    body += struct.pack(f">{n}H", *(start for start, _, _ in segments))
    wrapped = (((d + 32768) % 65536) - 32768 for *_, d in segments)
    body += struct.pack(f">{n}h", *wrapped)
    body += struct.pack(f">{n}H", *([0] * n))
    body = body[:2] + struct.pack(">H", len(body)) + body[4:]
    cmap = struct.pack(">HHHHI", 0, 1, 3, 1, 12) + body
    header = struct.pack(">IHHHH", 0x00010000, 1, 16, 0, 0)
    entry = b"cmap" + struct.pack(">III", 0, 12 + 16, len(cmap))
    return header + entry + cmap


TABLE = "keys,en,pt_BR\nSTART,Start,Começar\nPLAY,▶ Play,▶ Jogar\n"
LATIN = "".join(chr(c) for c in range(0x21, 0x7F))


def project(tmp_path, fonts):
    (tmp_path / "text").mkdir()
    (tmp_path / "text" / "strings.csv").write_text(TABLE, encoding="utf-8")
    (tmp_path / "fonts").mkdir()
    listed = []
    for name, chars, keys in fonts:
        (tmp_path / "fonts" / name).write_bytes(font(chars))
        listed.append(f'{{ path = "fonts/{name}"'
                      + (f', keys = {keys!r}'.replace("'", '"') if keys else "") + " }")
    (tmp_path / "polyweave.toml").write_text(
        f'[words]\ntable = "text/strings.csv"\nfonts = [{", ".join(listed)}]\n',
        encoding="utf-8",
    )


def test_the_reader_maps_what_the_font_maps(tmp_path):
    (tmp_path / "f.ttf").write_bytes(font("Abç"))
    assert words.characters(tmp_path / "f.ttf") == {ord("A"), ord("b"), ord("ç")}


def test_a_character_the_font_lacks_is_named_with_its_keys_and_locales(tmp_path):
    """§PW335: Nunito lacked the ▶ a prompt used, and only the game's own check saw."""
    project(tmp_path, [("body.ttf", LATIN + "ç", None)])
    found = words.glyphs(root=str(tmp_path))
    missing = {one["char"]: one for one in found["fonts"][0]["missing"]}
    assert set(missing) == {"▶", "Ç"}
    assert missing["▶"]["keys"] == ["PLAY"]
    assert missing["▶"]["locales"] == ["en", "pt_BR"]
    # Upper case counts: a game may upper-case "Começar" as it draws it.
    assert missing["Ç"]["keys"] == ["START"] and missing["Ç"]["locales"] == ["pt_BR"]
    assert missing["▶"]["code"] == "U+25B6"
    assert found["passed"] is False


def test_a_font_is_held_only_to_the_rows_it_draws(tmp_path):
    project(tmp_path, [("body.ttf", LATIN + "çÇ▶", None),
                       ("title.ttf", LATIN, ["START"])])
    found = words.glyphs(root=str(tmp_path))
    title = found["fonts"][1]
    assert [one["char"] for one in title["missing"]] == ["Ç", "ç"]
    assert found["fonts"][0]["missing"] == []


def test_a_font_with_every_character_passes(tmp_path):
    project(tmp_path, [("body.ttf", LATIN + "çÇ▶", None)])
    assert words.glyphs(root=str(tmp_path))["passed"] is True


@pytest.mark.parametrize("setup", ["none", "missing", "not-a-font"])
def test_a_font_that_cannot_be_read_is_refused(tmp_path, setup):
    project(tmp_path, [("body.ttf", LATIN, None)])
    if setup == "none":
        (tmp_path / "polyweave.toml").write_text(
            '[words]\ntable = "text/strings.csv"\n', encoding="utf-8")
    elif setup == "missing":
        (tmp_path / "fonts" / "body.ttf").unlink()
    else:
        (tmp_path / "fonts" / "body.ttf").write_bytes(b"not a font at all, just text")
    with pytest.raises(PolyweaveError) as refused:
        words.glyphs(root=str(tmp_path))
    assert refused.value.code == "words.no-fonts"
