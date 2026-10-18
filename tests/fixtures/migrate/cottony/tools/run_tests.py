"""Run every Godot test under tests/ and fail honestly.

Run:  python tools/run_tests.py [tests/match3_test.gd ...]

A test is a SceneTree script named tests/*_test.gd. It prints one summary line,
`checks ran: N, failed: M`, and quits non-zero when anything failed.

**The procedure is the plugin's now** (polyweave PW466): `game.test` is this file's own
procedure, written from it, and Cottony's convention is its default. It imports the
project headless first, so a class_name added since the last import resolves on a fresh
clone; runs each script at a fixed 60 fps, bounded by frames and by a wall clock, since
a script that does not compile sits in Godot's main loop forever; and reads the output
rather than the exit code, which lies three ways. A run is a failure unless its summary
is present and reports zero failures, and a SCRIPT ERROR, a parse or compile error, or a
string that could not be formatted (RK128) fails it too. Godot comes from `[paths]
godot` in polyweave.toml, then $GODOT, then PATH.

This file stays as the name both workflows call and prints the line per script they
always printed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import polyweave
from polyweave.errors import PolyweaveError
from polyweave.testing import test

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    # Godot's output goes through here on a failure, and so does the plugin's refusal
    # when it cannot find Godot at all. Neither is ours to re-encode on the way past.
    polyweave.readable()
    scripts = [Path(arg).resolve().relative_to(ROOT).as_posix() for arg in sys.argv[1:]]
    try:
        found = test(scripts, root=str(ROOT))
    except PolyweaveError as refused:
        raise SystemExit(f"{refused.message}\n  {refused.remedy}") from refused
    failing: dict[str, list[str]] = {}
    for one in found["failures"]:
        at = f"{one['file']}:{one['line']} " if one.get("line") else ""
        failing.setdefault(one["script"], []).append(f"{at}{one['said']}")
    for run in found["runs"]:
        named = run["script"].removeprefix("res://")
        if run["passed"]:
            print(f"PASS  {named}  {run['checks']} checks")
        else:
            print(f"FAIL  {named}  " + "; ".join(failing.get(run["script"], [])[:5]))
    return 0 if found["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
