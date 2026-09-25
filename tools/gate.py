"""The test gate, keeping its log and stamping what ran (§PW134).

`python -m pytest -q` prints a count and a dot per test. On a machine without Blender
the whole render path skips, and "passed" says nothing about whether a picture was
drawn; a run left in the background is known only to whoever read the tail of it. So:

    python tools/gate.py [pytest arguments]

- the whole output goes to `.polyweave/gate/pytest.log`, and a red one is copied aside
  as `pytest-red-<time>.log`, because the next run, made to see whether it reproduces,
  would overwrite it;
- `.polyweave/gate/stamp.json` records the commit, the exit code, passed, failed and
  skipped, and per engine whether it was here and how many tests skipped for lack of it;
- the last line says it plainly: `Blender: absent, 41 tests skipped for it`;
- a lock is held while it runs, since two overlapping runs share `.polyweave/` and
  Shio measured a false red of three errors from exactly that.

The exit code is pytest's own. A gate piped into `grep` reports `grep`'s; this does not.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / ".polyweave" / "gate"

#: What a skip reason says when the engine it needs is missing.
ENGINES = {
    "Blender": ("bpy", "blender", "renderer"),
    "Godot": ("godot",),
}


class Held(Exception):
    """Another run holds the lock."""


def lock() -> Path:
    """Take the lock, or refuse; a lock whose process is gone is taken over."""
    HERE.mkdir(parents=True, exist_ok=True)
    held = HERE / "lock"
    try:
        handle = os.open(held, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            other = int(held.read_text(encoding="utf-8").strip() or 0)
        except (OSError, ValueError):
            other = 0
        if other and _alive(other):
            raise Held(f"another gate run holds {held} (pid {other})") from None
        held.unlink(missing_ok=True)
        handle = os.open(held, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(handle, str(os.getpid()).encode())
    os.close(handle)
    return held


def _alive(pid: int) -> bool:
    if sys.platform == "win32":
        found = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            check=False,
        )
        return str(pid) in found.stdout
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def counts(report: Path) -> dict:
    """Passed, failed, skipped, and skips per missing engine, off the JUnit report."""
    found = {"passed": 0, "failed": 0, "skipped": 0}
    skipped_for = {engine: 0 for engine in ENGINES}
    if not report.is_file():
        return {**found, "skipped_for": skipped_for}
    for case in ET.parse(report).getroot().iter("testcase"):
        skip = case.find("skipped")
        if skip is not None:
            found["skipped"] += 1
            said = (skip.get("message", "") + (skip.text or "")).lower()
            for engine, words in ENGINES.items():
                if any(word in said for word in words):
                    skipped_for[engine] += 1
                    break
        elif case.find("failure") is not None or case.find("error") is not None:
            found["failed"] += 1
        else:
            found["passed"] += 1
    return {**found, "skipped_for": skipped_for}


def present() -> dict[str, bool]:
    return {
        "Blender": importlib.util.find_spec("bpy") is not None,
        "Godot": bool(os.environ.get("GODOT") or shutil.which("godot")),
    }


def commit() -> str:
    done = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return done.stdout.strip()


def summary(stamp: dict) -> str:
    engines = "; ".join(
        f"{engine}: {'present' if stamp['present'][engine] else 'absent'}, "
        f"{stamp['skipped_for'][engine]} tests skipped for it"
        for engine in ENGINES
    )
    return (
        f"gate {'green' if stamp['exit'] == 0 else 'RED'} at {stamp['commit']}: "
        f"{stamp['passed']} passed, {stamp['failed']} failed, {stamp['skipped']} "
        f"skipped. {engines}. Log: {stamp['log']}"
    )


def main(argv: list[str]) -> int:
    try:
        held = lock()
    except Held as busy:
        print(f"gate: {busy}", file=sys.stderr)
        return 3
    try:
        log = HERE / "pytest.log"
        report = HERE / "junit.xml"
        report.unlink(missing_ok=True)
        with log.open("w", encoding="utf-8") as out:
            done = subprocess.run(
                [sys.executable, "-m", "pytest", f"--junitxml={report}", *argv],
                cwd=ROOT,
                stdout=out,
                stderr=subprocess.STDOUT,
                check=False,
            )
        stamp = {
            "commit": commit(),
            "exit": done.returncode,
            "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "log": log.relative_to(ROOT).as_posix(),
            "present": present(),
            **counts(report),
        }
        if done.returncode != 0:
            kept = HERE / f"pytest-red-{time.strftime('%Y%m%d-%H%M%S')}.log"
            shutil.copyfile(log, kept)
            stamp["red_log"] = kept.relative_to(ROOT).as_posix()
        (HERE / "stamp.json").write_text(json.dumps(stamp, indent=1) + "\n", "utf-8")
        print(summary(stamp))
        return done.returncode
    finally:
        held.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
