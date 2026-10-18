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

#: What a declaration takes, and which of it may be left out. `why` says what built-in
#: it stands in for, which is how a gap it fills stays visible (§PW519).
FIELDS = ("fn", "subject", "unit", "range", "direction", "about", "why")
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
    why: str = ""

    def described(self) -> dict:
        return {"fn": self.fn, "subject": self.subject, "unit": self.unit,
                "range": [self.low, self.high], "direction": self.direction,
                "about": self.about, "why": self.why}


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
            f"a measure takes {', '.join(FIELDS)}; direction may be left out, and "
            "why says what built-in it stands in for",
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
        about=str(entry["about"]), why=str(entry["why"]),
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
    try:
        done = _run_apart([one.fn, str(where), str(here)], here)
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


# -- a project's own operations (§PW518) ---------------------------------------------

#: What an operation's declaration takes, and each of its parameters.
OPERATION_FIELDS = ("fn", "about", "why", "produces", "kind", "params", "producer")
PARAM_FIELDS = ("type", "about", "lo", "hi", "unit", "choices", "default")
PARAM_TYPES = ("str", "int", "float", "bool", "list", "dict")


@dataclass(frozen=True)
class Operation:
    """One project operation, as `[extend.operations.<short>]` declares it."""

    name: str
    short: str
    fn: str
    about: str
    produces: str | None
    #: A job kind where it runs as a job, and none where a call waits for it.
    kind: str | None
    parameters: tuple[dict, ...]
    #: Whether `search.sweep` may turn it, a sample at a time into its `out`.
    producer: bool
    #: What built-in it stands in for (§PW519).
    why: str = ""

    def described(self) -> dict:
        """What `describe` answers for it, in the shape a built-in's answer has."""
        return {
            "operation": self.name,
            "summary": self.about,
            "produces": self.produces,
            "kind": self.kind,
            "asynchronous": self.kind is not None,
            "parameters": [dict(one) for one in self.parameters],
            "layer": None,
            "project": {"fn": self.fn, "producer": self.producer, "why": self.why},
        }


def operations(root: str | Path = ".") -> dict[str, Operation]:
    """Every operation the project declares, by the name it is served as."""
    config = load(root)
    project = str(config.get("project.name"))
    found = {}
    for short, entry in (config.get("extend.operations") or {}).items():
        one = _operation(short, entry, project)
        found[one.name] = one
    return found


def operation(name: str, root: str | Path = ".") -> Operation:
    """The project operation a call names, refused with the ones there are."""
    every = operations(root)
    if name not in every:
        raise PolyweaveError(
            "op.unknown",
            f"there is no operation named {name!r} in this project",
            f"name one of {', '.join(sorted(every))}" if every else
            "declare it under [extend.operations.<name>] in polyweave.toml",
            given=name,
            allowed=sorted(every),
        )
    return every[name]


def _operation(short: str, entry: Any, project: str) -> Operation:
    from polyweave.kernel.jobs.stages import KINDS

    at = f"extend.operations.{short}"

    def refused(why: str, remedy: str) -> PolyweaveError:
        return PolyweaveError("config.bad-operation", f"[{at}] {why}", remedy,
                              given=short, at=at, allowed=OPERATION_FIELDS)

    if not isinstance(entry, dict):
        raise refused("is not a table", f"write it as [{at}] with fn and about")
    unknown = sorted(set(entry) - set(OPERATION_FIELDS))
    if unknown or not all(entry.get(one) for one in ("fn", "about", "why")):
        raise refused(
            f"has {', '.join(unknown)}, which it does not take" if unknown
            else "says no fn, about or why",
            f"an operation takes {', '.join(OPERATION_FIELDS)}; fn, about and why, "
            "what built-in it stands in for, are needed",
        )
    fn = str(entry["fn"])
    if ":" not in fn or not fn.split(":", 1)[0].endswith(".py"):
        raise refused(f"names {fn!r} as its function",
                      "write fn as 'path/to/file.py:function', under the project")
    kind = entry.get("kind")
    if kind is not None and kind not in KINDS:
        raise refused(f"runs as a {kind!r} job, which is no job kind",
                      f"set kind to one of {', '.join(sorted(KINDS))}, or leave it "
                      "out for a call that waits")
    params = entry.get("params") or {}
    parameters = tuple(_parameter(name, said, refused) for name, said in params.items())
    producer = bool(entry.get("producer", False))
    if producer and "out" not in {one["name"] for one in parameters}:
        raise refused("is a producer with no out parameter",
                      'declare params.out = { type = "str", about = "where it is '
                      'written" }: a search writes each sample there')
    return Operation(
        name=f"{PREFIX}{project}.{short}", short=short, fn=fn,
        about=str(entry["about"]),
        produces=str(entry["produces"]) if entry.get("produces") else None,
        kind=kind, parameters=parameters, producer=producer, why=str(entry["why"]),
    )


