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
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from .config import load
from .errors import PolyweaveError
from .files import write_atomic

#: The two things being compared: the pipeline as it was, and the plugin.
WAYS = ("before", "after")

#: The costs a run records, and so the ones it can say it did not measure (§PW116).
MEASURED = ("seconds", "renders", "calls", "credits", "person_minutes")


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
    change: str | None = None,
    unmeasured: tuple[str, ...] | list[str] = (),
) -> dict:
    """Begin recording one asset made one way.

    A baseline started after the plugin has already made this asset is **refused**: the
    whole value of a baseline is that nobody knew the answer when it was taken.

    `change` names a perturbation of an asset already made both ways (§PW114): a hue in
    the palette, a sample count, a renderer version. The old rig's cost was never the
    first bake but the retuning that returns whenever something moves, so each way
    getting back to an accepted look after one named change is the comparison that can
    falsify the claim. The same rule holds per change: its baseline comes first.

    `unmeasured` names what this run did not measure (§PW116) — `seconds` for a hand
    search nobody timed, `renders` for work done before recording began — so a
    comparison can say which verdicts the missing numbers put out of reach instead of
    summing a partial side as a whole one.
    """
    unknown = sorted(set(unmeasured) - set(MEASURED))
    if unknown:
        raise PolyweaveError(
            "loop.unknown-measure",
            f"a run cannot leave {', '.join(unknown)} unmeasured; it records no such "
            "number",
            f"name some of {', '.join(MEASURED)}",
        )
    if way not in WAYS:
        raise PolyweaveError(
            "loop.unknown-way",
            f"{way!r} is neither of the two ways being compared",
            f"say one of {', '.join(WAYS)}",
        )
    runs = [r for r in read(root) if r["asset"] == asset]
    if change is not None:
        ported = {r["way"] for r in runs if r.get("change") is None}
        if ported != set(WAYS):
            raise PolyweaveError(
                "loop.not-ported",
                f"{asset} has not been made both ways, so a change to it has nothing "
                "to be measured against",
                "record the port first: a before and an after run with no change",
            )
    if way == "before":
        already = [
            r for r in runs if r["way"] == "after" and r.get("change") == change
        ]
        if already:
            event = f"after {change!r}" if change is not None else "the new way"
            raise PolyweaveError(
                "loop.baseline-too-late",
                f"{asset} has already been made {event} {len(already)} time(s), "
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
        "person_minutes": 0.0,
        "cache_hits": 0,
        "verdicts": [],
        **({"change": str(change)} if change is not None else {}),
        **({"unmeasured": sorted(set(unmeasured))} if unmeasured else {}),
    }


def spent(
    run: dict,
    *,
    renders: int = 0,
    calls: int = 0,
    credits: int = 0,
    seconds: float = 0,
    person_minutes: float = 0,
) -> dict:
    """Add to what this run has cost so far. Called as the work happens.

    `person_minutes` is a person's own time, timed as it happens: retuning constants by
    hand is what the old way costs after a change, and the machine's seconds miss it.
    """
    run["renders"] += int(renders)
    run["calls"] += int(calls)
    run["credits"] += int(credits)
    run["seconds"] += float(seconds)
    run["person_minutes"] = run.get("person_minutes", 0.0) + float(person_minutes)
    return run


#: The run bakes report into while one is open in this context (§PW115).
_OPEN: ContextVar[dict | None] = ContextVar("polyweave_loop_run", default=None)


@contextmanager
def recording(run: dict) -> Iterator[dict]:
    """Let every bake in this block count itself into `run`, rather than the caller.

    Recording the stars charged 32 renders for 28, because four of the final bakes were
    cache hits and the caller added them up as renders. A bake already knows which it
    was, so it says so here: a fresh render adds to `renders`, a hit to `cache_hits`,
    and both add their seconds to `render_seconds`. `spent` stays for what the plugin
    cannot see, such as a service call made elsewhere.
    """
    token = _OPEN.set(run)
    try:
        yield run
    finally:
        _OPEN.reset(token)


