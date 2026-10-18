"""Measure how long a frame takes through the worst thing the game does.

Run:  python tools/measure_frames.py

`check_export.py` caps the pack at 9 MB and, until RK105, that was the only number this
project defended. Block M added modelled sprites, a shaft of light across the board and a
bloom where it crosses, all of it during a cascade - which is when the most is already
moving. A dropped frame there undoes the whole art block and no gate would have said so.

**This is not a CI gate and cannot become one.** A headless run draws nothing, so the frame
time it reports is the time to not draw: it would pass forever and mean nothing. So
tools/perf/cascade.gd opens a window, exactly as tools/capture/ does, and this runs it by
hand alongside the art generator and the bake. CI has no screen and is not asked.

**What binds is not what this measures.** The platform that runs out of frame first is the
web export on the compatibility renderer; this is a desktop window. The number is a relative
one - it catches a change that made things worse, which is what a budget is actually for -
and is never proof that the web build holds.

**Starting the engine is the plugin's.** `polyweave.engine` bounds the run by frames and by
a wall clock, refuses to trust Godot's exit code, and reads the printed line as the verdict -
which is the procedure this file and capture_screens.py each used to carry their own copy
of, with the reasoning written a third time in run_tests.py. What stays here is the only
part that is about this game: which script, and what the numbers mean.

Godot comes from `[paths] godot` in polyweave.toml, then $GODOT, then PATH.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import polyweave
from polyweave import engine
from polyweave.errors import PolyweaveError

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = "tools/perf/cascade.gd"

## How far the worst frame may sit above the median one before it counts as dropped. Vsync
## pins every interval to the refresh, so a millisecond ceiling would measure the monitor
## rather than the game; a ratio says the same thing at 60 Hz and at 120. A frame that misses
## its slot arrives at roughly twice the median, so 1.5 sits comfortably between "jittery"
## and "dropped" and needs no adjusting per machine.
##
## Measured at 1.02 when this landed - p50 16.66 ms, worst 17.03 ms over 133 frames - so
## nothing Block M added drops a frame on this machine.
##
## RK105 asked for a baseline taken *before* Block M and there is none: Block M had already
## shipped. What is recorded is the number after it. Said plainly, because a baseline nobody
## can date is a baseline nobody can argue with.
DROP_RATIO = 1.5

## A cascade settles well inside this; the config's 6000 is for a capture that builds a
## whole screen first.
FRAMES = 2000

REPORT = (
    r"frames: n=(?P<count>\d+) p50=(?P<p50>[\d.]+) p95=(?P<p95>[\d.]+) "
    r"p99=(?P<p99>[\d.]+) max=(?P<worst>[\d.]+)"
)


def main() -> int:
    # This prints the plugin's own refusals, message and remedy both, and the plugin
    # never prints them itself - so the encoding they land in is ours to set.
    polyweave.readable()
    if os.environ.get("CI"):
        raise SystemExit(
            "measure_frames.py needs a real window and CI has no screen.\n"
            "  A headless run draws nothing, so the frame time it reports is the time to\n"
            "  not draw. Run this locally, the way the art generator and the bake are run."
        )

    try:
        found = engine.run(SCRIPT, expect=REPORT, root=ROOT, frames=FRAMES)
    except PolyweaveError as refused:
        print(f"{refused.code}: {refused.message}")
        print(f"  {refused.remedy}")
        return 1

    if not found["ok"]:
        print(f"no measurement: {found['why']}")
        for one in found.get("errors", [])[:3]:
            print(f"  {one}")
        return 1

    said = found["found"]
    p50, worst = float(said["p50"]), float(said["worst"])
    print(
        f"a cascade with a rainbow in it, over {said['count']} frames:\n"
        f"  p50 {said['p50']} ms   p95 {said['p95']} ms   p99 {said['p99']} ms   "
        f"worst {said['worst']} ms"
    )
    ratio = worst / max(p50, 1e-6)
    if ratio > DROP_RATIO:
        print(f"  a frame was dropped: the worst is {ratio:.2f}x the median, over {DROP_RATIO}x")
        print("  a mean would not have shown this - the one frame that missed is the defect")
        return 1
    print(f"  nothing dropped: the worst frame is {ratio:.2f}x the median, inside {DROP_RATIO}x")
    return 0


if __name__ == "__main__":
    sys.exit(main())
