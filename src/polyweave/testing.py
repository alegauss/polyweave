"""One way to run a game's tests, and one answer for what failed (§PW362).

Starship runs dev/check.gd and Cottony keeps tests/*_test.gd with a runner of its own,
and each is a thing a new session must find before it can tell whether its change broke
anything. `game.test` runs a project's tests the one way, whatever they look like:

- the project is imported headless first, so a `class_name` added since the last import
  resolves on a fresh clone as it does in the editor;
- each test script runs headless at a fixed 60 fps, bounded by frames and by the wall
  clock, so a test that hangs is stopped at `timeout` and named rather than waited on;
- its output is read for a summary line, which counts the checks and the failures, and
  for a failure line each, with the script and line where the line names one;
- a run with no summary, one that raised a script error and one that timed out are each
  a failure with its line where the engine gave one, never a silent pass.

Polyweave's own convention is Cottony's, so its tests are adopted as they stand: scripts
`tests/*_test.gd`, a failure `  FAIL: <words>` and a summary `checks ran: N, failed: M`.
The tests kit's PolyweaveTest writes exactly that, with each failure's line. A project
whose tests speak otherwise declares it in `[kit.tests]`: `scripts`, the `summary` and
`failure` patterns (named groups `ran`, `failed` and `said`), and `timeout`.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Annotated

from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

#: The convention a project is held to where it declares none: Cottony's.
DEFAULTS = {
    "scripts": ["tests/*_test.gd"],
    "summary": r"^checks ran: (?P<ran>\d+), failed: (?P<failed>\d+)",
    "failure": r"^\s*FAIL:?\s+(?P<said>.+)$",
    "timeout": 300,
}

#: Where a failure line names its own place, as PolyweaveTest writes it.
_AT = re.compile(r"\((?P<file>res://[^\s:()]+):(?P<line>\d+)\)\s*$")

#: Frames at the fixed 60 fps a test runs at: ten simulated minutes, so a run that
#: reaches them has hung, which the wall clock also bounds.
_FRAMES = 36000


def declared(here: Path) -> dict:
    """The project's convention: `[kit.tests]` laid over polyweave's own."""
    config = load(here)
    kit = config.table("kit") if (here / "polyweave.toml").is_file() else {}
    own = kit.get("tests", {}) if isinstance(kit, dict) else {}
    return {**DEFAULTS, **{k: v for k, v in own.items() if k in DEFAULTS}}


def _scripts(here: Path, patterns: list) -> list[Path]:
    found: list[Path] = []
    for pattern in patterns:
        for one in sorted(here.glob(pattern)):
            if one.is_file() and one.suffix == ".gd" and one not in found:
                found.append(one)
    return found


def _res(path: Path, here: Path) -> str:
    return "res://" + path.relative_to(here).as_posix()


def read(output: str, script: str, convention: dict) -> dict:
    """What one run's output says: its counts and each failure with its place."""
    from . import engine

    summary = re.compile(convention["summary"], re.MULTILINE).search(output)
    failures = []
    for line in re.finditer(convention["failure"], output, re.MULTILINE):
        said = line["said"].strip()
        at = _AT.search(said)
        failures.append({
            "script": script,
            "file": at["file"] if at else script,
            "line": int(at["line"]) if at else None,
            "said": _AT.sub("", said).strip() if at else said,
        })
    lines = output.splitlines()
    errors = 0
    for index, line in enumerate(lines):
        if not engine.ERRORS.search(line):
            continue
        errors += 1
        # the engine names the place on the error's line or on the one after it
        place = engine.AT.search(line) or (
            engine.AT.search(lines[index + 1]) if index + 1 < len(lines) else None)
        file, _, number = place[1].rpartition(":") if place else (script, "", "")
        failures.append({"script": script, "file": file,
                         "line": int(number) if number else None, "said": line.strip()})
    groups = summary.groupdict() if summary else {}
    ran = int(groups["ran"]) if groups.get("ran") else None
    failed = int(groups["failed"]) if groups.get("failed") else 0
    if summary is None:
        failures.append({"script": script, "file": script, "line": None,
                         "said": "the script never printed its summary line"})
    passed = summary is not None and not failed and not errors
    return {"script": script, "passed": passed, "checks": ran,
            "failed": failed if summary else None, "failures": failures}


@operation("game.test")
def test(
    scripts: Annotated[
        list, Param("test scripts to run; every one the convention finds where unset")
    ] = (),
    root: Annotated[str, Param("the Godot project the tests are in")] = ".",
) -> dict:
    """Every test of a game, run headless the one way, and what failed with its line.

    Imports the project, then runs each script the project's convention finds
    (`tests/*_test.gd`, or `[kit.tests] scripts`) at a fixed 60 fps, bounded by frames
    and by `timeout` seconds. Answers the counts first, then each failure with its
    script, file, line and words. A test that does not parse, raises, never prints its
    summary or hangs is a failure, never a silent pass (§PW362).
    """
    from . import engine

    here = load(root).root
    if not (here / "project.godot").is_file():
        raise PolyweaveError(
            "engine.no-project",
            f"there is no project.godot at {here}, so there are no game tests to run",
            "run the tests from the Godot project's own folder",
        )
    convention = declared(here)
    chosen = [here / one for one in scripts] if scripts else _scripts(
        here, list(convention["scripts"]))
    if not chosen:
        raise PolyweaveError(
            "engine.no-tests",
            f"no test script matches {', '.join(convention['scripts'])} in {here}",
            "write tests/<name>_test.gd, or declare [kit.tests] scripts",
        )
    godot = engine.find(here)
    timeout = float(convention["timeout"])
    engine._launch([godot, "--headless", "--import", "--path", str(here)], cwd=here,
                   timeout=max(timeout, 300.0))
    runs = []
    for script in chosen:
        res = _res(script, here)
        try:
            output, _ = engine._launch(
                [godot, "--headless", "--path", str(here), "--fixed-fps", "60",
                 "--quit-after", str(_FRAMES), "--script", res],
                cwd=here, timeout=timeout)
        except subprocess.TimeoutExpired:
            hung = f"it was still running after {timeout:g} s, so it hangs"
            runs.append({"script": res, "passed": False, "checks": None, "failed": None,
                         "failures": [{"script": res, "file": res, "line": None,
                                       "said": hung}]})
            continue
        runs.append(read(output, res, convention))
    failures = [one for run in runs for one in run["failures"]]
    checks = sum(run["checks"] or 0 for run in runs)
    passed = all(run["passed"] for run in runs)
    return {
        "passed": passed,
        "scripts": len(runs),
        "checks": checks,
        "failed": len(failures),
        "failures": failures,
        "runs": [{k: run[k] for k in ("script", "passed", "checks", "failed")}
                 for run in runs],
        "says": f"{len(runs)} script(s), {checks} check(s), "
        + ("all passed" if passed else f"{len(failures)} failure(s), the first "
           f"{failures[0]['file']}"
           + (f":{failures[0]['line']}" if failures[0]["line"] else "")
           + f": {failures[0]['said']}"),
    }