def bake_seen(answer: dict) -> None:
    """One bake's answer, counted into the open run where there is one."""
    run = _OPEN.get()
    if run is None:
        return
    key = "cache_hits" if answer.get("cached") else "renders"
    run[key] = run.get(key, 0) + 1
    run["render_seconds"] = round(
        run.get("render_seconds", 0.0) + float(answer.get("elapsed_s") or 0.0), 3
    )


def judged(
    run: dict,
    *,
    tool_passed: bool,
    person_accepted: bool,
    why: str = "",
    check: dict | None = None,
    named: tuple[str, ...] | list[str] = (),
) -> dict:
    """One result, as the tool called it and as a person called it.

    Both, always. A tool's own verdict is worth nothing on its own here — the number
    this line is really after is the gap between the two.

    `check` is what `accept.check` said of the result, and `named` the predicates a
    person blamed when they overruled it (§PW108). With them the verdict keeps each
    predicate's value at the moment it was given, which is what lets `bounds` say which
    number a rejection was about. A caller passing neither records what it always did.
    """
    verdict = {
        "tool_passed": bool(tool_passed),
        "person_accepted": bool(person_accepted),
        "why": str(why),
        "at": time.time(),
    }
    if check is not None:
        verdict["predicates"] = [
            {
                "id": one["id"],
                "value": one.get("value"),
                "passed": bool(one.get("passed")),
                "side": (one.get("bound") or {}).get("side"),
            }
            for one in check.get("predicates", ())
        ]
    if named:
        known = {one["id"] for one in verdict.get("predicates", ())}
        unknown = sorted(set(named) - known)
        if unknown:
            raise PolyweaveError(
                "loop.unknown-predicate",
                f"the verdict names {', '.join(unknown)}, which the check it was "
                "given does not carry",
                "pass the check the person judged, and name predicates from it: "
                + (", ".join(sorted(known)) or "it has none"),
            )
        verdict["named"] = sorted(set(named))
    run["verdicts"].append(verdict)
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
        # Not free and not a render: a loop fast because it repeats itself shows here.
        "cache_hits": sum(one.get("cache_hits", 0) for one in runs),
        "calls": sum(one["calls"] for one in runs),
        "credits": sum(one["credits"] for one in runs),
        "person_minutes": round(sum(one.get("person_minutes", 0.0) for one in runs), 3),
        "results": sum(one.get("results", 0) for one in runs),
        "overruled": sum(one.get("overruled", 0) for one in runs),
        "commits": sorted({one["commit"] for one in runs if one["commit"]}),
    }


#: How many times a bound must be overruled the same way before it is called wrong.
#: Once is a person's mood; twice in one direction is a pattern worth a number.
WRONG_AFTER = 2


def bounds(root: str | Path = ".", *, asset: str | None = None) -> list[dict]:
    """Which bounds a person overruled, which way, and with what values (§PW108).

    Arithmetic over the ledger, not a model of taste. A bound is **too tight** when its
    predicate failed and a person accepted the result anyway: the side it broke is the
    one to move. It is **too loose** when its predicate passed, a person rejected the
    result, and named it. A rejection naming nothing is counted as `unattributed` on
    its asset rather than spread over every predicate that happened to pass.
    """
    found: dict[tuple[str, str, str], dict] = {}
    unattributed: dict[str, int] = {}
    for run in read(root):
        if asset is not None and run["asset"] != asset:
            continue
        for verdict in run.get("verdicts", ()):
            accepted = verdict["person_accepted"]
            named = set(verdict.get("named", ()))
            if not accepted and verdict["tool_passed"] and not named:
                unattributed[run["asset"]] = unattributed.get(run["asset"], 0) + 1
            for one in verdict.get("predicates", ()):
                if accepted and not one["passed"]:
                    way = "tight"
                elif not accepted and one["passed"] and one["id"] in named:
                    way = "loose"
                else:
                    continue
                key = (run["asset"], one["id"], one.get("side") or "")
                entry = found.setdefault(
                    key,
                    {
                        "asset": key[0],
                        "id": key[1],
                        "side": key[2] or None,
                        "tight": [],
                        "loose": [],
                    },
                )
                entry[way].append(one["value"])
    out = []
    for entry in found.values():
        tight, loose = len(entry["tight"]), len(entry["loose"])
        entry["wrong"] = None
        if max(tight, loose) >= WRONG_AFTER and tight != loose:
            bound = f"{entry['id']}'s {entry['side'] or 'bound'}"
            if tight > loose:
                entry["wrong"] = (
                    f"{bound} is too tight: {tight} result(s) it failed were "
                    f"accepted, at {_listed(entry['tight'])}"
                )
            else:
                entry["wrong"] = (
                    f"{bound} is too loose: {loose} result(s) it passed were "
                    f"rejected for it, at {_listed(entry['loose'])}"
                )
        out.append(entry)
    out.sort(key=lambda e: (e["wrong"] is None, e["asset"], e["id"], e["side"] or ""))
    return out + [
        {"asset": name, "unattributed": count}
        for name, count in sorted(unattributed.items())
    ]


