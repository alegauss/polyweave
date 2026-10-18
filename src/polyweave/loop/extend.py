"""A project's own measure, declared in polyweave.toml and run apart (§PW517).

The vocabulary polyweave ships is closed, and that rule stays: a name outside it is
refused. A look only one game needs, such as a glow at a rim, is declared by the
project instead, under `[extend.measures.<name>]`:

    fn        = "tools/art/rim.py:glow"   # called with the subject's path
    subject   = "picture"                 # or "file": what it is handed
    unit      = "ratio"
    range     = [0, 1]                    # a value outside it is refused, never clamped
    direction = "higher"                  # which way is better, for a search
    about     = "light at the silhouette over light in the body"

A spec names it `x.<project>.<name>`: the prefix keeps it from colliding with a built-in
and says plainly that it is not polyweave's. It is described from the TOML alone, so
describing it never imports the project's code. It runs in a separate interpreter with
a job's environment, through the job worker's own way of finding a target, so project
code is never imported into this process. Each value is kept with the digest of the
function's source file, and a changed function makes the values it produced stale.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from polyweave.kernel.config import load
from polyweave.kernel.errors import PolyweaveError

#: What a project measure's name begins with in a spec.
PREFIX = "x."

#: What a declaration takes, and which of it may be left out.
FIELDS = ("fn", "subject", "unit", "range", "direction", "about")
OPTIONAL = ("direction",)
SUBJECTS = ("picture", "file")
DIRECTIONS = ("higher", "lower")

#: How long one measure may take before it is called failed.
TIMEOUT = 300

#: Where each value is kept with the source it came from, under `[paths] work`.
KEPT = "extended.json"


@dataclass(frozen=True)
class Declared:
    """One project measure, as `[extend.measures.<short>]` declares it."""

    name: str
    short: str
    fn: str
    subject: str
    unit: str
    low: float
    high: float
    direction: str
    about: str

    def described(self) -> dict:
        return {"fn": self.fn, "subject": self.subject, "unit": self.unit,
                "range": [self.low, self.high], "direction": self.direction,
                "about": self.about}


def is_extended(name: str) -> bool:
    return str(name).startswith(PREFIX)


def declared(root: str | Path = ".") -> dict[str, Declared]:
    """Every measure the project declares, by the name a spec calls it."""
    config = load(root)
    project = str(config.get("project.name"))
    found = {}
    for short, entry in (config.get("extend.measures") or {}).items():
        one = _checked(short, entry, project)
        found[one.name] = one
    return found


def of(name: str, root: str | Path = ".") -> Declared:
    """The project measure a spec names, refused with the ones there are."""
    every = declared(root)
    if name not in every:
        raise PolyweaveError(
            "spec.unknown-measure",
            f"{name!r} is not a measure this project declares",
            f"name one of {', '.join(sorted(every))}" if every else
            "declare it under [extend.measures.<name>] in polyweave.toml",
            given=name,
            allowed=sorted(every),
        )
    return every[name]


def _checked(short: str, entry: Any, project: str) -> Declared:
    at = f"extend.measures.{short}"

    def refused(why: str, remedy: str) -> PolyweaveError:
        return PolyweaveError("config.bad-measure", f"[{at}] {why}", remedy,
                              given=short, at=at, allowed=FIELDS)

    if not isinstance(entry, dict):
        raise refused("is not a table", f"write it as [{at}] with {', '.join(FIELDS)}")
    unknown = sorted(set(entry) - set(FIELDS))
    missing = [one for one in FIELDS if one not in entry and one not in OPTIONAL]
    if unknown or missing:
        raise refused(
            f"has {', '.join(unknown)}, which it does not take" if unknown
            else f"says no {', '.join(missing)}",
            f"a measure takes {', '.join(FIELDS)}; direction may be left out",
        )
    fn = str(entry["fn"])
    if ":" not in fn or not fn.split(":", 1)[0].endswith(".py"):
        raise refused(f"names {fn!r} as its function",
                      "write fn as 'path/to/file.py:function', under the project")
    if entry["subject"] not in SUBJECTS:
        raise refused(f"is handed a {entry['subject']!r}",
                      f"set subject to one of {', '.join(SUBJECTS)}")
    direction = entry.get("direction", "higher")
    if direction not in DIRECTIONS:
        raise refused(f"moves {direction!r}",
                      f"set direction to one of {', '.join(DIRECTIONS)}")
    bounds = entry["range"]
    if (not isinstance(bounds, list) or len(bounds) != 2
            or not all(_number(one) for one in bounds) or bounds[0] >= bounds[1]):
        raise refused(f"gives the range {bounds!r}",
                      "write range as [low, high], two numbers, low first")
    return Declared(
        name=f"{PREFIX}{project}.{short}", short=short, fn=fn,
        subject=str(entry["subject"]), unit=str(entry["unit"]),
        low=float(bounds[0]), high=float(bounds[1]), direction=str(direction),
        about=str(entry["about"]),
    )


def _number(value: Any) -> bool:
    return (isinstance(value, int | float) and not isinstance(value, bool)
            and math.isfinite(value))


def source(one: Declared, root: str | Path) -> dict:
    """The function's file and its digest, which is what makes a value stale."""
    here = load(root).root
    path = here / one.fn.split(":", 1)[0]
    if not path.is_file():
        raise PolyweaveError(
            "spec.measure-failed",
            f"{one.name} names {one.fn}, and there is no file at {path}",
            "write fn as a path under the project, or put the file there",
            given=one.fn,
        )
    return {"fn": one.fn, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def measured(one: Declared, subject: str | Path, root: str | Path = ".") -> dict:
    """One project measure of one subject: its value, its unit and its source.

    Run in a separate interpreter, as a job's target is, and refused where it fails or
    answers a value outside its declared range. The value is kept with the digest of
    the source it came from.
    """
    here = load(root).root
    where = Path(subject) if Path(subject).is_absolute() else here / subject
    said = source(one, here)
    from polyweave.kernel.jobs.runner import _PACKAGE_ROOT

    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(_PACKAGE_ROOT), *([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])])
    try:
        done = subprocess.run(  # noqa: S603 - the project's own interpreter and code
            [sys.executable, "-m", "polyweave.loop.extend", one.fn, str(where),
             str(here)],
            cwd=here, env=env, capture_output=True, text=True, encoding="utf-8",
            timeout=TIMEOUT, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise PolyweaveError(
            "spec.measure-failed",
            f"{one.name} took more than {TIMEOUT}s on {where.name}",
            "make the function faster, or measure a smaller subject",
            given=one.fn,
        ) from exc
    answer = _answered(done.stdout)
    if done.returncode != 0 or answer is None or "error" in answer:
        raise PolyweaveError(
            "spec.measure-failed",
            f"{one.name} failed on {where.name}"
            + (f": {answer['error']}" if answer and answer.get("error") else ""),
            f"run {one.fn} on that file yourself; it is the project's code",
            given=one.fn,
            detail=(done.stderr or "")[-800:],
        )
    value = answer.get("value")
    if not _number(value) or not one.low <= value <= one.high:
        raise PolyweaveError(
            "spec.measure-out-of-range",
            f"{one.name} answered {value!r} for {where.name}, outside its declared "
            f"[{one.low:g}, {one.high:g}] {one.unit}",
            "fix the function, or the range it declares; a value is never clamped",
            given=str(value),
        )
    _keep(one, where, float(value), said, here)
    return {"value": float(value), "of": str(where), "unit": one.unit,
            "source": said}


def _answered(out: str) -> dict | None:
    for line in reversed((out or "").splitlines()):
        try:
            said = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(said, dict):
            return said
    return None


def _kept_at(here: Path) -> Path:
    return load(here).path("paths.work") / KEPT


def _keep(one: Declared, where: Path, value: float, said: dict, here: Path) -> None:
    from polyweave.kernel import provenance
    from polyweave.kernel.files import write_atomic

    path = _kept_at(here)
    held = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    held.setdefault(provenance.relative(where, here), {})[one.name] = {
        "value": value,
        "sha256": hashlib.sha256(where.read_bytes()).hexdigest(),
        "source": said,
        "at": datetime.now(tz=UTC).isoformat(timespec="seconds"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(path, json.dumps(held, indent=2, sort_keys=True) + "\n")


def stale(root: str | Path = ".") -> list[dict]:
    """Each kept value whose function changed since, or whose measure is gone."""
    here = load(root).root
    path = _kept_at(here)
    if not path.is_file():
        return []
    every = declared(here)
    out = []
    held = json.loads(path.read_text(encoding="utf-8"))
    for subject, measures in sorted(held.items()):
        for name, kept in sorted(measures.items()):
            one = every.get(name)
            if one is None:
                out.append({"subject": subject, "measure": name,
                            "why": "the project no longer declares it"})
                continue
            there = (here / one.fn.split(":", 1)[0]).is_file()
            now = source(one, here) if there else {"fn": one.fn, "sha256": ""}
            if now != kept["source"]:
                out.append({"subject": subject, "measure": name,
                            "why": f"{one.fn} changed since it was measured"})
    return out


def main(argv: list[str] | None = None) -> int:
    """Run one project measure in this interpreter and print its value as JSON."""
    from polyweave.kernel.jobs.worker import resolve_target

    fn, subject, root = (argv if argv is not None else sys.argv[1:])
    try:
        value = resolve_target(fn, Path(root))(str(subject))
    except Exception as exc:  # noqa: BLE001 - the project's code, said back as it failed
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}))
        return 1
    print(json.dumps({"value": value if _number(value) else repr(value)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
