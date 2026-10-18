"""Capture screens from the running game, for the promo site's gallery.

Run:  python tools/capture_screens.py [tools/capture/map.gd ...]

Each tools/capture/<name>.gd is a SceneTree script that builds the game on a save of its
own, puts up the screen it is named for and saves what the renderer drew under
docs/design/, then prints one line, `captured: <path> <width> x <height>`. The export
presets leave both the scripts and `docs/design/screenshot-*.png` out of a build.

**The procedure is the plugin's now.** Starting Godot, bounding the run, distrusting its
exit code and reading the printed line rather than believing it are all `polyweave.engine`;
which offscreen route actually draws on this machine is `polyweave.offscreen`, which probes
rather than assumes; and the settings the picture depends on are `polyweave.capture`, which
this file had no equivalent of at all. Godot still runs the scene - what changed is who
starts it and what is checked once it has.

**What that check adds.** A capture that ran at the wrong resolution, the wrong locale or
the wrong renderer used to print its line, write its file and pass, and the site published
it. The run now states every setting `[capture] declared` names, the script applies them and
prints back an `environment:` line saying what it applied, and the run refuses where the two
differ. The regular expression that used to prove `const LOCALE` was both named and passed is
gone with it: that was a check about how this project's code is written, and it could not see
resolution at all.

**And what it says about the run before.** The record beside each picture is compared with
the one the last run left, and a capture whose settings did not move but whose bytes did is
said out loud. It is not a failure: `strike.gd` waits for the effect rather than counting
frames, on purpose, so it lands on whichever frame the effect arrived on. But `board`, `card`
and `map` come out byte-identical every time, so a diff on those three is worth opening and a
diff on `strike` usually is not - and before this, all four just printed OK.

A capture still needs a real renderer, so CI has no screen for this - run it by hand after a
change the screen shows, then `python tools/site_assets.py` for the site's copy.

Godot comes from `[paths] godot` in polyweave.toml, then $GODOT, then PATH.
"""

from __future__ import annotations

import sys
from pathlib import Path

import polyweave
from polyweave import capture
from polyweave.errors import PolyweaveError

ROOT = Path(__file__).resolve().parents[1]
CAPTURES = ROOT / "tools" / "capture"

## The line that means the script did what it was for. `wrote` is read back as a path that
## has to exist: a script that printed its line before finishing the write is a failure, and
## the exit code will not say so.
CAPTURED = r"captured: res://(?P<wrote>\S+) (?P<width>\d+) x (?P<height>\d+)"

## Which language each picture is in. Here rather than in the scripts, because the run is
## what states a setting and the script is what applies it - a constant the script keeps to
## itself is the thing that made two desks give two pictures (RK148). Every one is in
## English, README.md's language: the owner chose it for the site's gallery on 2026-10-16,
## and the gallery's Portuguese half shows the same pictures.
LOCALES = {
    "board": "en",
    "card": "en",
    "map": "en",
    "strike": "en",
}


def take(script: Path) -> tuple[bool, str]:
    """One capture, in the environment the project declares and this one names."""
    try:
        found = capture.run(
            script.relative_to(ROOT).as_posix(),
            expect=CAPTURED,
            root=ROOT,
            environment=capture.wanted(ROOT, locale=LOCALES.get(script.stem)),
            produces=("wrote",),
        )
    except PolyweaveError as refused:
        return False, f"{refused.code}: {refused.message}"

    if not found["ok"]:
        settings = found.get("environment") or {}
        return False, settings.get("why") or found.get("why") or "the run did not finish"
    said = found["found"]
    detail = f"{said['wrote']}, {said['width']} x {said['height']}"
    again = found.get("reproduced") or {}
    if not again.get("holds", True):
        detail += f"\n      SAME SETTINGS, DIFFERENT PICTURE: {again['why']}"
    return True, detail


def main() -> int:
    # The plugin returns its prose and never prints it, so the encoding of what we print
    # it to is ours to set. Left at the locale's, an em dash in a refusal goes out as one
    # cp1252 byte and reaches a UTF-8 reader as a lozenge - nothing lost writing it.
    polyweave.readable()
    scripts = [Path(arg).resolve() for arg in sys.argv[1:]] or sorted(
        one for one in CAPTURES.glob("*.gd") if one.stem != "environment"
    )
    if not scripts:
        raise SystemExit("no tools/capture/*.gd to run")
    every = True
    for script in scripts:
        ok, detail = take(script)
        every = every and ok
        print(f"{'OK  ' if ok else 'FAIL'}  {script.relative_to(ROOT).as_posix()}  {detail}")
    return 0 if every else 1


if __name__ == "__main__":
    raise SystemExit(main())
