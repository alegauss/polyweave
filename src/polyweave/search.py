"""Finding a rig number by searching for it, rather than by hand.

The evidence is §PW13: fourteen tuned constants in Cottony's rig were each found the
same way — render, look, change a number, render again — at two minutes a sample. That
is the single largest cost in making an asset, and a search a machine should be running.

Given an acceptance spec and a cheap rung, the loop is mechanical: propose values,
render at the lowest rung that can evaluate the predicates, score, continue. The space
is small and mostly continuous, so a coarse grid then local refinement is enough, and
the interesting engineering is in the **evaluation budget** rather than the optimiser.

Two things keep it honest:

- It searches **only the parameters it is told it may search**, over the ranges the spec
  states. It can tune the exposure; it cannot decide the asset should be twice as large.
- It reports the winner's score **against every individual predicate**, so a spec
  satisfied by an ugly render is visible as exactly that rather than as a success.
"""

from __future__ import annotations

import difflib
import inspect
import itertools
import math
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import Annotated, Any

from . import accept, loop
from .accept import Spec
from .describe import Param, operation
from .doors import Blank, door
from .errors import PolyweaveError

#: How many points each axis gets in a pass, before the window closes around the best.
POINTS = 3

#: How many renders a search may spend unless the caller says otherwise. A number, not a
#: wall-clock: the budget is the thing being managed, and it has to be legible.
BUDGET = 24

#: What a render takes that should not change the look (§PW107). A search turning one
#: would pick whichever seed the noise happened to favour.
NOISE = ("seed", "samples", "size")


def grid(
    low: float, high: float, points: int, step: float | None = None
) -> list[float]:
    """Evenly spaced values across a range, snapped to the step where there is one."""
    if high < low:
        low, high = high, low
    points = max(2, int(points))
    if step:
        count = int(math.floor((high - low) / step)) + 1
        if count <= points:
            return [round(low + i * step, 10) for i in range(max(1, count))]
    if high == low:
        return [low]
    span = (high - low) / (points - 1)
    values = [low + i * span for i in range(points)]
    if step:
        snapped = {round(low + round((v - low) / step) * step, 10) for v in values}
        values = sorted(snapped)
    return [round(v, 10) for v in values]


def ranges(spec: Spec) -> dict[str, dict]:
    """What this spec permits a search to turn, refusing to run without any."""
    if not spec.search:
        raise PolyweaveError(
            "search.nothing-to-search",
            f"{spec.asset or 'this spec'} names no parameter a search may turn",
            "add a [search.<param>] range; a parameter not named there is not searched",
        )
    return spec.search


def turnable(draw: Callable, *wanted: dict, also: dict = ()) -> list[str]:
    """Refuse a parameter the renderer has no knob for, and say what the rest are in.

    Returns every axis as `name (unit)` where the unit is declared, which is the half
    that catches a name this renderer takes and the caller means differently (§PW63).

    A spec's search axes and a renderer's parameters are two lists, and until §PW36
    nothing reconciled them. Adopting Cottony is what found it: that project's rig calls
    the whole-rig scale `light` and the shape's weight `form`, both of which the
    acceptance spec's own worked example carried, and neither is a parameter here. The
    spec loaded, `ranges` returned the axis, and the search died on its first sample
    with a bare `TypeError` — no code, no remedy, and the setup already paid for.

    Checked here rather than in `ranges`, because this is the one place that knows which
    callable is about to receive the values: geometry turns its own parameters through
    the same spec and they are not this renderer's (§PW32).

    A renderer taking `**kwargs` is not checked. It has said it accepts anything, and a
    stand-in written for a test is the usual one.
    """
    from .render.rig import described

    noise = sorted({name for one in wanted for name in one} & set(NOISE))
    if noise:
        raise PolyweaveError(
            "search.noise-axis",
            f"a search may not turn {', '.join(noise)}, which changes the noise and "
            "should not change the look",
            "drop the range; a bound's room for that noise is what `calibrate` "
            "measures (§PW107)",
            call=door(
                "calibrate.run",
                spec=Blank("the spec"),
                accepted=Blank("the render a person accepted"),
            ),
        )
    taken = inspect.signature(draw).parameters
    asked = [name for one in (*wanted, dict(also)) for name in one]
    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in taken.values()):
        return [described(name) for name in asked]
    unknown = [name for name in asked if name not in taken]
    if not unknown:
        # Every axis with what it is measured in. A name this renderer takes can still
        # mean something else where the number came from (§PW63) — Cottony's `fill` is
        # the fraction of the frame a model fills and this one is a light in watts — and
        # a guard that only refuses unknown names cannot see that. Saying the unit back
        # is what puts the mistake in front of whoever made it.
        return [described(name) for name in asked]
    near = difflib.get_close_matches(unknown[0], taken, n=1)
    raise PolyweaveError(
        "search.unknown-parameter",
        f"nothing here turns {', '.join(sorted(set(unknown)))}",
        f"did you mean {described(near[0])}?"
        if near
        else "name a parameter the renderer takes, or drop the range",
    )


