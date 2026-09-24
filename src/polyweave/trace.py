"""What the search rejected, not only what it chose.

The evidence is §PW15: a search that returns only its winner is a search nobody can
overrule. The failure it hides is specific and likely — a spec satisfiable by a render a
person would reject, where every predicate passes and the picture is still wrong. If the
only output is a set of numbers, that outcome is indistinguishable from success.

So a search writes down what it did:

    write(found, spec=spec, out="docs/renders/mascot.trace", root=".")
    #  mascot.trace.json   every sample, its score against every predicate, its key
    #  mascot.trace.png    the best handful side by side

A person looks at the sheet, sees that the top-scoring render is not the one they would
have chosen, and now knows **the spec is wrong rather than the renderer**. That is the
loop this block exists for: the spec is the thing being debugged, and the search is the
fastest way yet found to discover it is incomplete.

The sheet is assembled from the cache, because the cache already holds every sample's
picture under its key. Without one there is nothing to lay out, and the trace says so
rather than quietly writing a sheet of the last render repeated.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

from . import cache as store
from . import compose
from .accept import Spec
from .config import load
from .describe import Param, operation
from .files import write_atomic

#: How many of the best samples go on the sheet. Enough to see a trend, few enough to
#: take in at a glance.
TOP = 6


def ranked(found: dict, top: int = TOP) -> list[dict]:
    """The best samples, best first."""
    return sorted(found.get("trace", []), key=lambda s: -s.get("score", 0.0))[:top]


def sheet(
    found: dict,
    out: str | Path,
    *,
    root: str | Path = ".",
    top: int = TOP,
    cell: int = 256,
) -> dict:
    """Lay the best handful of samples side by side, from what the cache kept.

    Best first and left to right, so the eye reads the ranking the search produced and
    can disagree with it.
    """
    work = load(root).path("paths.work")
    tiles, shown, missing = [], [], []
    for sample in ranked(found, top):
        key = (sample.get("render") or {}).get("cache_key")
        hit = store.look(key, work=work) if key else None
        if hit is None:
            missing.append(sample.get("params"))
            continue
        tiles.append(hit["artefact"])
        shown.append({"params": sample["params"], "score": sample["score"]})
    if not tiles:
        return {
            "sheet": None,
            "shown": [],
            "why": "no sample's picture is in the cache, so there is nothing to "
            "lay out",
        }
    made = compose.sheet(tiles, cell=cell, out=out)
    return {
        "sheet": str(made.path),
        "shown": shown,
        "missing": missing,
        "why": "" if not missing else f"{len(missing)} samples were not in the cache",
    }


def as_record(found: dict, spec: Spec | None = None, *, root: str | Path = ".") -> dict:
    """The trace as it is written down: the samples, and what produced them.

    The seed and the search's own configuration sit beside the samples, because a result
    nobody can reproduce is one nobody can check.
    """
    config = load(root)
    return {
        "asset": found.get("asset"),
        "searched": found.get("searched", []),
        "ranges": dict(spec.search) if spec else {},
        "rung": spec.needs_rung() if spec else None,
        "budget": found.get("budget"),
        "spent": found.get("spent"),
        "stopped": found.get("stopped"),
        "seed": int(config.get("render.seed")),
        "best": {
            "params": found.get("best"),
            "score": found.get("score"),
            "passed": found.get("passed"),
            "predicates": found.get("predicates", []),
            "failed": found.get("failed", []),
        },
        "samples": [
            {
                "params": s.get("params"),
                "score": s.get("score"),
                "passed": s.get("passed"),
                "predicates": s.get("predicates", []),
                "cache_key": (s.get("render") or {}).get("cache_key"),
            }
            for s in found.get("trace", [])
        ],
    }


def write(
    found: dict,
    *,
    out: str | Path,
    spec: Spec | None = None,
    root: str | Path = ".",
    top: int = TOP,
    cell: int = 256,
) -> dict:
    """Write the trace and its contact sheet, and say where both landed."""
    where = Path(root).resolve()
    base = Path(out)
    if not base.is_absolute():
        base = where / base
    record = as_record(found, spec, root=root)
    # Appended rather than substituted: `run.trace` is a name, not a suffix, and
    # `with_suffix` would turn it into `run.json`.
    written = base.with_name(base.name + ".json")
    write_atomic(written, json.dumps(record, indent=2, sort_keys=True) + "\n")
    laid_out = sheet(
        found, base.with_name(base.name + ".png"), root=root, top=top, cell=cell
    )
    return {"trace": str(written), **laid_out, "samples": len(record["samples"])}


@operation("trace.read")
def read(
    path: Annotated[str, Param("the trace's .json, as search.sweep wrote it")],
) -> dict[str, Any]:
    """Read a trace back, which is what makes a past search arguable."""
    return json.loads(Path(path).read_text(encoding="utf-8"))