def _parameter(name: str, said: Any, refused) -> dict:
    if not isinstance(said, dict) or said.get("type") not in PARAM_TYPES \
            or not said.get("about") or set(said) - set(PARAM_FIELDS):
        raise refused(
            f"declares the parameter {name!r} as {said!r}",
            f"write params.{name} = {{ type = ..., about = ... }}, the type one of "
            f"{', '.join(PARAM_TYPES)}, with lo, hi, unit, choices or default",
        )
    low, high = said.get("lo"), said.get("hi")
    return {
        "name": name,
        "type": said["type"],
        "required": "default" not in said,
        "default": said.get("default"),
        "about": str(said["about"]),
        **({"range": [low, high]} if low is not None or high is not None else {}),
        **({"choices": list(said["choices"])} if said.get("choices") else {}),
        **({"unit": str(said["unit"])} if said.get("unit") else {}),
    }


def called(name: str, args: dict | None, root: str | Path = ".") -> dict:
    """One call of a project operation, held to its declaration before it runs.

    One declaring a `kind` is started as a job and answers its handle; any other runs
    in a separate interpreter and answers what the function returned, with the record
    written for what it produced.
    """
    from polyweave.kernel import describe as D

    one = operation(name, root)
    values = D.checked(one.name, one.parameters, dict(args or {}))
    if one.kind:
        from polyweave.kernel.jobs import JobStore

        return JobStore.for_project(root).start(
            "polyweave.loop.extend:job", kind=one.kind, label=one.name,
            args={"operation": one.name, "values": values},
        )
    return apart(one, values, root)


def apart(one: Operation, values: dict, root: str | Path = ".") -> dict:
    """Run a project operation in a separate interpreter, as a job's target runs."""
    here = load(root).root
    done = _run_apart(["make", one.name, json.dumps(values), str(here)], here)
    answer = _answered(done.stdout)
    if done.returncode != 0 or answer is None or "error" in answer:
        raise PolyweaveError(
            "op.project-failed",
            f"{one.name} failed"
            + (f": {answer['error']}" if answer and answer.get("error") else ""),
            f"run {one.fn} yourself with those arguments; it is the project's code",
            given=one.fn,
            detail=(done.stderr or "")[-800:],
        )
    return answer


def job(report, *, operation: str, values: dict) -> dict:
    """A project operation run as a job: the worker is the project's interpreter."""
    report.stage("building", note=f"running {operation}")
    return made(operation, values, ".")


def made(name: str, values: dict, root: str | Path = ".") -> dict:
    """Call the project's function here and record what it produced.

    What it returns is its answer. Where it says an `artefact`, or answers a path, and
    the operation `produces` something, the file is recorded with the function's source
    as an input, so a changed function makes it stale.
    """
    from polyweave.kernel import provenance
    from polyweave.kernel.jobs.worker import resolve_target

    here = load(root).root
    one = operation(name, here)
    said = resolve_target(one.fn, here)(**values)
    artefact = said.get("artefact") if isinstance(said, dict) else (
        said if isinstance(said, str) else None)
    recorded = None
    if artefact and one.produces:
        where = Path(artefact) if Path(artefact).is_absolute() else here / artefact
        record = provenance.build(
            "extend", where, root=here, params=values,
            engine={"name": "project", "operation": one.name},
            inputs=[provenance.source("fn", here / one.fn.split(":", 1)[0], here)],
        )
        recorded = str(provenance.write(record, here))
    return {"result": said, "artefact": artefact, "recorded": recorded}