def _points_per_axis(axes: int, budget: int, points: int) -> int:
    """As fine a grid as the budget affords, and never coarser than two."""
    if axes <= 0:
        return 0
    affordable = int(budget ** (1.0 / axes))
    return max(2, min(points, affordable))


def slowest_first(names: Sequence[str], rebuilding: Sequence[str]) -> list[str]:
    """Order the axes so the expensive ones change least often.

    §PW32: rebuilding geometry costs more than re-rendering it, so a mixed search over
    shape and rig has to order its sampling to rebuild as rarely as it can. The whole
    fix is where a name sits in the product: the cartesian product varies its **last**
    axis fastest, so putting the rebuilding parameters first holds one shape still while
    every rig value is swept over it.
    """
    rebuilds = set(rebuilding)
    return sorted(names, key=lambda name: (name not in rebuilds, name))


def rebuilds_in(samples: Sequence[dict], rebuilding: Sequence[str]) -> int:
    """How many times the geometry actually changed across a run of samples.

    The number the ordering exists to keep down, reported rather than assumed.
    """
    watched = sorted(set(rebuilding))
    if not watched:
        return 0
    count, last = 0, None
    for sample in samples:
        shape = tuple(round(float(sample["params"][n]), 10) for n in watched)
        if shape != last:
            count += 1
            last = shape
    return count


