"""A performance budget the gate holds, and a baseline a commit regresses from (§PW365).

Cottony keeps tools/perf/ started by hand: each script measures, prints, and leaves the
comparison with last week to whoever remembers last week's number. A project declares
budgets per scene instead, in polyweave.toml:

    [perf.title]
    scene = "res://title.tscn"
    frames = 300          # frames measured after a short settling
    p95_ms = 16.6         # frame time at the 95th and 99th percentile, never a mean
    p99_ms = 33.3
    load_ms = 1500        # loading the scene and putting it in place
    memory_mb = 512       # the peak of static memory
    nodes = 4000          # the peak node count

`engine.perf` runs each scene with polyweave's own measuring script, through the route
that draws real pixels here, vsync off: a frame time with no GPU behind it measures
nothing, so a machine with no such route is skipped and said, never passed. The first
run on a machine and device writes the baseline, under the work folder; each run after
answers every budget held or exceeded, and how far each measure moved from the baseline.
A measure holds on the machine that took it, which the answer names with its device; it
catches a regression there and never certifies a player's hardware.
"""

from __future__ import annotations

import json
import platform
import re
from pathlib import Path
from typing import Annotated

from .config import load
from .describe import Param, operation
from .errors import PolyweaveError
from .files import write_atomic

#: What the measuring script prints, and what a budget may bound.
MEASURES = ("load_ms", "p95_ms", "p99_ms", "memory_mb", "nodes")
LINE = re.compile(r"^PERF (?P<pairs>load_ms=.*)$", re.MULTILINE)
SCRIPT = Path(__file__).parent / "godot" / "perf_run.gd"
#: The device the engine says it draws with, as Godot prints it at start-up.
DEVICE = re.compile(r"Using Device #\d+: ([^\r\n]+)")


def _measured(found: str) -> dict:
    return {k: float(v) for k, v in re.findall(r"(\w+)=(-?[\d.]+)", found)}


def held(measured: dict, budget: dict, baseline: dict | None) -> dict:
    """Each budget held or exceeded, and each measure's move from its baseline."""
    budgets = {
        name: {"value": measured.get(name), "most": float(budget[name]),
               "held": measured.get(name) is not None
               and measured[name] <= float(budget[name])}
        for name in MEASURES if name in budget
    }
    moved = {}
    for name in MEASURES:
        was = (baseline or {}).get(name)
        if was and measured.get(name) is not None:
            moved[name] = {"was": was, "now": measured[name],
                           "change": round((measured[name] - was) / was, 4)}
    return {"budgets": budgets, "moved": moved,
            "held": all(one["held"] for one in budgets.values())}


@operation("engine.perf", kind="capture")
def perf(
    scenes: Annotated[
        list, Param("the [perf.<name>] budgets to run; every one declared where unset")
    ] = (),
    rebase: Annotated[
        bool, Param("write this run as the baseline for this machine and device")
    ] = False,
    root: Annotated[str, Param("the Godot project whose scenes these are")] = ".",
) -> dict:
    """Each declared scene measured and held to its budget and this machine's baseline.

    Runs every `[perf.<name>]` scene with polyweave's measuring script through the
    route that draws real pixels, vsync off, and answers per scene its load time, frame
    time at the 95th and 99th percentile, peak static memory and peak node count, each
    budget held or exceeded, and how far each moved from the baseline this machine and
    device took first (or that `rebase` writes). With no route that draws, it is
    skipped and said, never passed (§PW365).
    """
    from . import offscreen

    config = load(root)
    here = config.root
    declared = config.table("perf")
    chosen = {name: one for name, one in declared.items()
              if isinstance(one, dict) and (not scenes or name in scenes)}
    if not chosen:
        raise PolyweaveError(
            "engine.no-budget",
            "polyweave.toml declares no [perf.<name>] budget to run",
            'declare [perf.title] scene = "res://title.tscn" and the most it may cost',
        )
    try:
        route = offscreen.route_for(here)
    except PolyweaveError as refused:
        return {"ok": None, "skipped": refused.message, "scenes": {},
                "says": "skipped: nothing draws real pixels here, and a frame time "
                "with no GPU behind it measures nothing"}
    kept = config.path("paths.work") / "perf" / "baseline.json"
    baselines = json.loads(kept.read_text(encoding="utf-8")) if kept.is_file() else {}
    answered, device = {}, ""
    for name, budget in chosen.items():
        found = offscreen.capture(
            SCRIPT, expect=r"^PERF (load_ms=.*|failed.*)$", root=here,
            fixed_fps=0, route=route.name,
            frames=int(budget.get("frames", 300)) * 4 + 600,
            args=("--", f"scene={budget['scene']}",
                  f"frames={budget.get('frames', 300)}"),
        )
        log = Path(str(found.get("log") or ""))
        text = (log.read_text(encoding="utf-8", errors="replace")
                if log.is_file() else "")
        said = DEVICE.search(text)
        device = device or (said[1] if said else "")
        line = LINE.search(text)
        if line is None:
            answered[name] = {"held": False, "scene": budget["scene"],
                              "why": found.get("why") or "the scene printed no measure"}
            continue
        measured = _measured(line["pairs"])
        key = f"{platform.node()}|{device}|{name}"
        result = held(measured, budget, baselines.get(key))
        if rebase or key not in baselines:
            baselines[key] = measured
            result["baseline"] = "written"
        answered[name] = {"scene": budget["scene"], "measured": measured, **result}
    write_atomic(kept, json.dumps(baselines, indent=1) + "\n")
    broke = [name for name, one in answered.items() if not one["held"]]
    return {
        "ok": not broke,
        "machine": platform.node(),
        "device": device,
        "route": route.name,
        "scenes": answered,
        "says": f"{len(answered)} scene(s), "
        + ("every budget held" if not broke else f"over budget: {', '.join(broke)}"),
    }
