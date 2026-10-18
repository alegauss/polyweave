"""Export a pack and check what landed in it.

Run:  python tools/check_export.py ["Windows Desktop"]

The whole `docs/` tree lives inside the project, so an export that is not filtered
ships the reference mockups - fourteen megabytes of them - beside a five megabyte game,
and nobody notices until the download is slow. `export_presets.cfg` filters them out by
name; this is what holds that filter to its word.

It exports a pack (`--export-pack`, which needs no export template, so it runs on a
machine that cannot build a release), reads the pack's own file table, and fails when
anything the game loads is missing, when a file nothing loads is present, or when the
pack is over the ceiling below. Godot exits 0 on a filter that drops half the game, so
the file list is the check and the exit code is not.

Two things about a pack make this less obvious than listing files. An imported asset
travels as `.godot/imported/<source name>-<hash>.ctex` and never under its own path, so
a reference mockup that slips through the filter shows up there; and a scene or a
resource travels as a `.remap` beside the exported copy. Both are matched by name here.

**The export and the table are the plugin's** (polyweave PW470): `game.pack` exports the
preset into polyweave's work area, finds Godot through `[paths] godot`, then $GODOT,
then PATH, and lists the pack's files with each imported asset's source. What the game
must and must not carry, below, is this project's and stays here.
"""

from __future__ import annotations

import sys
from pathlib import Path

from polyweave import driving
from polyweave.errors import PolyweaveError
from polyweave.pack import pack as exported
from polyweave.pack import source_of

ROOT = Path(__file__).resolve().parents[1]

# the only preset there is, since RK106 took the web target out of export_presets.cfg
DEFAULT_PRESET = "Windows Desktop"

# The game is about 5 MB and the reference imagery alone is 13.5 MB, so anything near the
# ceiling means the filter stopped working rather than that the game grew. That is what this
# number is for and always was.
#
# It was sized for a web download, and RK106 dropped the web target for Forward+. A desktop
# installer does not care about nine megabytes, so the ceiling is restated rather than
# deleted: it is a filter check, not a download budget, and it is the only thing standing
# between a build and fourteen megabytes of concept art. Raised to leave room for the meshes
# Block O brings in, which a web build could never have carried either.
CEILING_MB = 24.0

# what the game loads by a path written in code, which no dependency walk would find,
# plus the licences: the font's, which the OFL requires to travel with it, and the
# project's, because a build is a copy and MIT asks its notice to come along
MUST_HOLD = [
    "project.binary",
    "scenes/main.tscn.remap",
    "data/levels.tres.remap",
    # the authored levels: plain JSON the game reads with FileAccess, so nothing about the
    # project references them and only this says they have to travel
    "data/levels/level_001.json",
    "data/levels/level_020.json",
    # and the cutscenes, read the same way for the same reason (RK109)
    "data/cutscenes/opening.json",
    "scripts/game.gdc",
    "tools/art/fonts/OFL.txt",
    "LICENSE",
]

# one of each kind of imported asset, by the source file it was imported from
MUST_HOLD_IMPORTED = [
    "piece_heart.png",
    "booster_hammer.png",
    "sky.png",
    "pop_heart.wav",
    "swap.wav",
    "music_calm.ogg",
    "Nunito.ttf",
]

# nothing under these belongs in a build: the tests and the screen captures, which are
# scripts that drive the game, and the MCP wiring, which is a .json and therefore a
# resource as far as an unfiltered export is concerned
MUST_NOT_START = ["tests/", "tools/capture/", ".mcp.json"]

# art that is still in the tree and that the game no longer loads: the baked tray and the cell
# sprites that sat on it, both replaced by `TrayMesh` in the board's 3D layer (RK114). Named by
# the source file, because an imported asset travels under a hashed name
MUST_NOT_IMPORT = ["board_panel.png", "cell.png"]


def loadable() -> set[str]:
    """Every asset the game may legitimately carry: the art, the audio and the font."""
    names: set[str] = set()
    for folder in ["docs/design/art", "docs/design/audio", "tools/art/fonts"]:
        for asset in (ROOT / folder).rglob("*"):
            if asset.is_file() and asset.suffix != ".import":
                names.add(asset.name)
    return names


def driven(pack: Path) -> list[str]:
    """The flows an agent kept through polyweave, replayed, and the pack checked for its
    driver.

    Each file in tests/flows is a path through the game an agent drove and kept
    (polyweave's game.keep): the title to a won first level, a setting that sticks.
    Replayed here with no agent, they are the only check that presses the menus'
    buttons. And polyweave's driver answers any method it is asked to, so it must never
    reach a player: game.release_check reads the presets and this pack for it.
    """
    problems = [
        f"{one['at']}: {one['why']}; {one['fix']}"
        for one in driving.release_checked(ROOT, pack=str(pack))["findings"]
    ]
    for flow in sorted((ROOT / "tests" / "flows").glob("*.flow.json")):
        replayed = driving.replayed(str(flow), root=ROOT)
        if replayed["ok"]:
            print(f"  flow {flow.name}: held to frame {replayed['frame']}")
        else:
            problems.append(
                f"flow {flow.name} broke at step {replayed['failed_step']}, frame "
                f"{replayed['frame']}: {replayed['why']}"
            )
    return problems


def main() -> int:
    preset = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PRESET
    try:
        found = exported(preset, root=str(ROOT))
    except PolyweaveError as refused:
        raise SystemExit(f"{refused.message}\n  {refused.remedy}") from refused
    pack = ROOT / found["pack"]
    held = [(one["path"], one["bytes"]) for one in found["files"]]
    names = {path for path, _ in held}
    megabytes = found["megabytes"]

    problems: list[str] = []
    for path in MUST_HOLD:
        if path not in names:
            problems.append(f"missing: {path}")
    imported = {source_of(path) for path in names if path.startswith(".godot/imported/")}
    for source in MUST_HOLD_IMPORTED:
        if source not in imported:
            problems.append(f"missing: whatever {source} imports to")

    allowed = loadable()
    for source in sorted(imported - allowed):
        problems.append(f"imported from outside art/ and audio/: {source}")
    for source in MUST_NOT_IMPORT:
        if source in imported:
            problems.append(f"nothing loads this any more: {source}")
    for path in sorted(names):
        for start in MUST_NOT_START:
            if path.startswith(start):
                problems.append(f"should not be in a build: {path}")
    if megabytes > CEILING_MB:
        problems.append(f"pack is {megabytes:.1f} MB, over the {CEILING_MB:.1f} MB ceiling")

    print(f"{preset}: {len(held)} files, {megabytes:.1f} MB")
    for path, size in sorted(held, key=lambda pair: pair[1], reverse=True)[:5]:
        print(f"  {size / 1024:8.1f} KB  {path}")
    problems += driven(pack)
    for problem in problems:
        print(f"FAIL  {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
