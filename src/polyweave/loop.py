"""What one asset cost to make, each way, so the claim can be falsified.

The evidence is §PW35: **every line in this backlog is a claim that something will be
faster or more certain, and not one of them is measured.** The risk is specific — the
work gets rearranged rather than reduced, and the plugin becomes a different way to
spend the same afternoon.

So the loop itself is instrumented, against a real asset made both ways. Five numbers,
from brief to accepted render:

- **wall-clock seconds**, which is the one the claim is about;
- **renders spent**, because a faster loop that renders ten times as much is not faster;
- **tool calls**, because a turn is what an agent pays;
- **credits**, because some of this is real money;
- **how many results a person rejected after the tool reported them as passing.**

That last one is the honest measure of assertiveness. **A tool that approves renders a
person then rejects has made things worse however fast it was**, and nothing else here
would show it.

**A baseline cannot be written after the fact.** Starting the old way for an asset the
plugin has already made is refused, because a baseline recorded once the answer is known
is not a baseline, it is a justification. Each run also carries the commit it was taken
at, so the order is checkable by somebody who was not there.
"""

from __future__ import annotations

import json
import subprocess
import time
import uuid
from pathlib import Path

from .config import load
from .errors import PolyweaveError
from .files import write_atomic

#: The two things being compared: the pipeline as it was, and the plugin.
WAYS = ("before", "after")


def _where(root: str | Path) -> Path:
    settings = load(root)
    return settings.path("paths.loop")


def read(root: str | Path = ".") -> list[dict]:
    """Every run recorded, oldest first."""
    where = _where(root)
    if not where.is_file():
        return []
    try:
        found = json.loads(where.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PolyweaveError(
            "loop.malformed",
            f"{where.name} is not readable as JSON",
            "fix the syntax the detail below points at",
            detail=str(exc),
        ) from exc
    return list(found.get("runs", []))


def _commit(root: str | Path) -> str:
    """The commit this run was taken at, so its place in the order is checkable."""
    try:
        done = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(Path(root).resolve()),
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):  # pragma: no cover - no git here
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def start(
    asset: str,
    way: str,
    *,
    root: str | Path = ".",
    brief: str = "",
    who: str = "",
) -> dict:
    """Begin recording one asset made one way.

    A baseline started after the plugin has already made this asset is **refused**: the
    whole value of a baseline is that nobody knew the answer when it was taken.
    """
    if way not in WAYS:
        raise PolyweaveError(
            "loop.unknown-way",
            f"{way!r} is neither of the two ways being compared",
            f"say one of {', '.join(WAYS)}",
        )
    if way == "before":
        already = [r for r in read(root) if r["asset"] == asset and r["way"] == "after"]
        if already:
            raise PolyweaveError(
                "loop.baseline-too-late",
                f"{asset} has already been made the new way {len(already)} time(s), "
                f"so a baseline taken now is not one",
                "record the baseline before porting the asset, or measure an asset "
                "that has not been ported; a baseline written once the answer is "
                "known is a justification",
            )
    return {
        "id": uuid.uuid4().hex[:12],
        "asset": str(asset),
        "way": way,
        "brief": str(brief),
        "who": str(who),
        "started": time.time(),
        "commit": _commit(root),
        "renders": 0,
        "calls": 0,
        "credits": 0,
        "seconds": 0.0,
        "verdicts": [],
    }


def spent(
    run: dict, *, renders: int = 0, calls: int = 0, credits: int = 0, seconds: float = 0
) -> dict:
    """Add to what this run has cost so far. Called as the work happens."""
    run["renders"] += int(renders)
    run["calls"] += int(calls)
    run["credits"] += int(credits)
    run["seconds"] += float(seconds)
    return run


def judged(
    run: dict, *, tool_passed: bool, person_accepted: bool, why: str = ""
) -> dict:
    """One result, as the tool called it and as a person called it.

    Both, always. A tool's own verdict is worth nothing on its own here — the number
    this line is really after is the gap between the two.
    """
    run["verdicts"].append(
        {
            "tool_passed": bool(tool_passed),
            "person_accepted": bool(person_accepted),
            "why": str(why),
            "at": time.time(),
        }
    )
    return run


