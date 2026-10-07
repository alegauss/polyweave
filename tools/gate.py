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

The window's tests run here too (§PW303), so one gate covers both halves: where `gui/`
is installed, its typecheck and vitest run after pytest, into `gui.log`, and the last
line says how they went. Where node or `gui/node_modules` is missing, the line says that
instead, as it says an engine is absent.

The exit code is pytest's own, or 1 where pytest passed and the window did not. A
gate piped into `grep` reports `grep`'s; this does not.
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
GUI = ROOT / "gui"

#: What a skip reason says when the engine it needs is missing.
ENGINES = {
    "Blender": ("bpy", "blender", "renderer"),
    "Godot": ("godot",),
    # Pedalboard, FluidSynth with a SoundFont, and Surge XT: what a score renders
    # through (§PW187). The tests find them by FLUIDSYNTH and SOUNDFONT.
    "Audio": ("audio engine",),
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
        "Audio": importlib.util.find_spec("pedalboard") is not None
        and bool(os.environ.get("FLUIDSYNTH") or shutil.which("fluidsynth"))
        and Path(os.environ.get("SOUNDFONT", "")).is_file(),
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


def window(log: Path) -> dict:
    """The window's typecheck and tests, where it is installed (§PW303)."""
    npm = shutil.which("npm")
    if not (GUI / "package.json").is_file():
        return {"ran": False, "why": "no gui/ here"}
    if npm is None:
        return {"ran": False, "why": "node is absent"}
    if not (GUI / "node_modules").is_dir():
        return {"ran": False, "why": "not installed: run npm ci in gui/"}
    with log.open("w", encoding="utf-8") as out:
        for script in ("typecheck", "test"):
            done = subprocess.run(
                [npm, "run", script],
                cwd=GUI,
                stdout=out,
                stderr=subprocess.STDOUT,
                check=False,
            )
            if done.returncode != 0:
                return {"ran": True, "exit": done.returncode, "failed": script}
    return {"ran": True, "exit": 0}


def _said(gui: dict) -> str:
    if not gui["ran"]:
        return f"gui: skipped, {gui['why']}"
    if gui["exit"] == 0:
        return "gui: typecheck and tests green"
    return f"gui: {gui['failed']} RED"


def summary(stamp: dict) -> str:
    engines = "; ".join(
        f"{engine}: {'present' if stamp['present'][engine] else 'absent'}, "
        f"{stamp['skipped_for'][engine]} tests skipped for it"
        for engine in ENGINES
    )
    gui = f" {_said(stamp['gui'])}." if "gui" in stamp else ""
    return (
        f"gate {'green' if stamp['exit'] == 0 else 'RED'} at {stamp['commit']}: "
        f"{stamp['passed']} passed, {stamp['failed']} failed, {stamp['skipped']} "
        f"skipped. {engines}.{gui} Log: {stamp['log']}"
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
        gui = window(HERE / "gui.log")
        failed = done.returncode or (gui.get("exit", 0) and 1)
        stamp = {
            "commit": commit(),
            "exit": failed,
            "gui": gui,
            "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "log": log.relative_to(ROOT).as_posix(),
            "present": present(),
            **counts(report),
        }
        if failed:
            kept = HERE / f"pytest-red-{time.strftime('%Y%m%d-%H%M%S')}.log"
            shutil.copyfile(log, kept)
            stamp["red_log"] = kept.relative_to(ROOT).as_posix()
        (HERE / "stamp.json").write_text(json.dumps(stamp, indent=1) + "\n", "utf-8")
        print(summary(stamp))
        return failed
    finally:
        held.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