def pending(root: str | Path = ".") -> dict:
    """Which assets wait on a person's look, and where every asset stands (§PW110).

    A read over what is already on disk and nothing else: the ledger, the specs under
    `[paths] specs` and the render records under `[paths] renders`. A render is a
    candidate for an asset when its file is named after it (`<asset>.png`), and the
    asset **waits** when its newest candidate is newer than the last verdict a person
    gave on it, or when it has none. The list decides nothing and reorders nothing; it
    is what lets a person's time be asked for once rather than once per family.
    """
    from datetime import datetime

    from . import accept, provenance

    settings = load(root)
    here = Path(root).resolve()
    rows: dict[str, dict] = {}

    def row(name: str) -> dict:
        return rows.setdefault(
            name,
            {
                "asset": name,
                "spec": None,
                "before": False,
                "after": False,
                "candidate": None,
                "judged": None,
                "waiting": False,
            },
        )

    specs = settings.path("paths.specs")
    for found in sorted(specs.rglob(f"*{accept.SUFFIX}")) if specs.is_dir() else ():
        try:
            name = accept.read(found).asset
        except PolyweaveError:
            name = found.name[: -len(accept.SUFFIX)]
        row(name)["spec"] = provenance.relative(found, here)

    judged_at: dict[str, float] = {}
    for run in read(root):
        one = row(run["asset"])
        one[run["way"]] = True
        for verdict in run.get("verdicts", ()):
            judged_at[run["asset"]] = max(
                judged_at.get(run["asset"], 0.0), float(verdict.get("at", 0.0))
            )

    made = _candidates(settings.path("paths.renders"), set(rows), here)
    for name, one in rows.items():
        if name in made:
            one["candidate"] = made[name][1]
        if name in judged_at:
            one["judged"] = datetime.fromtimestamp(judged_at[name]).isoformat(
                timespec="seconds"
            )
        one["waiting"] = name in made and made[name][0] > judged_at.get(name, 0.0)
    listed = sorted(rows.values(), key=lambda r: (not r["waiting"], r["asset"]))
    waiting = [r["asset"] for r in listed if r["waiting"]]
    return {
        "assets": listed,
        "pending": waiting,
        "says": f"{len(waiting)} asset(s) wait on a person's look: "
        + (", ".join(waiting) or "none")
        + ("; one sitting can take all of them" if len(waiting) > 1 else ""),
    }


def _candidates(
    renders: Path, names: set[str], here: Path
) -> dict[str, tuple[float, str]]:
    """The newest render of each named asset, as (when, artefact), off its record."""
    from datetime import datetime

    from . import provenance

    made: dict[str, tuple[float, str]] = {}
    if not renders.is_dir():
        return made
    for found in sorted(renders.rglob(f"*{provenance.SUFFIX}")):
        try:
            record = provenance.read(found, here)
        except PolyweaveError:
            continue
        artefact = (record.get("artefact") or {}).get("path") or ""
        name = Path(artefact).stem
        if name not in names or record.get("kind") != "render":
            continue
        stamp = str(record.get("produced_at") or "").replace("Z", "+00:00")
        try:
            when = datetime.fromisoformat(stamp).timestamp()
        except ValueError:
            continue
        if when >= made.get(name, (float("-inf"), ""))[0]:
            made[name] = (when, artefact)
    return made


