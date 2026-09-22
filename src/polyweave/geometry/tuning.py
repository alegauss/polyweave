"""A shape's own numbers, reachable from the search that tunes everything else.

The evidence is §PW32: the rig's parameters live in a dataclass and the geometry's live
inside Python modules, so the search in Block C can reach the lighting and never the
shape it is lighting. **That split is arbitrary.** A bevel radius, a wall thickness,
a crown height and a pitch are all numbers somebody tuned by rendering and looking,
exactly like the exposure was.

Now that a shape is a declaration with named parameters at its head, those numbers are
addressable, and a search can be handed a mixed space of shape and rig. Two things have
to hold for that to be safe, and both are here:

**A geometry parameter needs a declared range like any other.** A wall thickness that
goes negative does not produce a poor render, it produces an invalid mesh — which is
Block A's post-condition check earning its place, and why a build that fails is scored
as a failed sample rather than being allowed to end the search.

**The search has to know which parameters force a rebuild**, or it pays the rebuild cost
on every sample. `geometry.rebuilds` already answers that per parameter, and the search
takes it as `rebuilding`; the ordering does the rest.
"""

from __future__ import annotations

from typing import Any

from .. import search as S
from ..accept import Spec
from ..errors import PolyweaveError
from . import expand, rebuilds


def addressable(document: dict, names: Any) -> dict[str, list[str]]:
    """Which of these names the document actually has, and what each one rebuilds.

    A name the document does not declare is **refused**, not ignored: a search over a
    misspelled geometry parameter would otherwise run its whole budget turning a knob
    attached to nothing and report the result as a finding.
    """
    declared = set(document["params"])
    unknown = sorted(name for name in names if name not in declared)
    if unknown:
        raise PolyweaveError(
            "geom.unknown-name",
            f"the search names {', '.join(unknown)}, which this shape does not declare",
            f"name a parameter the document has: {', '.join(sorted(declared))}",
        )
    return {name: rebuilds(document, name) for name in sorted(names)}


def split(document: dict, spec: Spec) -> dict:
    """The spec's searchable parameters, sorted into the shape's and everything else.

    A name is the shape's if the document declares it. Nothing else has to be told
    which is which, which is the point: one space, two costs.
    """
    permitted = S.ranges(spec)
    declared = set(document["params"])
    shape = sorted(name for name in permitted if name in declared)
    rig = sorted(name for name in permitted if name not in declared)
    return {
        "shape": shape,
        "rig": rig,
        "rebuilds": addressable(document, shape),
        "order": S.slowest_first(sorted(permitted), shape),
    }


def evaluator(
    document: dict,
    build: Any,
    judge: Any,
    *,
    shape: Any = (),
) -> Any:
    """One evaluator over a mixed space, rebuilding only when the shape changed.

    `build` takes the resolved document and returns a mesh; `judge` takes that mesh and
    the rig values and returns what `accept.check` returns. Keeping the two apart is
    what lets this count its own rebuilds honestly.

    A build that refuses — a negative wall thickness, an emptied boolean — is **a
    failed sample**, scored zero and carried in the answer. A search that died on one
    invalid combination would report nothing about the valid ones already paid for.
    """
    named = sorted(shape)
    state: dict[str, Any] = {"key": None, "mesh": None, "rebuilds": 0, "refused": []}

    def evaluate(values: dict) -> dict:
        key = tuple(round(float(values[name]), 10) for name in named)
        if state["key"] != key or state["mesh"] is None:
            state["key"] = key
            state["rebuilds"] += 1
            try:
                state["mesh"] = build(expand(document, **{n: values[n] for n in named}))
            except PolyweaveError as refused:
                state["mesh"] = None
                state["refused"].append(
                    {"params": dict(values), "why": refused.message}
                )
                return {
                    "passed": False,
                    "score": 0.0,
                    "predicates": [],
                    "failed": [refused.code],
                    "why": refused.message,
                }
        if state["mesh"] is None:
            return {"passed": False, "score": 0.0, "predicates": [], "failed": []}
        return judge(state["mesh"], values)

    evaluate.state = state  # type: ignore[attr-defined]
    return evaluate


def tune(
    document: dict,
    spec: Spec,
    build: Any,
    judge: Any,
    **how: Any,
) -> dict:
    """Search a shape and its rig together, rebuilding as rarely as the order allows."""
    sorted_out = split(document, spec)
    evaluate = evaluator(document, build, judge, shape=sorted_out["shape"])
    found = S.search(spec, evaluate, rebuilding=sorted_out["shape"], **how)
    state = evaluate.state
    return {
        **found,
        "shape": sorted_out["shape"],
        "rig": sorted_out["rig"],
        # What the ordering actually bought, counted rather than claimed: the builds
        # paid for, against one per sample had nothing been ordered.
        "built": state["rebuilds"],
        "naive_builds": found["spent"],
        "refused": state["refused"],
    }
