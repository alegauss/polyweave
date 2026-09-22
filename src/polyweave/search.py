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

import itertools
import math
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from . import accept
from .accept import Spec
from .errors import PolyweaveError

#: How many points each axis gets in a pass, before the window closes around the best.
POINTS = 3

#: How many renders a search may spend unless the caller says otherwise. A number, not a
#: wall-clock: the budget is the thing being managed, and it has to be legible.
BUDGET = 24


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
    evaluate: Callable[[dict], dict],
    *,
    budget: int = BUDGET,
    points: int = POINTS,
    passes: int = 3,
    rebuilding: Sequence[str] = (),
) -> dict:
    """Search the spec's permitted parameters for values that satisfy its predicates.

    `evaluate` takes one set of parameter values and returns what `accept.check`
    returns. Everything about rendering is on the other side of it, so this is testable
    without a renderer and a parallel evaluator is a drop-in.

    A search that has already found its answer stops: there is no reason to pay for the
    renders after a spec passes with nothing left to gain.
    """
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
    spent = 0
    stopped = "the budget ran out"

    for _ in range(max(1, passes)):
        per_axis = _points_per_axis(len(names), budget - spent, points)
        axes = [
            grid(*windows[n], per_axis, steps[n] and float(steps[n])) for n in names
        ]
        for combination in itertools.product(*axes):
            if spent >= budget:
                break
            key = tuple(round(v, 10) for v in combination)
            if key in seen:
                continue
            values = dict(zip(names, combination, strict=True))
            found = evaluate(values)
            spent += 1
            sample = {
                "params": values,
                "score": float(found.get("score", 0.0)),
                "passed": bool(found.get("passed", False)),
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
            if best is None or sample["score"] > best["score"]:
                best = sample

        if best is not None and best["passed"] and best["score"] >= 1.0:
            stopped = "the spec passed with nothing left to gain"
            break
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
        "trace": trace,
    }


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

    at = rung or spec.needs_rung()
    draw = bake or R.bake

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


def sweep(
    spec: Spec,
    *,
    out: str | Path,
    root: str | Path = ".",
    budget: int = BUDGET,
    points: int = POINTS,
    rung: str | None = None,
    fixed: dict | None = None,
    trace: str | Path | None = None,
) -> dict:
    """Search by actually rendering: the whole loop, from a spec to the best values.

    `trace` is where to write down what it rejected. Worth passing: a search returning
    only its winner is one nobody can overrule.
    """
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