def search(
    spec: Spec,
    evaluate: Callable[[dict], dict] | None = None,
    *,
    evaluate_all: Callable[[list[dict]], list[dict]] | None = None,
    budget: int = BUDGET,
    points: int = POINTS,
    passes: int = 3,
    rebuilding: Sequence[str] = (),
) -> dict:
    """Search the spec's permitted parameters for values that satisfy its predicates.

    `evaluate` takes one set of parameter values and returns what `accept.check`
    returns. Everything about rendering is on the other side of it, so this is testable
    without a renderer and a parallel evaluator is a drop-in.

    `evaluate_all` is that drop-in: it takes the whole pass at once and returns a list
    in the same order, which is what lets four samples be four handles rather than four
    waits (§PW45). The job system was built for exactly this and the search was not
    using it, so a budget of twenty-four was twenty-four renders end to end on a machine
    that could run four at a time. One of the two is required, and never both.

    A search that has already found its answer stops: there is no reason to pay for the
    renders after a spec passes with nothing left to gain. That is why a pass is what is
    batched rather than the whole budget: the stopping is per pass, and handing over
    every sample at once would pay for the ones the answer made unnecessary.
    """
    if (evaluate is None) == (evaluate_all is None):
        raise PolyweaveError(
            "search.no-evaluator",
            "a search needs exactly one of evaluate and evaluate_all",
            "pass `evaluate` for one sample at a time, or `evaluate_all` for a whole "
            "pass at once",
        )
    permitted = ranges(spec)
    if budget < 1:
        raise PolyweaveError(
            "search.no-budget",
            f"a budget of {budget} renders cannot evaluate anything",
            "give it at least one render to spend",
        )

    # The expensive axes go first, so the product holds a shape still while it sweeps
    # everything cheap over it (§PW32). With nothing expensive this is plain sorting.
    names = slowest_first(sorted(permitted), rebuilding)
    windows = {
        n: (float(permitted[n]["min"]), float(permitted[n]["max"])) for n in names
    }
    steps = {n: permitted[n].get("step") for n in names}

    trace: list[dict] = []
    seen: dict[tuple, dict] = {}
    best: dict | None = None
    roomiest: float | None = None
    spent = 0
    stopped = "the budget ran out"

    for _ in range(max(1, passes)):
        per_axis = _points_per_axis(len(names), budget - spent, points)
        axes = [
            grid(*windows[n], per_axis, steps[n] and float(steps[n])) for n in names
        ]
        # The pass is settled before anything is evaluated, which is what makes handing
        # the whole of it over possible: deduplicated against what has been seen and cut
        # to what the budget still affords (§PW45).
        wanted: list[tuple[tuple, dict]] = []
        for combination in itertools.product(*axes):
            if spent + len(wanted) >= budget:
                break
            key = tuple(round(v, 10) for v in combination)
            if key in seen or any(key == k for k, _ in wanted):
                continue
            wanted.append((key, dict(zip(names, combination, strict=True))))

        results = (
            evaluate_all([v for _, v in wanted])
            if evaluate_all is not None
            else [evaluate(v) for _, v in wanted]
        )
        if len(results) != len(wanted):
            raise PolyweaveError(
                "search.batch-mismatch",
                f"{len(wanted)} samples were handed over and {len(results)} came back",
                "return one result per sample, in the order they were given",
            )

        for (key, values), found in zip(wanted, results, strict=True):
            spent += 1
            sample = {
                "params": values,
                "score": float(found.get("score", 0.0)),
                "passed": bool(found.get("passed", False)),
                "headroom": found.get("headroom"),
                "result": found,
            }
            seen[key] = sample
            # Every sample keeps its score against every predicate and the key its
            # picture is cached under: a search nobody can inspect is one nobody can
            # overrule, and §PW15 is what that costs.
            trace.append(
                {
                    "params": values,
                    "score": sample["score"],
                    "passed": sample["passed"],
                    "predicates": [
                        {k: p.get(k) for k in ("id", "value", "margin", "passed")}
                        for p in found.get("predicates", [])
                    ],
                    "render": found.get("render", {}),
                }
            )
            if best is None or _ranked(sample) > _ranked(best):
                best = sample

        if best is not None and best["passed"] and best["score"] >= 1.0:
            # Passing is not the same as passing comfortably (§PW104). Where the
            # evaluator measures headroom the search keeps going while a pass still
            # raises it; where it does not, a pass is all there is to find.
            room = best.get("headroom")
            if room is None:
                stopped = "the spec passed with nothing left to gain"
                break
            if roomiest is not None and room <= roomiest + 1e-9:
                stopped = "the spec passed, and a further pass found no more headroom"
                break
            roomiest = room
        if spent >= budget:
            break
        windows = _close_around(best, windows, steps, per_axis)
        if not windows:
            stopped = "the window closed to a single value on every axis"
            break
    else:
        stopped = "the passes ran out"

    if best is None:  # pragma: no cover - a budget of at least one always evaluates
        raise PolyweaveError(
            "search.no-budget",
            "the search evaluated nothing",
            "give it a budget of at least one render",
        )
    return {
        "asset": spec.asset,
        "searched": names,
        "rebuilding": sorted(set(rebuilding) & set(names)),
        "rebuilds": rebuilds_in(trace, set(rebuilding) & set(names)),
        "budget": budget,
        "spent": spent,
        "stopped": stopped,
        "passed": best["passed"],
        "score": best["score"],
        "best": best["params"],
        "predicates": best["result"].get("predicates", []),
        "failed": best["result"].get("failed", []),
        # How far inside its tightest bound the answer sits, and which bound that is.
        "headroom": best["result"].get("headroom"),
        "tightest": best["result"].get("tightest"),
        "trace": trace,
    }


def family(
    members: Sequence[dict],
    *,
    name: str = "family",
    ranges: dict | None = None,
    **how: Any,
) -> dict:
    """One set of values searched against every member of a family at once (§PW105).

    Each member is `{"name", "spec", "evaluate"}`: its own spec and the evaluator that
    renders it with what it fixes (colour, size, model). A sample passes when every
    member passes, scores the worst member's score and has the least headroom any member
    left, so the search climbs towards what the whole family accepts rather than what
    one member does. The axes are `ranges`, or the first member's `[search]`.

    Where nothing passes on every member, the answer carries the `conflict`: the pair of
    predicates on different members that each passed somewhere and never together, and
    the sample nearest each side. That is the question a person has to answer.
    """
    if not members:
        raise PolyweaveError(
            "search.no-evaluator",
            "a family search was given no members",
            "give it at least one member, each with a name, a spec and an evaluator",
        )
    seen: list[dict] = []

    def evaluate(values: dict) -> dict:
        answers = {one["name"]: one["evaluate"](values) for one in members}
        seen.append({"params": dict(values), "answers": answers})
        return _joined(answers)

    axes = ranges or members[0]["spec"].search
    spec = Spec(asset=name, rung=None, predicates=(), search=dict(axes))
    found = search(spec, evaluate, **how)
    found["members"] = {
        one["name"]: _joined(
            {one["name"]: _answer_at(seen, found["best"], one["name"])}
        )
        for one in members
    }
    if not found["passed"]:
        found["conflict"] = _conflict(seen)
    return found