def _listed(values: list) -> str:
    return ", ".join(f"{v:g}" if isinstance(v, int | float) else str(v) for v in values)


def changes(asset: str, *, root: str | Path = ".") -> list[str]:
    """Every change an asset has been measured through, in the order first recorded."""
    named = [one.get("change") for one in read(root) if one["asset"] == asset]
    return list(dict.fromkeys(c for c in named if c is not None))


def compare(asset: str, *, root: str | Path = ".", change: str | None = None) -> dict:
    """The two ways side by side, with what changed between them.

    Where a number went up, it says so. A loop that spends fewer seconds and twice the
    renders has moved the cost rather than removed it, and that is exactly the thing
    this line exists to make visible.

    Without `change` this is the first port; with one it is the runs that got the asset
    back to an accepted look after that change (§PW114), which is the event the claim
    is about. `event` says which was compared, and `changes` lists the others.
    """
    runs = [
        one
        for one in read(root)
        if one["asset"] == asset and one.get("change") == change
    ]
    sides = {way: [one for one in runs if one["way"] == way] for way in WAYS}
    if not sides["before"] or not sides["after"]:
        missing = "before" if not sides["before"] else "after"
        event = f" after {change!r}" if change is not None else ""
        raise PolyweaveError(
            "loop.nothing-to-compare",
            f"{asset} has no {missing} run recorded{event}, so there is nothing to "
            "compare",
            f"record the {missing} way; a claim measured on one side is not measured",
        )

    before, after = _totals(sides["before"]), _totals(sides["after"])
    changed = {
        name: _change(before[name], after[name])
        for name in (
            "seconds",
            "renders",
            "calls",
            "credits",
            "person_minutes",
            "overruled",
        )
    }
    # What either side said it never measured (§PW116): those numbers are partial, and
    # the verdicts that rest on them are out of reach rather than decided.
    missing = {
        way: sorted({n for one in sides[way] for n in one.get("unmeasured", ())})
        for way in WAYS
    }
    return {
        "asset": asset,
        "event": f"after {change}" if change is not None else "the first port",
        "changes": changes(asset, root=root),
        "before": before,
        "after": after,
        "changed": changed,
        "unmeasured": missing,
        "verdict": _verdict(
            changed, before, after, set(missing["before"]) | set(missing["after"])
        ),
    }


def _change(before: float, after: float) -> dict:
    return {
        "before": before,
        "after": after,
        "delta": round(after - before, 3),
        "times": round(after / before, 3) if before else None,
    }


def _verdict(
    changed: dict, before: dict, after: dict, unmeasured: set[str] = frozenset()
) -> str:
    """One sentence, and it is allowed to say the plugin made things worse.

    The overruling verdict needs only the counts of verdicts, so it stands whatever a
    side left unmeasured. Faster, slower and moved all rest on the costs, and a cost a
    side never measured cannot decide them (§PW116).
    """
    if after["overruled"] > before["overruled"]:
        return (
            f"a person overruled the tool {after['overruled']} times against "
            f"{before['overruled']}: faster or not, it is approving work that gets "
            f"rejected"
        )
    if "seconds" in unmeasured:
        return (
            "inconclusive: a side never measured its seconds, so neither faster nor "
            "slower can be said; only a rise in overruling could have been"
        )
    seconds = changed["seconds"]
    if seconds["delta"] >= 0:
        return (
            f"it took {seconds['delta']:+g}s, so the work was not reduced by this "
            f"measure"
        )
    watched = [
        name
        for name in ("renders", "calls", "credits", "person_minutes")
        if name not in unmeasured
    ]
    moved = [name for name in watched if changed[name]["delta"] > 0]
    if moved:
        return (
            f"{-seconds['delta']:g}s faster, but {', '.join(moved)} went up — the cost "
            f"may have moved rather than gone"
        )
    if len(watched) < 4:
        unseen = sorted(set(unmeasured) - {"seconds"})
        return (
            f"{-seconds['delta']:g}s faster, with nothing measured higher; "
            f"{', '.join(unseen)} went unmeasured on a side"
        )
    return f"{-seconds['delta']:g}s faster, with nothing else higher"