def drawer(name: str, root: str | Path = "."):
    """What `search.sweep` calls for one sample of a project producer (§PW518)."""
    one = operation(name, root)
    if not one.producer:
        raise PolyweaveError(
            "search.unknown-producer",
            f"{one.name} is not declared a producer, so a search does not turn it",
            f"set producer = true under [extend.operations.{one.short}]",
            given=one.name,
            allowed=sorted(n for n, o in operations(root).items() if o.producer),
        )

    def draw(report, *, out, rung=None, root=root, inline=True, **values):
        from polyweave.kernel import describe as D

        checked = D.checked(one.name, one.parameters, {**values, "out": str(out)})
        said = apart(one, checked, root)
        return {"artefact": said.get("artefact") or str(out)}

    return draw


# -- what polyweave does not yet do (§PW519) ------------------------------------------


def accounted(root: str | Path = ".") -> list[dict]:
    """Every extension the project declares, as what polyweave does not do yet.

    Each with the built-in it stands in for (`why`), how often the project's own
    records show it used, and the date polyweave.toml first declared it where git can
    say. A measure is used once per value kept; an operation once per file recorded as
    its make. A declaration that cannot be read is left to `project.check`.
    """
    here = load(root).root
    used: dict[str, int] = {}
    kept = _kept_at(here)
    if kept.is_file():
        for measures in json.loads(kept.read_text(encoding="utf-8")).values():
            for name in measures:
                used[name] = used.get(name, 0) + 1
    from polyweave.kernel import provenance

    for record in provenance._records(here):
        if record.get("kind") == "extend":
            name = (record.get("engine") or {}).get("operation")
            used[name] = used.get(name, 0) + 1
    out = []
    for kind, read in (("measure", declared), ("operation", operations)):
        try:
            found = read(here)
        except PolyweaveError:
            continue
        for name, one in sorted(found.items()):
            table = f"[extend.{kind}s.{one.short}]"
            out.append({"name": name, "kind": kind, "fn": one.fn, "why": one.why,
                        "used": used.get(name, 0),
                        "first_declared": _first_declared(here, table)})
    return out


def _first_declared(here: Path, table: str) -> str | None:
    """The day a commit first wrote `table` into polyweave.toml, or None."""
    try:
        done = subprocess.run(
            ["git", "log", "--reverse", "--format=%ad", "--date=short", "-S", table,
             "--", "polyweave.toml"],
            cwd=here, capture_output=True, text=True, encoding="utf-8", timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    days = done.stdout.split() if done.returncode == 0 else []
    return days[0] if days else None


def depended(measures: list[str], artefact: str | None,
             root: str | Path = ".") -> list[dict]:
    """The extensions an asset's bar or its artefact depends on, for its brief."""
    from polyweave.kernel import provenance

    here = load(root).root
    out = []
    for name in sorted({one for one in measures if is_extended(one)}):
        one = declared(here).get(name)
        out.append({"name": name, "kind": "measure", "why": one.why if one else None,
                    "in": "its bar"})
    if artefact:
        try:
            record = provenance.read(artefact, here)
        except PolyweaveError:
            record = {}
        if record.get("kind") == "extend":
            name = (record.get("engine") or {}).get("operation")
            one = operations(here).get(name)
            out.append({"name": name, "kind": "operation",
                        "why": one.why if one else None, "in": "its build"})
    return out


def _run_apart(argv: list[str], here: Path) -> subprocess.CompletedProcess:
    from polyweave.kernel.jobs.runner import _PACKAGE_ROOT

    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(_PACKAGE_ROOT), *([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])])
    return subprocess.run(  # noqa: S603 - the project's own interpreter and code
        [sys.executable, "-m", "polyweave.loop.extend", *argv],
        cwd=here, env=env, capture_output=True, text=True, encoding="utf-8",
        timeout=TIMEOUT, check=False,
    )


def main(argv: list[str] | None = None) -> int:
    """Run one project measure, or one project operation, here; print it as JSON."""
    from polyweave.kernel.jobs.worker import resolve_target

    args = argv if argv is not None else sys.argv[1:]
    try:
        if args[0] == "make":
            _, name, values, root = args
            print(json.dumps(made(name, json.loads(values), root), default=str))
            return 0
        fn, subject, root = args
        value = resolve_target(fn, Path(root))(str(subject))
    except Exception as exc:  # noqa: BLE001 - the project's code, said back as it failed
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}))
        return 1
    print(json.dumps({"value": value if _number(value) else repr(value)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