def _joined(answers: dict[str, dict]) -> dict:
    """Several members' answers to one sample, as one answer: the worst of each."""
    predicates, rooms = [], []
    for member, answer in answers.items():
        for one in answer.get("predicates", ()):
            predicates.append({**one, "id": f"{member}:{one.get('id')}"})
        rooms.append((answer.get("headroom"), f"{member}:{answer.get('tightest')}"))
    measured = [(room, who) for room, who in rooms if room is not None]
    tightest = min(measured) if measured and len(measured) == len(rooms) else None
    return {
        "passed": all(a.get("passed") for a in answers.values()),
        "score": min(float(a.get("score", 0.0)) for a in answers.values()),
        "predicates": predicates,
        "failed": [
            f"{member}:{one}"
            for member, answer in answers.items()
            for one in answer.get("failed", ())
        ],
        "headroom": tightest[0] if tightest else None,
        "tightest": tightest[1] if tightest else None,
    }


def _answer_at(seen: list[dict], params: dict, member: str) -> dict:
    for sample in seen:
        if sample["params"] == params:
            return sample["answers"][member]
    return {}  # pragma: no cover - the best is always one of the samples seen


def _conflict(seen: list[dict]) -> dict | None:
    """The two predicates, on different members, that no sample satisfied together."""
    held: dict[str, set[int]] = {}
    margins: dict[str, dict[int, float]] = {}
    for index, sample in enumerate(seen):
        for member, answer in sample["answers"].items():
            for one in answer.get("predicates", ()):
                key = f"{member}:{one.get('id')}"
                held.setdefault(key, set())
                margins.setdefault(key, {})[index] = float(
                    one.get("margin", 0.0) or 0.0
                )
                if one.get("passed"):
                    held[key].add(index)
    reached = sorted(key for key, where in held.items() if where)
    pairs = [
        (min(len(held[a]), len(held[b])), a, b)
        for i, a in enumerate(reached)
        for b in reached[i + 1 :]
        if a.split(":")[0] != b.split(":")[0] and not held[a] & held[b]
    ]
    never = sorted(key for key, where in held.items() if not where)
    if not pairs:
        # No two held apart: what failed is a predicate nothing ever satisfied, and
        # naming it is the whole of the answer.
        return {"between": None, "closest_to": {}, "never": never} if never else None
    _, one, other = max(pairs)

    def nearest(keep: str, reach: str) -> dict:
        index = max(held[keep], key=lambda i: margins[reach].get(i, 0.0))
        return seen[index]["params"]

    return {
        "between": [one, other],
        "closest_to": {one: nearest(one, other), other: nearest(other, one)},
        "never": never,
    }


def _ranked(sample: dict) -> tuple[float, float]:
    """Score first; among samples that pass, the one with more room wins (§PW104)."""
    room = sample.get("headroom")
    passing = sample["passed"] and room is not None
    return (sample["score"], float(room) if passing else float("-inf"))


def _close_around(best, windows, steps, per_axis) -> dict:
    """Narrow each range to the neighbourhood of the best value found so far.

    The window shrinks by a fixed factor rather than to the distance between grid
    points: a best value sitting dead centre of its range is the common case, and a
    neighbourhood measured from it would be the range it started as.
    """
    if best is None:
        return {}
    narrowed = {}
    moved = False
    for name, (low, high) in windows.items():
        reach = (high - low) / (2.0 * max(1, per_axis - 1))
        step = steps[name] and float(steps[name])
        if step and reach <= step:
            narrowed[name] = (low, high)  # already as fine as the step allows
            continue
        centre = float(best["params"][name])
        narrowed[name] = (max(low, centre - reach), min(high, centre + reach))
        if narrowed[name] != (low, high):
            moved = True
    return narrowed if moved else {}


# -- the evaluator that actually renders ---------------------------------------------


