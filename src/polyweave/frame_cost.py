"""What a change costs a frame: one timing script, two builds, the difference (§PW258).

Starship's RK131 added a sky, haze and searchlights behind the city under a design that
said the frame rate must hold. The project's own timing script, `dev/perf.gd`, had a
table recorded a day earlier (2.03 ms at High) that other work had since pushed to 4.23
ms, so the only honest number was a comparison. It was made by hand: stash everything,
re-import, time it, pop, re-import, time it again, four more runs for the table.

So `engine.cost` times one script on two builds of the same project, on the same machine
and settings, several times each:

- a side is the working tree or a git revision. A revision is checked out into a
  worktree of its own under the work folder, never by stashing the user's files, and
  kept there, so its import is paid once;
- each side is timed with its own copy of the script, as stashing would have, since a
  script leans on the game it times (Starship's perf.gd reads `Run.trail`, which the
  revisions before RK136 have no member for). A revision without the script at all is
  timed with the working tree's, and the answer says which side borrowed it;
- the runs alternate, one side then the other, so whatever the machine drifts through
  (heat, a background job) lands on both;
- every `name=number` pair on the line `expect` matches is a measure. Each is answered
  with both sides' means and spreads, the difference with an interval of two standard
  errors, and `sure` where that interval leaves out zero;
- the machine and the device the engine reported are named, since a frame time means
  nothing without them.

The answer is recorded under the work folder, keyed by the script and its arguments,
and the next call names the last one and whether it went stale: a table taken on
another build is a number about something that no longer exists.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import re
import subprocess
import time
from pathlib import Path
from typing import Annotated

from . import engine
from .config import load
from .describe import Param, operation
from .errors import PolyweaveError
from .files import write_atomic

#: One measure on the line a timing script prints: `avg=2.03ms`, `enemies_peak=41`.
PAIR = re.compile(r"\b(?P<name>[A-Za-z_]\w*)=(?P<value>-?\d+(?:\.\d+)?)")

#: The device the engine says it draws with, as Godot prints it at start-up.
DEVICE = re.compile(r"Using Device #\d+: (?P<device>[^\r\n]+)")


def _git(where: Path, *args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=where, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PolyweaveError(
            "engine.cost-no-revision",
            f"git could not answer `git {' '.join(args)}` in {where}",
            "run it inside a git repository, and name a revision it has",
            detail=getattr(exc, "stderr", "") or str(exc),
        ) from exc


def _side(named: str, here: Path, work: Path) -> dict:
    """Where one side of the comparison lives: the tree itself, or a revision's own
    worktree, checked out once and kept."""
    if not named:
        return {"label": "working tree", "root": here, "commit": "",
                "build": engine._build(here)}
    top = Path(_git(here, "rev-parse", "--show-toplevel"))
    commit = _git(here, "rev-parse", "--verify", f"{named}^{{commit}}")
    tree = work / "cost" / "trees" / commit[:12]
    if not (tree / ".git").exists():
        tree.parent.mkdir(parents=True, exist_ok=True)
        _git(top, "worktree", "add", "--detach", str(tree), commit)
    inside = here.resolve().relative_to(top.resolve())
    return {"label": named, "root": tree / inside, "commit": commit,
            "build": commit, "fresh": not (tree / ".polyweave-imported").exists(),
            "tree": tree}


def _imported(side: dict, binary: str, timeout: float) -> None:
    """Import a side's resources before it is timed, as the editor would on open."""
    output, _ = engine._launch(
        [binary, "--headless", "--import", "--path", str(side["root"])],
        cwd=side["root"], timeout=timeout,
    )
    if engine.ERRORS.search(output) and side.get("commit"):
        raise PolyweaveError(
            "engine.cost-import",
            f"{side['label']} did not import cleanly",
            "open that revision in the editor once, or name another revision",
            detail="\n".join(output.splitlines()[-8:]),
        )
    if side.get("tree"):
        (side["tree"] / ".polyweave-imported").write_text(
            time.strftime("%Y-%m-%dT%H:%M:%S"), encoding="utf-8")


