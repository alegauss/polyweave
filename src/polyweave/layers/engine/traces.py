"""Two runs of the same level compared entity by entity, and the first to part named
(§PW612).

Spinhold's stage editor replays a level to its playhead through the game's own code,
and a headless run plays the same level; the editor is right only if every entity stands
where the run has it, second by second. The same question is asked of a replay against
the run it recorded, a build against the one before, a fixed timestep against a variable
one, or two machines in lockstep, and the determinism kit's proof answers it only inside
the engine, exactly, for the state kit's names. So a run writes a trace and polyweave
compares two:

    {"frame": 0, "id": "wasp-1", "kind": "enemy", "position": [120.0, 40.0], "hp": 3}
    {"frame": 0, "id": "player", "kind": "player", "position": [320.0, 300.0]}
    {"frame": 1, "id": "wasp-1", "kind": "enemy", "position": [121.5, 40.0], "hp": 3}

One JSON object a line: the time (`frame`, or `t` in seconds, as `[trace] time` says),
the entity's stable `id`, its `kind`, and any fields the project chooses. Nothing about
a genre is built in. `[trace] tolerance` holds a field to a distance, a number's
difference or a list's Euclidean one (`position = 0.5`); anything not named must be
equal, since determinism means the same bits. The answer names the first entity and
field that parted, when, by how much and what each run said; every other entity's first
divergence after it is listed as a consequence, not a failure of its own. An entity one
run has at a time and the other has not parts on `exists`, and two runs that end apart
part on `ended`. `[trace] pairs` declares the pairs a gate holds to agree.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Annotated, Any

from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

#: The time keys a trace may be stamped by.
TIMES = ("frame", "t")
#: The consequences listed in full; the rest are counted.
LISTED = 20


def read(path: Path, time: str) -> dict[tuple, dict]:
    """A trace's samples by (time, id), each its fields, in the file's order."""
    if not path.is_file():
        raise PolyweaveError(
            "game.no-trace",
            f"there is no trace at {path}",
            "have the run write one, a JSON object a line, and name it under the "
            "project",
            given=str(path),
        )
    samples: dict[tuple, dict] = {}
    with path.open(encoding="utf-8-sig") as lines:
        for number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                one = json.loads(line)
            except ValueError as broken:
                raise _bad(path, number, f"is not JSON: {broken}") from None
            if not isinstance(one, dict) or time not in one or "id" not in one:
                raise _bad(path, number, f"has no {time!r} and 'id'")
            key = (one.pop(time), str(one.pop("id")))
            if key in samples:
                raise _bad(path, number, f"repeats {key[1]} at {time} {key[0]}")
            samples[key] = one
    if not samples:
        raise _bad(path, 0, "holds no sample, so there is nothing to compare")
    return samples


def _bad(path: Path, number: int, what: str) -> PolyweaveError:
    return PolyweaveError(
        "game.bad-trace",
        f"{path.name}{f', line {number},' if number else ''} {what}",
        "write each line as {\"frame\": <n>, \"id\": <stable id>, \"kind\": <kind>, "
        "<field>: <value>, ...}, or set [trace] time to the key the run stamps by",
        given=str(path),
    )


def distance(one: Any, other: Any) -> float | None:
    """How far apart two values are, or None where they can only be equal or not."""
    if _number(one) and _number(other):
        return abs(float(one) - float(other))
    if (isinstance(one, list) and isinstance(other, list) and len(one) == len(other)
            and all(_number(a) and _number(b)
                    for a, b in zip(one, other, strict=True))):
        return math.dist([float(a) for a in one], [float(b) for b in other])
    return None


def _number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _parted(field: str, one: Any, other: Any, tolerance: dict) -> dict | None:
    """The divergence of one field, or None where the two runs agree on it."""
    apart = distance(one, other)
    bound = float(tolerance.get(field, 0.0))
    if apart is not None:
        return None if apart <= bound else {"by": round(apart, 9)}
    return None if one == other else {"by": None}


def compare(one: dict, other: dict, tolerance: dict) -> dict:
    """Two traces read by `read`, compared; the first divergence and what followed."""
    ends = {"one": max(k[0] for k in one), "other": max(k[0] for k in other)}
    # Past the earlier end only one run speaks, which is `ended`, not every entity.
    common = min(ends.values())
    first_of: dict[str, dict] = {}
    order = {key: index for index, key in enumerate(one)}
    for key in sorted(set(one) | set(other), key=lambda k: (k[0], order.get(k, 1e18))):
        at, entity = key
        if at > common or entity in first_of:
            continue
        said, says = one.get(key), other.get(key)
        if said is None or says is None:
            first_of[entity] = {"at": at, "id": entity, "field": "exists",
                                "one": said is not None, "other": says is not None,
                                "by": None}
            continue
        for field in [*said, *(f for f in says if f not in said)]:
            parted = _parted(field, said.get(field), says.get(field), tolerance)
            if parted is not None:
                first_of[entity] = {"at": at, "id": entity, "field": field,
                                    "one": said.get(field), "other": says.get(field),
                                    **parted}
                break
    parted = list(first_of.values())
    if not parted and ends["one"] != ends["other"]:
        parted = [{"at": common, "id": None, "field": "ended", "one": ends["one"],
                   "other": ends["other"], "by": None}]
    first, after = (parted[0], parted[1:]) if parted else (None, [])
    return {
        "agree": first is None,
        "first": first,
        "consequences": after[:LISTED],
        "more": max(0, len(after) - LISTED),
        "ends": ends,
        "compared": {"samples": len(set(one) & set(other)),
                     "entities": len({k[1] for k in one} | {k[1] for k in other})},
        "says": _said(first, len(after)),
    }


def _said(first: dict | None, after: int) -> str:
    if first is None:
        return "the two runs agree on every entity at every time"
    if first["field"] == "ended":
        return (f"the two runs agree until one ends, at {first['one']} and "
                f"{first['other']}")
    by = f" by {first['by']:g}" if first.get("by") is not None else ""
    return (f"{first['id']} parted first, on {first['field']} at {first['at']}{by}: "
            f"{json.dumps(first['one'])} against {json.dumps(first['other'])}"
            + (f"; {after} more entities parted after it" if after else ""))


@operation("game.compare_runs")
def compare_runs(
    one: Annotated[str, Param("the first run's trace, .jsonl under the project")] = "",
    other: Annotated[str, Param("the second run's trace, held against the first")] = "",
    *,
    tolerance: Annotated[
        dict, Param("a distance per field, over [trace] tolerance; exact if unnamed")
    ] = None,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Whether two runs' entity traces agree, and if not, which entity parted first,
    on which field, when and by how much (§PW612).

    Every other entity's first divergence after it is a consequence, listed in order.
    With neither trace named, every pair [trace] pairs declares is compared, and
    `passed` is whether all agree: the gate's form.
    """
    config = load(root)
    here = config.root
    time = str(config.get("trace.time"))
    if time not in TIMES:
        raise PolyweaveError(
            "game.bad-trace",
            f"[trace] time is {time!r}, and a trace is stamped by frame or t",
            'set [trace] time = "frame", or "t" for seconds',
            given=time, allowed=list(TIMES),
        )
    held = {**(config.get("trace.tolerance") or {}), **(tolerance or {})}
    if bool(one) != bool(other):
        raise PolyweaveError(
            "game.bad-target",
            "two runs are compared, and one was named",
            "name both one and other, or neither to compare every [trace] pairs",
        )
    if one:
        return {"one": one, "other": other,
                **compare(read(here / one, time), read(here / other, time), held)}
    pairs = config.get("trace.pairs") or []
    if not pairs:
        raise PolyweaveError(
            "game.no-trace",
            "no traces were named and [trace] pairs declares none",
            'name one and other, or declare pairs = [{one = "...", other = "..."}]',
        )
    answers = []
    for pair in pairs:
        if not (isinstance(pair, dict) and pair.get("one") and pair.get("other")):
            raise PolyweaveError(
                "game.bad-trace",
                f"[trace] pairs holds {pair!r}, and a pair names one and other",
                'write each as {one = "runs/a.jsonl", other = "runs/b.jsonl"}',
                given=str(pair),
            )
        found = compare(read(here / pair["one"], time),
                        read(here / pair["other"], time), held)
        answers.append({"one": pair["one"], "other": pair["other"], **found})
    return {"pairs": answers, "passed": all(a["agree"] for a in answers),
            "says": "; ".join(f"{a['other']}: {a['says']}" for a in answers)}