def renderer(
    spec: Spec,
    *,
    out: str | Path,
    root: str | Path = ".",
    rung: str | None = None,
    fixed: dict | None = None,
    bake: Callable | None = None,
) -> Callable[[dict], dict]:
    """An evaluator that renders each sample and checks the spec against it.

    The rung is the lowest one that carries the spec's predicates, which is what makes
    the search affordable: a material question is answered on a sphere in three seconds.
    """
    from . import render as R

    at = rung or _rung_for(spec, root)
    draw = bake or R.bake
    turnable(draw, ranges(spec), also=fixed or {})

    class Quiet:
        """A search reports its own progress; each sample does not need to.

        Every method is empty on purpose: this stands in for the job's report, and a
        sample inside a sweep has nobody to report to.
        """

        def stage(self, stage, *, progress=None, note=None):
            pass

        def progress(self, value, *, note=None):
            pass

        def note(self, text):
            pass

    def evaluate(values: dict) -> dict:
        drawn = draw(
            Quiet(),
            out=str(out),
            rung=at,
            root=str(root),
            inline=False,
            **{**(fixed or {}), **values},
        )
        found = accept.check(spec, Path(root) / out, rung=at, root=root)
        # The key is what lets a contact sheet be assembled afterwards, since the cache
        # is already holding every sample's picture under it.
        found["render"] = {
            "cache_key": drawn.get("cache_key"),
            "cached": drawn.get("cached"),
            "artefact": drawn.get("artefact"),
        }
        return found

    return evaluate


def in_parallel(
    spec: Spec,
    *,
    out: str | Path,
    root: str | Path = ".",
    rung: str | None = None,
    fixed: dict | None = None,
    store: Any = None,
) -> Callable[[list[dict]], list[dict]]:
    """An evaluator that renders a whole pass at once, one job per sample.

    §PW45. The job system was built so that four parameter samples are four handles
    rather than four waits, and the search was calling its evaluator once per sample and
    waiting for each render before proposing the next.

    The reason it was not built this way to begin with is real and still holds: the
    render path drives Blender through the bpy module in process, and bpy is a
    singleton that cannot render two scenes at once in one interpreter. So each sample
    here pays an interpreter start that `renderer` avoids — a loss on cheap rungs and a
    win on dear ones, and `crossing_point` is how a project finds out which is which.

    Each sample writes its own picture, because they are in flight together and one
    path would be one file four processes were writing. The checking happens back here,
    in this process, since it costs no renderer.
    """
    from .jobs import JobStore

    at = rung or _rung_for(spec, root)
    turnable(_bake_signature(), ranges(spec), also=fixed or {})
    jobs = store or JobStore.for_project(root)
    where = Path(out)

    def evaluate_all(samples: list[dict]) -> list[dict]:
        if not samples:
            return []
        started: list[tuple[str, Path]] = []
        found: list[dict] = []
        # Bounded by what the project allows at once, and collected in batches of that
        # size: `start` refuses past the ceiling rather than queueing, which is the
        # right behaviour to obey rather than to work around.
        for batch in _chunked(list(enumerate(samples)), jobs.max_parallel):
            for index, values in batch:
                picture = where.with_name(f"{where.stem}-{index:03d}{where.suffix}")
                handle = jobs.start(
                    "polyweave.render:bake",
                    kind="bake",
                    label=f"sample {index}",
                    args={
                        "out": str(picture),
                        "rung": at,
                        "inline": False,
                        "root": str(root),
                        **(fixed or {}),
                        **values,
                    },
                )
                started.append((handle["job"], picture))
            for job, picture in started[len(found) :]:
                done = jobs.result(job, wait=True)
                if done.get("status") != "done":
                    # Raised rather than scored: a sample whose render failed has no
                    # picture, and checking the absent file would report the failure as
                    # a missing path instead of as whatever actually went wrong.
                    raise PolyweaveError.from_dict(done.get("error") or {})
                drawn = done.get("result") or {}
                # The bake ran in a worker, where no run is open, so it is counted here.
                loop.bake_seen(drawn)
                checked = accept.check(spec, Path(root) / picture, rung=at, root=root)
                checked["render"] = {
                    "cache_key": drawn.get("cache_key"),
                    "cached": drawn.get("cached"),
                    "artefact": drawn.get("artefact"),
                }
                found.append(checked)
        return found

    return evaluate_all


