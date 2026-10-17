"""No source file carries a PowerShell round-trip's bytes (§PW491)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]

#: The section sign read as cp1252 and written back as UTF-8, two characters where one
#: was meant, so a search for the citation misses the file. Spelled out, this file
#: would hold them itself.
TWICE = "§".encode().decode("cp1252").encode()

#: What `Set-Content -Encoding utf8` puts at the start of a file.
MARK = b"\xef\xbb\xbf"


def sources() -> list[Path]:
    return sorted(
        path
        for folder in ("src", "tests", "tools")
        for pattern in ("*.py", "*.gd", "*.md", "*.toml")
        for path in (ROOT / folder).rglob(pattern)
    )


def round_tripped(path: Path, root: Path = ROOT) -> list[str]:
    """Each place in the file a round-trip left its mark, as `path:line`."""
    data = path.read_bytes()
    name = path.relative_to(root).as_posix()
    found = [f"{name}:1 starts with a byte-order mark"] if data.startswith(MARK) else []
    for number, line in enumerate(data.splitlines(), 1):
        if TWICE in line:
            found.append(f"{name}:{number} holds the section sign read twice")
    return found


def test_the_twice_read_sign_is_the_bytes_the_section_named():
    assert bytes.fromhex("C382C2A7") == TWICE


def test_no_source_holds_a_round_trips_bytes():
    found = [place for path in sources() for place in round_tripped(path)]
    assert not found, "re-read as UTF-8, write back without a mark: " + "; ".join(found)


def test_a_round_tripped_file_is_named_with_its_line(tmp_path):
    path = tmp_path / "bad.py"
    path.write_bytes(MARK + b'"""fine"""\n"""(' + TWICE + b'PW379)"""\n')
    assert round_tripped(path, tmp_path) == [
        "bad.py:1 starts with a byte-order mark",
        "bad.py:2 holds the section sign read twice",
    ]
