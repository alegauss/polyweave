"""Boot the game headless, shut it down, and report what it said on the way out.

Run:  python tools/check_boot.py

`godot --headless --quit --path .` is the project's one check that the game boots and
shuts down clean, and reading it by eye stopped working: every clean run prints

    WARNING: 4 ObjectDB instances were leaked at exit
    ERROR: 2 resources still in use at exit

and a reader who has to know which two lines to ignore is a reader who will ignore a
third. Those two are not the game's: `--verbose` names the music's Ogg playback and the
stream it holds, released on the audio thread that the headless dummy driver never runs
again before the process exits, and a windowed run on a real driver prints neither
(RK75, RK134).

**The procedure is the plugin's now** (polyweave PW469): `game.boot` boots the main
scene headless, bounded by `[engine] timeout`, and fails on a script, parse or compile
error, a main scene missing or not loaded, any other line the game printed, or a leak
other than the one `[engine] leaks` forgives in polyweave.toml, `[4, 2]`, named exactly:
a run that leaks five objects is a run this reports. Godot comes from `[paths] godot`,
then $GODOT, then PATH. This file stays as the name the workflow calls.
"""

from __future__ import annotations

import sys
from pathlib import Path

import polyweave
from polyweave.errors import PolyweaveError
from polyweave.testing import boot

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    polyweave.readable()
    try:
        found = boot(str(ROOT))
    except PolyweaveError as refused:
        raise SystemExit(f"{refused.message}\n  {refused.remedy}") from refused
    print(found["says"])
    for line in [*found.get("fatal", []), *found.get("said", [])][:10]:
        print(f"  {line}")
    if found.get("exit_code"):
        # the output is the verdict, and the forgiven shutdown is exactly what makes the
        # engine exit non-zero on a good run
        print(f"  the engine exited {found['exit_code']}")
    return 0 if found["clean"] else 1


if __name__ == "__main__":
    sys.exit(main())
