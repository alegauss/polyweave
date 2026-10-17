"""What an exported pack carries, listed (§PW470).

Cottony's `check_export.py` exported a pack with `--export-pack`, which needs no export
template and so runs in CI, and parsed Godot's pack table itself to hold the export's
filter to its word: an unfiltered export once shipped fourteen megabytes of reference
mockups beside a five megabyte game, and Godot exits 0 on a filter that drops half of
it. The export and the table are the same for every game, so they are here; what a game
must and must not carry stays the game's.
"""

from __future__ import annotations

import re
import struct
import subprocess
from pathlib import Path
from typing import Annotated

from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

#: Where an imported asset travels in a pack: `.godot/imported/<source>-<hash>.<ext>`.
IMPORTED = ".godot/imported/"


def files_in(pack: Path) -> list[tuple[str, int]]:
    """Every path in a pack's file table, with its size.

    A GDPC header carries the format version, the engine version, the pack flags, the
    offset files are stored from and the offset of the file table itself, which from
    format 4 sits at the end of the pack rather than the front. An encrypted directory
    cannot be read, and is refused.
    """
    data = pack.read_bytes()
    if data[:4] != b"GDPC":
        raise PolyweaveError("game.pack-unread", f"{pack.name} is not a Godot pack",
                             "export the preset as a pack (.pck)")
    (version,) = struct.unpack_from("<i", data, 4)
    if version < 4:
        raise PolyweaveError(
            "game.pack-unread", f"{pack.name} is pack format {version}, older than 4",
            "export it with Godot 4.4 or later")
    (flags,) = struct.unpack_from("<I", data, 20)
    if flags & 1:
        raise PolyweaveError(
            "game.pack-unread", f"{pack.name}'s directory is encrypted",
            "export a pack without directory encryption to list it")
    (table,) = struct.unpack_from("<q", data, 32)
    (count,) = struct.unpack_from("<i", data, table)
    at, found = table + 4, []
    for _ in range(count):
        (length,) = struct.unpack_from("<i", data, at)
        at += 4
        path = data[at:at + length].rstrip(b"\0").decode("utf-8")
        at += length
        _offset, size = struct.unpack_from("<QQ", data, at)
        at += 16 + 16 + 4  # offset and size, then the md5, then per-file flags
        found.append((path, int(size)))
    return found


def source_of(path: str) -> str:
    """The file an imported asset came from: `.../sky.png-<hash>.ctex` is `sky.png`."""
    return path.rsplit("/", 1)[-1].rsplit("-", 1)[0]


@operation("game.pack")
def pack(
    preset: Annotated[
        str, Param("the export preset, by its name in export_presets.cfg")
    ],
    root: Annotated[str, Param("the Godot project to export")] = ".",
    ceiling_mb: Annotated[
        float, Param("the most the pack may weigh; nothing is held to one if unset",
                     unit="MB")
    ] = None,
) -> dict:
    """Export a preset as a pack and list what landed in it (§PW470).

    `--export-pack` needs no export template, so this runs where a release cannot be
    built. The pack is written into the work area and kept there, for
    `game.release_check` to read. Each file comes back with its size, and an imported
    asset with the `source` it came from, since a pack carries it under
    `.godot/imported/` and never under its own path. Godot's exit code is not read: a
    pack that was not written is the refusal. `over` says the pack outweighs
    `ceiling_mb`; which files belong is the game's to say.
    """
    from . import engine

    config = load(root)
    here = config.root
    if not (here / "project.godot").is_file():
        raise PolyweaveError(
            "engine.no-project", f"there is no project.godot at {here} to export",
            "export from the Godot project's own folder")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", preset).strip("-").lower() or "pack"
    into = config.path("paths.work") / "pack" / f"{slug}.pck"
    into.parent.mkdir(parents=True, exist_ok=True)
    if into.exists():
        into.unlink()
    timeout = float(config.get("engine.timeout"))
    try:
        output, _ = engine._launch(
            [engine.find(here), "--headless", "--path", str(here), "--export-pack",
             preset, str(into)], cwd=here, timeout=timeout)
    except subprocess.TimeoutExpired:
        output = f"the export was still running after {timeout:g} s"
    if not into.is_file():
        raise PolyweaveError(
            "game.pack-unwritten",
            f"no pack was written for preset {preset!r}",
            "check the preset's name in export_presets.cfg; the detail is what Godot "
            "printed",
            detail="\n".join(output.splitlines()[-10:]) or None, given=preset)
    held = files_in(into)
    weight = into.stat().st_size / 1024 / 1024
    over = ceiling_mb is not None and weight > float(ceiling_mb)
    from polyweave.kernel.provenance import relative

    return {
        "preset": preset,
        "pack": relative(into, here),
        "megabytes": round(weight, 3),
        **({"ceiling_mb": float(ceiling_mb), "over": over}
           if ceiling_mb is not None else {}),
        "files": [
            {"path": path, "bytes": size,
             **({"source": source_of(path)} if path.startswith(IMPORTED) else {})}
            for path, size in held
        ],
        "says": f"{preset}: {len(held)} files, {weight:.1f} MB"
        + (f", over the {float(ceiling_mb):.1f} MB ceiling" if over else ""),
    }
