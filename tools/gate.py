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
is installed, its typecheck, build and vitest run after pytest, into `gui.log`, and the
last line says how they went. Where node or `gui/node_modules` is missing, the line says
that instead, as it says an engine is absent.

The exit code is pytest's own, or 1 where pytest passed and the window did not. A
gate piped into `grep` reports `grep`'s; this does not.

Pytest runs across every core (`-n auto`) where pytest-xdist is installed and the
arguments choose no `-n` or `-m`: the gate went from half an hour to under fifteen
minutes on a 28-thread desk. Tests marked `serial`, the ones that measure time on the
machine, run alone after the rest, since a frame budget read beside 28 workers measures
the load and not the code.

**A worker that dies is named, with what it left** (§PW524). Blender runs in process, so
a render that kills it takes the xdist worker with it and the log says only "worker
crashed", with no traceback. It happened once in about 180 gate runs (2026-10-17, two
render tests) and not in ten runs of the render file on twelve workers since, so it is
not marked away. The summary instead says which tests' workers crashed, and any
`*.crash.txt` Blender wrote to the temp folder during the run is copied beside the red
log, so the next crash can be read rather than rerun.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
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


def summed(each: list[dict]) -> dict:
    """Several runs' counts as one, the way the gate reports them."""
    total = {"passed": 0, "failed": 0, "skipped": 0,
             "skipped_for": {engine: 0 for engine in ENGINES}}
    for one in each:
        for key in ("passed", "failed", "skipped"):
            total[key] += one[key]
        for engine, many in one["skipped_for"].items():
            total["skipped_for"][engine] += many
    return total


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
        # Built before the tests, so the live one opens the window as it ships.
        for script in ("typecheck", "build", "test"):
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


def kits() -> dict:
    """Every kit the plugin carries, proved in its own fixture (§PW342)."""
    done = subprocess.run(
        [sys.executable, "-m", "polyweave", "kit.prove", "--json"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    try:
        said = json.loads(done.stdout)
    except json.JSONDecodeError:
        return {"held": 0, "failed": 1, "skipped": 0,
                "why": (done.stderr or done.stdout)[-400:]}
    if "kits" not in said:
        return {"held": 0, "failed": 1, "skipped": 0, "why": said.get("message", "")}
    return {key: said[key] for key in ("held", "failed", "skipped")} | {
        "red": [one["kit"] for one in said["kits"] if one["status"] == "failed"]}


#: What xdist prints for a worker that died under a test.
CRASHED = re.compile(r"worker '(\w+)' crashed while running '([^']+)'")


def crashed(log: Path, since: float, keep: Path) -> dict:
    """The tests whose workers died, and Blender's crash logs from this run, kept.

    A crash log is any `*.crash.txt` in the temp folder written since the run began,
    copied into `keep` under the run's time so a later crash does not overwrite it.
    """
    text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
    tests = sorted({test for _, test in CRASHED.findall(text)})
    kept = []
    if tests:
        for found in sorted(Path(tempfile.gettempdir()).glob("*.crash.txt")):
            try:
                fresh = found.stat().st_mtime >= since
            except OSError:
                continue
            if fresh:
                to = keep / f"crash-{time.strftime('%Y%m%d-%H%M%S')}-{found.name}"
                shutil.copyfile(found, to)
                kept.append(to.relative_to(ROOT).as_posix())
    return {"tests": tests, "logs": kept}


def _crashed_said(found: dict) -> str:
    if not found["tests"]:
        return ""
    logs = (f"Blender's crash log kept at {', '.join(found['logs'])}" if found["logs"]
            else "Blender left no crash log in the temp folder")
    return (f" {len(found['tests'])} worker(s) crashed, under "
            f"{', '.join(found['tests'])}; {logs}.")


def _kits_said(proved: dict) -> str:
    said = (f"kits: {proved['held']} held, {proved['failed']} failed, "
            f"{proved['skipped']} skipped for want of an engine")
    red = proved.get("red") or ([proved["why"]] if proved.get("why") else [])
    return said + (f" ({', '.join(red)})" if proved["failed"] and red else "")


def _said(gui: dict) -> str:
    if not gui["ran"]:
        return f"gui: skipped, {gui['why']}"
    if gui["exit"] == 0:
        return "gui: typecheck, build and tests green"
    return f"gui: {gui['failed']} RED"


def summary(stamp: dict) -> str:
    engines = "; ".join(
        f"{engine}: {'present' if stamp['present'][engine] else 'absent'}, "
        f"{stamp['skipped_for'][engine]} tests skipped for it"
        for engine in ENGINES
    )
    gui = f" {_said(stamp['gui'])}." if "gui" in stamp else ""
    proved = f" {_kits_said(stamp['kits'])}." if "kits" in stamp else ""
    died = _crashed_said(stamp["crashed"]) if "crashed" in stamp else ""
    return (
        f"gate {'green' if stamp['exit'] == 0 else 'RED'} at {stamp['commit']}: "
        f"{stamp['passed']} passed, {stamp['failed']} failed, {stamp['skipped']} "
        f"skipped. {engines}.{gui}{proved}{died} Log: {stamp['log']}"
    )


def runs(argv: list[str]) -> list[list[str]]:
    """The pytest runs the gate makes: one, or two where it can run on every core.

    With xdist here and no `-n` or `-m` chosen, every test not marked `serial` runs on
    every core, then the `serial` ones alone: a test that measures frame times reads the
    machine's load, and Godot's launch proof measured 120 ms frames against its 100 ms
    budget with 28 workers beside it.
    """
    chosen = any(one.startswith(("-n", "--numprocesses", "-m")) for one in argv)
    off = "no:xdist" in argv
    if chosen or off or importlib.util.find_spec("xdist") is None:
        return [list(argv)]
    return [["-n", "auto", "-m", "not serial", *argv], ["-m", "serial", *argv]]


#: pytest's exit code where a run collected nothing, which a serial pass over files
#: holding no serial test is, and is not a failure.
NOTHING_COLLECTED = 5


def main(argv: list[str]) -> int:
    try:
        held = lock()
    except Held as busy:
        print(f"gate: {busy}", file=sys.stderr)
        return 3
    try:
        log = HERE / "pytest.log"
        planned = runs(argv)
        reports = [HERE / ("junit.xml" if i == 0 else f"junit-{i}.xml")
                   for i in range(len(planned))]
        for stale in HERE.glob("junit*.xml"):
            stale.unlink(missing_ok=True)
        codes = []
        began = time.time()
        with log.open("w", encoding="utf-8") as out:
            for args, report in zip(planned, reports, strict=True):
                out.flush()
                codes.append(subprocess.run(
                    [sys.executable, "-m", "pytest", f"--junitxml={report}", *args],
                    cwd=ROOT,
                    stdout=out,
                    stderr=subprocess.STDOUT,
                    check=False,
                ).returncode)
        ran = [c for c in codes if not (c == NOTHING_COLLECTED and len(codes) > 1)]
        tested = next((c for c in ran if c), 0) if ran else NOTHING_COLLECTED
        gui = window(HERE / "gui.log")
        proved = kits()
        failed = (tested or (gui.get("exit", 0) and 1)
                  or (proved["failed"] and 1))
        stamp = {
            "commit": commit(),
            "exit": failed,
            "gui": gui,
            "kits": proved,
            "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "log": log.relative_to(ROOT).as_posix(),
            "present": present(),
            **summed([counts(report) for report in reports]),
        }
        died = crashed(log, began, HERE)
        if died["tests"]:
            stamp["crashed"] = died
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