def _stats(values: list[float]) -> dict:
    n = len(values)
    mean = sum(values) / n if n else math.nan
    spread = (math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))
              if n > 1 else 0.0)
    return {"mean": round(mean, 4), "stdev": round(spread, 4), "n": n,
            "values": [round(v, 4) for v in values]}


def _compared(on: list[float], against: list[float]) -> dict:
    a, b = _stats(on), _stats(against)
    difference = a["mean"] - b["mean"]
    error = math.sqrt((a["stdev"] ** 2) / max(a["n"], 1)
                      + (b["stdev"] ** 2) / max(b["n"], 1))
    low, high = difference - 2 * error, difference + 2 * error
    return {
        "on": a,
        "against": b,
        "difference": round(difference, 4),
        "interval": [round(low, 4), round(high, 4)],
        "percent": round(100 * difference / b["mean"], 2) if b["mean"] else None,
        # Two runs a side at least, or there is no spread to be sure against.
        "sure": a["n"] > 1 and b["n"] > 1 and (low > 0 or high < 0),
    }


def _machine(devices: set[str]) -> dict:
    return {"system": platform.platform(), "processor": platform.processor(),
            "device": sorted(devices)}


def _once(side: dict, headless: bool, how: dict) -> dict:
    """One timed run of one side: headless, or through whichever route draws here."""
    from . import offscreen

    if headless:
        return engine.run(side["script"], headless=True, root=side["root"], **how)
    # Timed with its window shown, since a minimised window may present frames
    # differently from the one a player looks at (§PW296).
    return offscreen.capture(side["script"], root=side["root"], quiet_window=False,
                             **how)


def _timed(sides: list[dict], runs: int, headless: bool, how: dict):
    """Every run of both sides, alternating, as the numbers each printed."""
    taken: list[list[dict]] = [[], []]
    failed, devices = [], set()
    for turn in range(runs):
        # One side then the other, and the other first next time, so drift is shared.
        for index in (0, 1) if turn % 2 == 0 else (1, 0):
            side = sides[index]
            found = _once(side, headless, how)
            log = Path(found["log"]).read_text(encoding="utf-8", errors="replace")
            devices.update(m["device"].strip() for m in DEVICE.finditer(log))
            line = how["expect"].search(log)
            if not found["ok"] or line is None:
                failed.append({"side": side["label"], "run": turn + 1,
                               "verdict": found.get("verdict"), "why": found.get("why"),
                               "log": found["log"]})
                continue
            end = log.find("\n", line.start())
            said = log[line.start(): end if end >= 0 else len(log)]
            taken[index].append({p["name"]: float(p["value"])
                                 for p in PAIR.finditer(said)})
    return taken, failed, devices


def _comparison(taken: list[list[dict]], measures) -> dict:
    """Each measure both sides printed, compared; only those named where some are."""
    on, against = taken
    names = sorted({n for r in on for n in r} & {n for r in against for n in r})
    if measures:
        names = [n for n in names if n in measures]
    return {name: _compared([r[name] for r in on if name in r],
                            [r[name] for r in against if name in r])
            for name in names}