#: What a worker costs before it renders anything: spawning an interpreter and importing
#: bpy. Measured at 0.85s on Blender 5.2.1 — a sphere render that takes 0.24s in process
#: took 1.09s round-tripped through a job.
WORKER_START_S = 0.85


def crossing_point(*, lanes: int = 4, start_s: float = WORKER_START_S) -> float:
    """How long one render must take before running `lanes` of them at once pays.

    §PW45's open question, answered with arithmetic over a measurement rather than with
    a rule of thumb. Serial costs `lanes * one`; parallel costs `one + start_s`, since
    the lanes overlap and each pays its own interpreter start only once. They meet at
    `start_s / (lanes - 1)`.

    Measured against the ladder on Blender 5.2.1, four samples at a time:

    | rung    | one render | serial | parallel |         |
    |---------|-----------:|-------:|---------:|---------|
    | sphere  |      0.24s |  0.95s |    1.09s | a loss  |
    | preview |      0.22s |  0.86s |    1.07s | a loss  |
    | final   |     11.44s | 45.78s |   12.30s | 3.7x    |

    So **parallel is for the dear rung and not the cheap ones**, which is what the cheap
    rung is for. The parallel column is the optimistic bound — four Blenders contend for
    the same cores — so the crossing sits somewhat above what this returns, and a rung
    near it should be measured rather than assumed.
    """
    return float(start_s) / max(1, int(lanes) - 1)


@operation("search.worth_parallel")
def worth_parallel(
    seconds_per_render: Annotated[
        float, Param("what one render costs at this rung", lo=0.0, unit="s")
    ],
    *,
    lanes: Annotated[int, Param("how many run at once", lo=1)] = 4,
    start_s: Annotated[
        float, Param("what a worker costs before it renders", lo=0.0, unit="s")
    ] = WORKER_START_S,
) -> bool:
    """Whether four handles beat four waits, for a render that costs this much."""
    return float(seconds_per_render) > crossing_point(lanes=lanes, start_s=start_s)


def _rung_for(spec: Spec, root: str | Path) -> str:
    """The cheapest rung this project enables that carries the spec's predicates.

    Asked of the project rather than of the ladder alone (§PW117): a project that does
    not render spheres searches a material on its preview instead of being refused.
    """
    from . import render as R

    asked = [p.measure for p in spec.predicates]
    return R.plan(asking=asked or None, floor=spec.rung, root=root)["rung"]


def _bake_signature() -> Callable:
    """The renderer a job will run, for checking the axes against before spawning."""
    from . import render as R

    return R.bake


def _chunked(items: list, size: int) -> Iterator[list]:
    size = max(1, int(size))
    for start in range(0, len(items), size):
        yield items[start : start + size]


@operation("search.sweep", kind="search")
def sweep(
    spec: Annotated[str, Param("the acceptance spec, as a path under the project")],
    *,
    out: Annotated[str, Param("where each sample's picture is written")],
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
    budget: Annotated[int, Param("how many renders it may spend", lo=1)] = BUDGET,
    points: Annotated[int, Param("points per axis in a pass", lo=2)] = POINTS,
    rung: Annotated[str, Param("the rung, or the spec's own where empty")] = "",
    fixed: Annotated[
        dict, Param("render arguments held still, such as the model")
    ] = None,
    trace: Annotated[
        str, Param("where to write what it rejected, as <name>.json and .png")
    ] = "",
) -> dict:
    """Search a spec's permitted parameters by actually rendering, and return the best.

    `trace` is where to write down what it rejected. Worth passing: a search returning
    only its winner is one nobody can overrule. `spec` may also be a `Spec` in memory.
    """
    if not isinstance(spec, Spec):
        spec = accept.read(spec, root)
    rung = rung or None
    trace = trace or None
    found = search(
        spec,
        renderer(spec, out=out, root=root, rung=rung, fixed=fixed),
        budget=budget,
        points=points,
    )
    if trace is not None:
        from . import trace as written

        found["trace_written"] = written.write(found, out=trace, spec=spec, root=root)
    return found


def best_of(results: Sequence[dict]) -> dict | None:  # pragma: no cover - a convenience
    return max(results, key=lambda r: r.get("score", 0.0), default=None)


def as_params(found: dict) -> dict[str, Any]:
    """The winning values, ready to be passed straight back into a render."""
    return dict(found["best"])