def overruled(run: dict) -> int:
    """Results the tool passed and a person rejected. The measure of assertiveness."""
    return sum(
        1
        for one in run["verdicts"]
        if one["tool_passed"] and not one["person_accepted"]
    )


def finish(run: dict, *, root: str | Path = ".", accepted: bool | None = None) -> dict:
    """Close the run and append it to the ledger, which is append-only."""
    if not run["verdicts"] and accepted is None:
        raise PolyweaveError(
            "loop.unfinished",
            f"{run['asset']} ({run['way']}) was never judged, so it says nothing",
            "judge it before finishing it; an asset nobody accepted or rejected did "
            "not finish being made",
        )
    done = {
        **run,
        "finished": time.time(),
        "seconds": round(run["seconds"] or (time.time() - run["started"]), 3),
        "accepted": bool(
            accepted
            if accepted is not None
            else (run["verdicts"] and run["verdicts"][-1]["person_accepted"])
        ),
        "overruled": overruled(run),
        "results": len(run["verdicts"]),
    }
    where = _where(root)
    write_atomic(
        where,
        json.dumps({"runs": [*read(root), done]}, indent=2, sort_keys=True) + "\n",
    )
    return done


# -- reading it back -------------------------------------------------------------------


def assets(root: str | Path = ".") -> list[str]:
    return sorted({one["asset"] for one in read(root)})


def _totals(runs: list[dict]) -> dict:
    accepted = [one for one in runs if one.get("accepted")]
    return {
        "runs": len(runs),
        "accepted": len(accepted),
        "seconds": round(sum(one["seconds"] for one in runs), 3),
        "renders": sum(one["renders"] for one in runs),
        "calls": sum(one["calls"] for one in runs),
        "credits": sum(one["credits"] for one in runs),
        "results": sum(one.get("results", 0) for one in runs),
        "overruled": sum(one.get("overruled", 0) for one in runs),
        "commits": sorted({one["commit"] for one in runs if one["commit"]}),
    }


def compare(asset: str, *, root: str | Path = ".") -> dict:
    """The two ways side by side, with what changed between them.

    Where a number went up, it says so. A loop that spends fewer seconds and twice the
    renders has moved the cost rather than removed it, and that is exactly the thing
    this line exists to make visible.
    """
    runs = [one for one in read(root) if one["asset"] == asset]
    sides = {way: [one for one in runs if one["way"] == way] for way in WAYS}
    if not sides["before"] or not sides["after"]:
        missing = "before" if not sides["before"] else "after"
        raise PolyweaveError(
            "loop.nothing-to-compare",
            f"{asset} has no {missing} run recorded, so there is nothing to compare",
            f"record the {missing} way; a claim measured on one side is not measured",
        )

    before, after = _totals(sides["before"]), _totals(sides["after"])
    changed = {
        name: _change(before[name], after[name])
        for name in ("seconds", "renders", "calls", "credits", "overruled")
    }
    return {
        "asset": asset,
        "before": before,
        "after": after,
        "changed": changed,
        "verdict": _verdict(changed, before, after),
    }


def _change(before: float, after: float) -> dict:
    return {
        "before": before,
        "after": after,
        "delta": round(after - before, 3),
        "times": round(after / before, 3) if before else None,
    }


def _verdict(changed: dict, before: dict, after: dict) -> str:
    """One sentence, and it is allowed to say the plugin made things worse."""
    if after["overruled"] > before["overruled"]:
        return (
            f"a person overruled the tool {after['overruled']} times against "
            f"{before['overruled']}: faster or not, it is approving work that gets "
            f"rejected"
        )
    seconds = changed["seconds"]
    if seconds["delta"] >= 0:
        return (
            f"it took {seconds['delta']:+g}s, so the work was not reduced by this "
            f"measure"
        )
    moved = [
        name for name in ("renders", "calls", "credits") if changed[name]["delta"] > 0
    ]
    if moved:
        return (
            f"{-seconds['delta']:g}s faster, but {', '.join(moved)} went up — the cost "
            f"may have moved rather than gone"
        )
    return f"{-seconds['delta']:g}s faster, with nothing else higher"