def _previous(record: Path, sides: list[dict]) -> dict | None:
    """The last answer for this script, and whether either build has moved since."""
    try:
        last = json.loads(record.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return {
        "taken": last.get("taken"),
        "on": last.get("on"),
        "against": last.get("against"),
        "stale": (last.get("on", {}).get("build") != sides[0]["build"]
                  or last.get("against", {}).get("build") != sides[1]["build"]),
    }


@operation("engine.cost", kind="capture")
def cost(
    script: Annotated[str, Param("the timing script, as a path under the project")],
    *,
    expect: Annotated[
        str, Param("the line holding its numbers, as a pattern; name=number pairs")
    ],
    against: Annotated[str, Param("the revision to compare with")] = "HEAD",
    on: Annotated[str, Param("the revision measured; the working tree if unset")] = "",
    runs: Annotated[int, Param("runs each side, alternating", lo=2, hi=20)] = 5,
    args: Annotated[list, Param("the script's own arguments, after --")] = (),
    measures: Annotated[list, Param("only these names off the line")] = (),
    headless: Annotated[bool, Param("no window, for a CPU-only script")] = False,
    frames: Annotated[int, Param("each run's frame budget; the project's")] = None,
    timeout: Annotated[float, Param("each run's wall clock", unit="s")] = None,
    root: Annotated[str, Param("the project the engine runs")] = ".",
) -> dict:
    """What a change costs: one timing script on two builds, and how sure the gap is.

    A revision is checked out in a worktree under the work folder, never by stashing,
    and both sides are imported, then timed alternately, each with its own copy of the
    script. Each `name=number` on the `expect` line is answered with both means and
    spreads, the difference with a two-standard-error interval, and `sure`. The answer
    names the machine and device, is recorded, and says whether the last one went stale.
    """

    settings = load(root)
    here = settings.root
    work = settings.path("paths.work")
    path = Path(script)
    path = path if path.is_absolute() else here / path
    if not path.is_file():
        raise PolyweaveError(
            "engine.no-script", f"there is no scene script at {path}",
            "write the path relative to the project root",
        )
    if on == against:
        raise PolyweaveError(
            "engine.cost-same", f"both sides are {against or 'the working tree'}",
            "name the revision to compare with in against, and leave on unset for the "
            "working tree",
        )
    binary = engine.find(here)
    clock = float(settings.get("engine.timeout", timeout))
    sides = [_side(on, here, work), _side(against, here, work)]
    for side in sides:
        if not side.get("commit") or side.get("fresh"):
            _imported(side, binary, max(clock, 600.0))
    wanted = re.compile(expect, re.MULTILINE)
    inside = path.relative_to(here) if path.is_relative_to(here) else None
    for side in sides:
        own = side["root"] / inside if inside is not None else None
        side["script"] = own if own is not None and own.is_file() else path
        side["borrowed"] = side["script"] == path and side["root"] != here
    how = {"expect": wanted, "args": ("--", *(str(one) for one in args or ())),
           "frames": frames, "timeout": timeout, "fixed_fps": 0, "binary": binary}
    taken, failed, devices = _timed(sides, int(runs), headless, how)
    compared = _comparison(taken, measures)
    short = [s["label"] for s, got in zip(sides, taken, strict=True) if len(got) < 2]
    named = inside.as_posix() if inside is not None else str(path)
    key = hashlib.sha256(json.dumps(
        {"script": named, "args": list(args or ()), "expect": expect},
        sort_keys=True).encode("utf-8")).hexdigest()[:12]
    record = work / "cost" / f"{path.stem}-{key}.json"
    answer = {
        "ok": not short and bool(compared),
        "script": named,
        **{name: {"label": s["label"], "build": s["build"],
                  **({"script": "the working tree's"} if s["borrowed"] else {})}
           for name, s in zip(("on", "against"), sides, strict=True)},
        "runs": int(runs),
        "measures": compared,
        "sure": sorted(n for n, c in compared.items() if c["sure"]),
        "machine": _machine(devices),
        "failed": failed,
        "taken": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "previous": _previous(record, sides),
        "record": str(record),
    }
    if short:
        answer["why"] = (f"{', '.join(short)} had fewer than two runs that printed the "
                         "line, so there is nothing to compare; the failed runs name "
                         "their logs")
    elif not compared:
        answer["why"] = ("the line held no name=number both sides printed"
                         + (f" among {', '.join(measures)}" if measures else ""))
    write_atomic(record, json.dumps({k: v for k, v in answer.items()
                                     if k != "previous"}, indent=2) + "\n")
    return answer
