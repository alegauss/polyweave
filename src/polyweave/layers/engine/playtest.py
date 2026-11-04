"""What players met in a level, read off the events their runs wrote (§PW327).

A level's probe says what a level asks (§PW202), never what happened when a person
played it, and the owner of a shooter wants balance measured, not felt. So a run writes
its events, one JSON object a line, and polyweave reads one run or many:

    {"t": 12.4, "event": "spawn", "id": "mote-17", "kind": "mote", "weight": 1.0}
    {"t": 13.1, "event": "hit", "kind": "lancer"}
    {"t": 14.0, "event": "kill", "id": "mote-17"}
    {"t": 20.2, "event": "life_lost"}

`t` is seconds from the level's start and `event` is the project's own word; nothing
about a genre is built in. An `id` pairs a `spawn` with the event that ends it (by
default `kill`), which is how many are alive each second is known, and a `weight`
counts an event at more than one. `level.trace` answers each event per second and in
all, averaged over the runs, the alive count per second, and its peak.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Annotated, Any

from polyweave.kernel import provenance
from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError
from polyweave.kernel.files import write_atomic


def _events(path: Path) -> list[dict]:
    """One run's events, each with its time, refused on a line that is not one."""
    if not path.is_file():
        raise PolyweaveError(
            "game.no-trace", f"there is no trace at {path}",
            "have the run write its events, a JSON object a line, and name it under "
            "the project", given=str(path))
    out = []
    with path.open(encoding="utf-8-sig") as lines:
        for number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                one = json.loads(line)
            except json.JSONDecodeError as exc:
                raise _bad(path, number, "is not JSON") from exc
            t = one.get("t") if isinstance(one, dict) else None
            if (not isinstance(t, int | float) or isinstance(t, bool) or t < 0
                    or not isinstance(one.get("event"), str) or not one["event"]):
                raise _bad(path, number, "has no t in seconds from 0 and no event word")
            weight = one.get("weight", 1)
            if not isinstance(weight, int | float) or isinstance(weight, bool):
                raise _bad(path, number, "has a weight that is no number")
            out.append(one)
    return out


def _bad(path: Path, number: int, why: str) -> PolyweaveError:
    return PolyweaveError(
        "game.bad-trace", f"{path.name} line {number} {why}",
        'write each line as {"t": 12.4, "event": "spawn", "id": "mote-17"}',
        given=f"{path.name}:{number}")


def _per_second(events: list[dict], seconds: int, starts: str,
                ends: str) -> tuple[dict[str, list[float]], list[float]]:
    """Each event's weighted count in each second, and how many are alive in it: a
    `starts` event whose `id` no `ends` event has closed by the second's end."""
    counts: dict[str, list[float]] = {}
    for one in events:
        row = counts.setdefault(one["event"], [0.0] * seconds)
        row[min(int(one["t"]), seconds - 1)] += float(one.get("weight", 1))
    opened = {one["id"]: one["t"] for one in events
              if one["event"] == starts and "id" in one}
    closed = {one["id"]: one["t"] for one in events
              if one["event"] == ends and "id" in one}
    alive = [0.0] * seconds
    for ident, began in opened.items():
        stop = math.ceil(closed[ident]) if ident in closed else seconds
        for s in range(int(began), min(seconds, stop)):
            alive[s] += 1.0
    return counts, alive


@operation("level.trace")
def trace(
    traces: Annotated[list, Param("the runs' event traces under the project")],
    *,
    starts: Annotated[str, Param("the event an alive thing starts at")] = "spawn",
    ends: Annotated[str, Param("the event that ends it, paired by id")] = "kill",
    out: Annotated[str, Param("where to write the answer, recorded; nowhere if empty")]
    = "",
    root: Annotated[str, Param("the project the traces are under")] = ".",
) -> dict:
    """What players met in a level: each event per second and in all, and how many
    were alive, averaged over the runs their traces record (§PW327)."""
    here = load(root).root
    if not traces:
        raise PolyweaveError("game.no-trace", "no trace was named",
                             "pass traces, the runs' event files under the project")
    paths = [here / str(one) for one in traces]
    runs = [_events(path) for path in paths]
    seconds = max(1, max((math.floor(one["t"]) + 1 for run in runs for one in run),
                         default=1))
    per_run = [_per_second(run, seconds, starts, ends) for run in runs]
    names = sorted({name for counts, _ in per_run for name in counts})
    n = len(runs)
    events = {name: [round(sum(counts.get(name, [0.0] * seconds)[s]
                               for counts, _ in per_run) / n, 4)
                     for s in range(seconds)] for name in names}
    alive = [round(sum(a[s] for _, a in per_run) / n, 4) for s in range(seconds)]
    answer: dict[str, Any] = {
        "runs": n,
        "seconds": seconds,
        "totals": {name: round(sum(row), 4) for name, row in events.items()},
        "peak_alive": max(alive),
        "events": events,
        "alive": alive,
    }
    if out:
        target = here / out
        write_atomic(target, json.dumps(answer, indent=1) + "\n")
        provenance.write(provenance.build(
            "capture", target, root=here,
            inputs=[provenance.source("trace", path, root=here) for path in paths],
            params={"starts": starts, "ends": ends}), root=here)
        answer["written"] = provenance.relative(target, here)
    busiest = max(alive)
    answer["says"] = (
        f"{n} run(s) over {seconds} s: "
        + ", ".join(f"{name} {total:g}" for name, total in answer["totals"].items())
        + f" a run; at most {busiest:g} alive, in second {alive.index(busiest)}")
    return answer
