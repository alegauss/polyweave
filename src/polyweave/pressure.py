"""How hard each second of a wave timeline is, from events the game writes (§PW330).

Starship's owner found the waves unbalanced, and nothing said how hard a second of a
phase was: a total or a peak cannot show the second a wave goes empty or floods. The
game alone knows its wave format, so it writes the timeline as weighted events, each
`{second, kind, weight, until}`, where `until` is the end of the wave it belongs to.
Per second this answers:

- `entering`: the threat that spawns in that second;
- `alive_fast` and `alive_slow`: the threat alive in the two bounding cases, every
  enemy killed the moment it lands (after `warp` seconds of warp-in) and nothing
  killed until its wave's end;
- the gaps with nothing to shoot, read off the fast case, where a player who kills
  everything as it lands finds the screen empty: the longest, and every one past
  `window` (a multiplier's timeout, say).

A `compare` timeline is laid beside it, so a change is read against the one before.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Annotated, Any

from .describe import Param, operation
from .errors import PolyweaveError

_EVENTS = Param("the events, each {second, kind, weight, until}")
_FILE = Param("or a JSON file of them under the project, as the game wrote it")


def _read(events: Any, root: Path) -> tuple[list[dict], Path | None]:
    """The events as a list, and the file they came from where they came from one."""
    source = None
    if isinstance(events, str | Path):
        source = Path(events) if Path(events).is_absolute() else root / events
        if not source.is_file():
            raise PolyweaveError(
                "spec.no-targets",
                f"there is no events file at {source}",
                "write the timeline the game knows as a JSON list of {second, kind, "
                "weight, until}, or pass the list",
                given=str(events),
            )
        events = json.loads(source.read_text(encoding="utf-8"))
        if isinstance(events, dict):
            events = events.get("events")
    if not isinstance(events, list) or not events:
        raise PolyweaveError(
            "spec.no-targets",
            "no events to measure the timeline's pressure from",
            "pass events, each {second, kind, weight, until}",
        )
    found = []
    for index, one in enumerate(events):
        try:
            second, weight = float(one["second"]), float(one.get("weight", 1.0))
            until = float(one.get("until", second))
        except (KeyError, TypeError, ValueError):
            raise PolyweaveError(
                "spec.no-targets",
                f"event {index + 1} is {one!r}, and an event is "
                "{second, kind, weight, until}",
                "give each event its second, and the end of its wave as until",
                given=str(one),
            ) from None
        if second < 0 or until < second or weight < 0:
            raise PolyweaveError(
                "spec.no-targets",
                f"event {index + 1} spawns at {second:g} and its wave ends at "
                f"{until:g} with weight {weight:g}",
                "a wave ends at or after its spawn, and a weight is not negative",
                given=str(one),
            )
        found.append({"second": second, "kind": str(one.get("kind", "")),
                      "weight": weight, "until": until})
    return found, source


def _curves(events: list[dict], warp: float, window: float) -> dict:
    """Per-second threat in both bounding cases, and the gaps of the fast one."""
    end = max(max(e["until"], e["second"] + warp) for e in events)
    seconds = max(1, math.ceil(end))
    entering = [0.0] * seconds
    fast = [0.0] * seconds
    slow = [0.0] * seconds
    for e in events:
        entering[min(int(e["second"]), seconds - 1)] += e["weight"]
        for curve, stop in ((fast, e["second"] + warp), (slow, e["until"])):
            for s in range(int(e["second"]), min(seconds, math.ceil(stop))):
                # Weighted by how much of that second it is alive for.
                share = min(stop, s + 1) - max(e["second"], s)
                if share > 0:
                    curve[s] += e["weight"] * share
    # The gaps: stretches no fast-case enemy is alive in, from the first spawn on.
    spans = sorted((e["second"], e["second"] + warp) for e in events)
    gaps, reach = [], spans[0][0]
    for start, stop in spans:
        if start > reach:
            gaps.append([round(reach, 3), round(start, 3)])
        reach = max(reach, stop)
    longest = max((b - a for a, b in gaps), default=0.0)
    past = [g for g in gaps if window and g[1] - g[0] > window]

    def tidy(curve):
        return [round(v, 4) for v in curve]

    return {
        "seconds": seconds,
        "entering": tidy(entering),
        "alive_fast": tidy(fast),
        "alive_slow": tidy(slow),
        "total": round(sum(e["weight"] for e in events), 4),
        "peak_slow": round(max(slow), 4),
        "longest_gap": round(longest, 3),
        "gaps": gaps,
        "past_window": past,
    }


@operation("measure.pressure")
def pressure(
    events: Annotated[list, _EVENTS] = None,
    *,
    file: Annotated[str, _FILE] = None,
    compare: Annotated[list, Param("an earlier timeline, laid beside this one")] = None,
    compare_file: Annotated[str, Param("or the earlier timeline's file")] = None,
    warp: Annotated[
        float, Param("seconds an enemy warps in before it can be shot", lo=0, unit="s")
    ] = 0.0,
    window: Annotated[
        float, Param("the gap past which a gap is named; 0 names none", lo=0, unit="s")
    ] = 0.0,
    out: Annotated[str, Param("a JSON file under the project to keep it in")] = None,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """A wave timeline's threat per second, in its two bounding cases, and its gaps.

    Each second answers the threat `entering`, `alive_fast` (every enemy killed as it
    lands, after `warp`) and `alive_slow` (nothing killed until its wave ends), with
    the `gaps` a fast player finds the screen empty in, the `longest_gap` and those
    `past_window`. `compare` adds the same of an earlier timeline beside it; `out`
    keeps the answer as a file with its record (§PW330).
    """
    here = Path(root).resolve()
    now, source = _read(file if events is None else events, here)
    answer = _curves(now, float(warp), float(window))
    answer.update(events=len(now), warp=float(warp), window=float(window))
    inputs = [source] if source else []
    if compare is not None or compare_file is not None:
        before, earlier = _read(compare_file if compare is None else compare, here)
        was = _curves(before, float(warp), float(window))
        answer["compare"] = was
        answer["change"] = {
            key: round(answer[key] - was[key], 4)
            for key in ("total", "peak_slow", "longest_gap")
        }
        inputs += [earlier] if earlier else []
    if out:
        from . import provenance

        kept = Path(out) if Path(out).is_absolute() else here / out
        kept.parent.mkdir(parents=True, exist_ok=True)
        kept.write_text(json.dumps(answer, indent=1) + "\n", encoding="utf-8",
                        newline="\n")
        record = provenance.build(
            "capture", kept, engine={"name": "measure.pressure"},
            inputs=[provenance.source("events", one, root=here) for one in inputs],
            params={"warp": float(warp), "window": float(window)},
            root=here,
        )
        provenance.write(record, here)
        answer["out"] = provenance.relative(kept, here)
    return answer
