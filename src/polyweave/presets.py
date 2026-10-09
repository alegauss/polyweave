"""Graphics presets found by search, the best look that fits each budget (§PW367).

Cottony's render rig shows the cost: every constant of it was found by hand at two
minutes a sample, and a graphics preset is the same problem in another place.
`engine.preset_search` runs a scene once per combination of graphics settings, in the
graphics kit's terms (render scale and upscaler, MSAA, the costly effects, the shadow
atlas), timing its frames and keeping its last one. The full-quality combination is the
reference. For each preset's frame budget at p95 the answer is the combination that fits
and loses least against the reference, by measure.same, with its frame time, its loss
and its picture; and each feature's cost, the reference's frame time less the same run
with that feature dropped, so "effects cost 5.9 ms here" arrives without profiling.

How much loss is acceptable is taste, so every preset that loses any goes on a sheet
for a person (verdict.sheet), and the agent never accepts one. A search holds for the
machine and device it ran on, as engine.perf says of every measure; with no route that
draws real pixels it is skipped and said, never passed.
"""

from __future__ import annotations

import itertools
import json
import re
from pathlib import Path
from typing import Annotated

from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

SCRIPT = Path(__file__).parent / "godot" / "preset_run.gd"
LINE = re.compile(r"^PRESET p95_ms=(?P<p95>[\d.]+) p99_ms=(?P<p99>[\d.]+)",
                  re.MULTILINE)

#: The settings searched where a call names none: full quality first, then each cheaper.
GRID = {
    "scale": [1.0, 0.75, 0.5],
    "scaler": ["bilinear", "fsr"],
    "msaa": [4, 0],
    "effects": [True, False],
    "shadows": [4096, 2048],
}


def combinations(grid: dict) -> list[dict]:
    """Every combination of the grid, the first value of each being full quality; an
    upscaler is only tried below full scale, where it does anything."""
    keys = list(grid)
    found = []
    for values in itertools.product(*(grid[k] for k in keys)):
        one = dict(zip(keys, values, strict=True))
        if one.get("scale", 1.0) >= 1.0 and one.get("scaler", "bilinear") != grid.get(
                "scaler", ["bilinear"])[0]:
            continue
        found.append(one)
    return found


def choose(ran: list[dict], budgets: dict) -> tuple[dict, list[dict]]:
    """Per preset, the run fitting its p95 budget that loses least (the faster of two
    that lose alike), and each chosen run that loses any, for a person to judge."""
    chosen, lossy = {}, []
    for name, most in budgets.items():
        fits = [one for one in ran if one["p95_ms"] <= float(most)]
        best = min(fits, key=lambda one: (one["loss"], one["p95_ms"]), default=None)
        if best is None:
            chosen[name] = {"budget_ms": float(most), "fits": False,
                            "cheapest_ms": min(one["p95_ms"] for one in ran)}
            continue
        chosen[name] = {"budget_ms": float(most), "fits": True, **best}
        if best["loss"] > 0:
            lossy.append({"name": name, **best})
    return chosen, lossy


def _label(settings: dict) -> str:
    return "-".join(f"{k}{v}" for k, v in settings.items()).replace(".", "_")


@operation("engine.preset_search", kind="capture")
def preset_search(
    scene: Annotated[str, Param("the scene searched, as res://…")],
    *,
    budgets: Annotated[
        dict, Param("each preset's frame budget at p95, in ms: {low: 33.3, high: 8.3}")
    ],
    grid: Annotated[
        dict, Param("the values each setting may take, full quality first")
    ] = None,
    frames: Annotated[int, Param("frames timed in each run", lo=10)] = 120,
    root: Annotated[str, Param("the Godot project the scene is in")] = ".",
) -> dict:
    """For each preset, the settings that fit its frame budget and lose least (§PW367).

    Runs `scene` once per combination of `grid` (render scale, upscaler, MSAA, effects,
    shadows; a default where unset) through the route that draws real pixels, timing
    frames and keeping the last. Per preset of `budgets`, the combination fitting its
    p95 that loses least against the full-quality frame by measure.same; per feature,
    what dropping it saves; and a sheet for a person of every preset that loses any,
    since how much loss is acceptable is taste the agent never judges.
    """
    from . import measure, offscreen, verdict

    config = load(root)
    here = config.root
    if not budgets:
        raise PolyweaveError(
            "engine.no-budget",
            "no preset's frame budget was given to search for",
            "pass budgets, each preset's p95 in ms: {low: 33.3, high: 8.3}",
        )
    try:
        route = offscreen.route_for(here)
    except PolyweaveError as refused:
        return {"ok": None, "skipped": refused.message, "presets": {},
                "says": "skipped: a frame time with no GPU behind it measures nothing"}
    tried = combinations(grid or GRID)
    out = config.path("paths.work") / "presets"
    out.mkdir(parents=True, exist_ok=True)
    runs = []
    for settings in tried:
        shot = out / f"{_label(settings)}.png"
        found = offscreen.capture(
            SCRIPT, expect=LINE, root=here, fixed_fps=0, route=route.name,
            frames=frames * 4 + 600,
            args=("--", f"scene={scene}", f"frames={frames}",
                  f"shot={shot.as_posix()}", f"settings={json.dumps(settings)}"))
        log = Path(str(found.get("log") or ""))
        text = (log.read_text(encoding="utf-8", errors="replace")
                if log.is_file() else "")
        line = LINE.search(text)
        if line is None or not shot.is_file():
            runs.append({"settings": settings, "failed": found.get("why") or "no line"})
            continue
        runs.append({"settings": settings, "p95_ms": float(line["p95"]),
                     "p99_ms": float(line["p99"]), "shot": str(shot)})
    ran = [one for one in runs if "p95_ms" in one]
    if not ran:
        raise PolyweaveError(
            "engine.no-signal",
            f"no combination of {scene} ran to its measure",
            "run the scene once with engine.perf, which says why",
            detail=runs[0].get("failed") if runs else None,
        )
    reference = ran[0]
    for one in ran:
        one["loss"] = round(float(measure.same(
            one["shot"], reference["shot"], root=str(here))["distance"]), 4)
    costs = {}
    searched = grid or GRID
    for feature, values in searched.items():
        if feature not in reference["settings"] or len(values) < 2:
            continue
        # the feature dropped to the cheapest value it was searched at, all else full
        twin = {**reference["settings"], feature: values[-1]}
        match = next((one for one in ran if one["settings"] == twin), None)
        if match is not None:
            costs[feature] = round(reference["p95_ms"] - match["p95_ms"], 3)
    chosen, members = choose(ran, budgets)
    members = [{"name": one["name"], "old": _relative(reference["shot"], here),
                "new": _relative(one["shot"], here)} for one in members]
    sheet = None
    if members:
        sheet = verdict.sheet(members, out=_relative(out / "sheet.png", here),
                              root=str(here)).get("out")
    dearest = max(costs, key=costs.get) if costs else None
    return {
        "ok": all(one["fits"] for one in chosen.values()),
        "route": route.name,
        "reference": reference,
        "presets": chosen,
        "costs_ms": costs,
        "dearest": dearest,
        "runs": len(runs),
        "sheet": sheet,
        "says": (f"{len(ran)} combination(s) of {scene}"
                 + (f"; {dearest} costs {costs[dearest]} ms here" if dearest else "")
                 + ("; a person judges the presets that lose quality on the sheet"
                    if members else "")),
    }


def _relative(path: str | Path, here: Path) -> str:
    return Path(path).resolve().relative_to(here.resolve()).as_posix()
