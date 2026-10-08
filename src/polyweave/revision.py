"""A change a person asks for, kept as a record rather than a chat line (§PW301).

The review page keeps a person's words and a mask when they answer a sitting the agent
laid out. Starting from the other end was not possible: "this picture needs a warmer
rim", said about an item nobody put up for review, lived only in the conversation that
heard it, and nothing told the next session it was asked.

A revision is an event appended to `[paths] work/revisions.jsonl`, the same way the
page's answers are kept: the inventory id, the digest the person was looking at, an
optional mask or time span, their words and when. `revision.ask` writes one,
`revision.open` hands the open ones over with each item's brief, and `revision.close`
ends one with the run and the sitting that answered it, or the reason it was withdrawn.
Nothing here closes on a verdict: the verdict stays the person's.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from .describe import Param, operation
from .errors import PolyweaveError

#: Where every revision event lands, one line each, appended and never rewritten.
REVISIONS = "revisions.jsonl"

ROOT = Param("the project the item is in")


def _file(root: str) -> Path:
    from .config import load

    return load(root).path("paths.work") / REVISIONS


def _events(root: str) -> list[dict]:
    from .files import read_text_retrying

    text = read_text_retrying(_file(root)) or ""
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _append(event: dict, root: str) -> dict:
    where = _file(root)
    where.parent.mkdir(parents=True, exist_ok=True)
    with where.open("a", encoding="utf-8", newline="\n") as appended:
        appended.write(json.dumps(event, sort_keys=True) + "\n")
    return event


def _now() -> str:
    return datetime.now(tz=UTC).isoformat(timespec="microseconds")


def _rows(root: str) -> dict[str, dict]:
    from . import project
    from .config import load

    return {row["id"]: row for row in project._items(load(root).root)}


@operation("revision.ask")
def ask(
    item: Annotated[str, Param("the item, by the id project.inventory gives it")],
    words: Annotated[str, Param("what the person asked for, in their words")],
    *,
    mask: Annotated[
        str, Param("a mask under the project, black where the change is wanted")
    ] = "",
    span: Annotated[
        list, Param("for a sound, [start, end] in seconds", unit="s")
    ] = (),
    root: Annotated[str, ROOT] = ".",
) -> dict:
    """Keep a person's request to change one item, against what they were looking at.

    Written on a person's behalf: the words are theirs, never the agent's own idea of
    what the item needs. The digest is the item's as it is now, so a later read can say
    whether the item has moved since the request was made.
    """
    rows = _rows(root)
    if item not in rows:
        raise PolyweaveError(
            "review.unknown-item",
            f"project.inventory lists no item {item!r}",
            "name an item by the id project.inventory gives it",
            given=item,
            allowed=sorted(rows),
        )
    if not words.strip():
        raise PolyweaveError(
            "review.no-words",
            "a revision with no words asks for nothing",
            "pass what the person asked for, in their words",
        )
    event: dict = {
        "event": "asked",
        "revision": uuid.uuid4().hex[:12],
        "item": item,
        "digest": rows[item]["digest"],
        "words": words.strip(),
        "at": _now(),
    }
    if mask:
        event["mask"] = _masked(mask, root)
    if len(span):
        event["span"] = _span(span)
    return _append(event, root)


def _masked(mask: str, root: str) -> str:
    from . import provenance
    from .config import load

    here = load(root).root
    where = Path(mask) if Path(mask).is_absolute() else here / mask
    if not where.is_file():
        raise PolyweaveError(
            "review.no-mask",
            f"there is no mask at {mask}",
            "pass a mask image under the project, black where the change is wanted",
        )
    return provenance.relative(where, here)


def _span(span) -> list[float]:
    try:
        start, end = (float(v) for v in span)
    except (TypeError, ValueError):
        start = end = -1.0
    if not 0.0 <= start < end:
        raise PolyweaveError(
            "review.bad-span",
            f"span is {list(span)!r}, which is not a stretch of time",
            "pass [start, end] in seconds, the start before the end",
            example="span = [1.5, 2.25]",
        )
    return [start, end]


def _open(root: str) -> dict[str, dict]:
    """Every revision asked and not yet closed, by its id, oldest first."""
    asked: dict[str, dict] = {}
    for event in _events(root):
        if event.get("event") == "asked":
            asked[event["revision"]] = {**event, "turns": []}
        elif event.get("event") == "turn" and event.get("revision") in asked:
            asked[event["revision"]]["turns"].append(
                {key: event[key] for key in ("by", "text", "at")}
            )
        elif event.get("event") == "closed":
            asked.pop(event.get("revision"), None)
    return asked


@operation("revision.open")
def open_(
    item: Annotated[str, Param("only this item's; every open one if empty")] = "",
    *,
    root: Annotated[str, ROOT] = ".",
) -> dict:
    """The revisions still open, each with its item's brief and whether it has moved.

    `moved` is true where the item's digest is no longer the one the person was looking
    at, so the agent knows the request may already be answered, or was made of an
    earlier version.
    """
    from . import brief

    rows = _rows(root)
    found = []
    for event in _open(root).values():
        if item and event["item"] != item:
            continue
        row = rows.get(event["item"])
        one = {**event, "moved": row is None or row["digest"] != event["digest"]}
        # Where it is judged, and what the person said there (§PW307).
        one["sitting"] = _laid(event, root)
        one["answer"] = _answer(one["sitting"], root)
        try:
            one["brief"] = brief.brief(event["item"], root=root)
        except PolyweaveError as refused:
            one["brief"] = {"refused": refused.as_dict()}
        found.append(one)
    return {"revisions": found, "file": str(_file(root))}


#: Who a turn of a revision's conversation is from.
SPEAKERS = ("person", "session")


@operation("revision.turn")
def turn(
    revision: Annotated[str, Param("the revision, by the id revision.ask gave it")],
    text: Annotated[str, Param("what was said, whole")],
    *,
    by: Annotated[str, Param("who said it", choices=SPEAKERS)] = "person",
    root: Annotated[str, ROOT] = ".",
) -> dict:
    """Keep one turn of the conversation a revision is worked through (§PW306).

    The person refining what they asked, or the session answering, kept on the revision
    itself, so the request and how it was talked through travel together and a later
    session reads both. `revision.open` lists each revision's turns, oldest first.
    """
    still = _open(root)
    if revision not in still:
        raise PolyweaveError(
            "review.not-open",
            f"revision {revision!r} is not open, so it takes no more turns",
            "keep a turn on one revision.open lists",
            given=revision,
            allowed=sorted(still),
        )
    if not text.strip():
        raise PolyweaveError(
            "review.no-words",
            "a turn with no words says nothing",
            "pass what was said",
        )
    event = {"event": "turn", "revision": revision, "by": by, "text": text.strip(),
             "at": _now()}
    return _append(event, root)


def _when(stamp: str) -> datetime:
    return datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))


def _laid(asked: dict, root: str) -> str | None:
    """The newest sitting laid out for this item since the person asked (§PW307).

    A member holds the item by its file, or, for a line, by its key. A sitting laid
    before the request answers an older question, so it does not count.
    """
    from . import review
    from .config import load

    item = asked["item"]
    key = item[len("line:"):] if item.startswith("line:") else None
    since = _when(asked["at"])
    found = None
    for sitting in review.sittings(load(root).root):
        if not sitting.get("at") or _when(sitting["at"]) < since.replace(microsecond=0):
            continue
        for laid in (sitting.get("families") or {}).values():
            for member in laid.get("members") or ():
                if member.get("new") == item or (key and member.get("line") == key):
                    found = sitting["manifest"]
    return found


def _answer(sitting: str | None, root: str) -> dict | None:
    """The person's latest answer on that sitting, as the review page kept it."""
    from . import verdict

    if not sitting:
        return None
    said = [one for one in verdict.answers(root=root)["answers"]
            if one.get("sitting") == sitting]
    if not said:
        return None
    return {key: said[-1].get(key) for key in ("choice", "why", "at", "family")}


#: The tools that write a file, whose path the scope is held against (§PW309).
WRITERS = "Write|Edit|MultiEdit|NotebookEdit"


def _scope(asked: dict, root: str) -> set[str]:
    """The files a change to this item may legitimately reach (§PW309).

    Its artefact and that file's record, its declaration, its spec, and everything made
    from it, by the provenance graph. Anything else is outside the revision.
    """
    from . import brief, provenance

    here = Path(root).resolve()
    row = _rows(root).get(asked["item"]) or {}
    own = [one for one in (row.get("artefact"), row.get("declaration")) if one]
    found = set(own)
    for path in own:
        found.add(provenance.relative(provenance.sidecar(path, here), here))
        for made in provenance.dependents(path, root=str(here))["artefacts"]:
            found.add(made["artefact"])
    try:
        held = brief.brief(asked["item"], root=str(here)).get("spec") or {}
        spec = held.get("path")
    except PolyweaveError:
        spec = None
    if spec:
        found.add(spec)
    return found


def _outside(path: str, asked: dict, root: str) -> str | None:
    """Why a write to this file is outside the revision, or None where it is inside."""
    from .config import FILENAME, load

    here = Path(root).resolve()
    where = Path(path)
    where = where if where.is_absolute() else here / where
    try:
        relative = where.resolve().relative_to(here).as_posix()
    except ValueError:
        return f"{path} is outside the project altogether"
    work = load(here).path("paths.work").resolve()
    if where.resolve().is_relative_to(work):
        return None  # the plugin's own work area: sittings, marks, caches
    if relative in _scope(asked, root):
        return None
    if relative == FILENAME:
        return (f"{relative} is the project's config, which every item is held to, "
                f"not only {asked['item']}")
    return (f"{relative} is not {asked['item']}, its declaration, its spec, or "
            "anything made from it")


def _reached(revision: str, asked: dict, root: str) -> dict:
    """What a revision's session wrote, and which of the item's dependents now wait."""
    from . import provenance

    here = Path(root).resolve()
    wrote = sorted({
        provenance.relative(e["file"], here)
        for e in _events(root)
        if e.get("event") == "touched" and e.get("revision") == revision
    })
    made = _scope(asked, root)
    waiting = sorted(
        one["artefact"] for one in provenance.outdated(str(here))["outdated"]
        if one["artefact"] in made
    )
    return {"touched": wrote, "waiting": waiting}


def _asked(revision: str, root: str) -> dict:
    still = _open(root)
    if revision not in still:
        raise PolyweaveError(
            "review.not-open",
            f"revision {revision!r} is not open",
            "name one revision.open lists",
            given=revision,
            allowed=sorted(still),
        )
    return still[revision]


@operation("revision.check")
def check(
    revision: Annotated[str, Param("the revision, by the id revision.ask gave it")],
    *,
    root: Annotated[str, ROOT] = ".",
) -> dict:
    """The item's own checks, run on it as it now stands (§PW307).

    Chosen by the item and never by the session: its acceptance spec where one holds
    it, words.check on a line's row, sound.measure on a sound. `passed` is None where
    nothing checks this kind yet, which is said rather than passed.
    """
    from . import brief, words
    from .config import load

    here = load(root).root
    asked = _asked(revision, root)
    item = asked["item"]
    briefed = brief.brief(item, root=str(here))
    kind = (briefed.get("item") or {}).get("kind")
    artefact = (briefed.get("artefact") or {}).get("path")
    spec = briefed.get("spec")
    checks: list[dict] = []
    if spec and spec.get("path") and artefact:
        from . import accept

        found = accept.checked(spec["path"], artefact, root=str(here))
        checks.append({
            "check": "accept.check",
            "passed": bool(found["passed"]),
            "failed": [r["id"] for r in found["predicates"] if not r["passed"]],
        })
    if kind == "line":
        key = item[len("line:"):]
        found = words.check(root=str(here))
        mine = [f for f in found["findings"] if f.get("key") == key]
        checks.append({"check": "words.check", "passed": not mine, "failed": mine})
    if kind in ("sound", "music") and artefact:
        from . import sound

        measured = sound.measure(here / artefact)
        checks.append({"check": "sound.measure", "passed": True, "measured": measured})
    passed = all(one["passed"] for one in checks) if checks else None
    said = (
        "nothing checks this kind of item yet; a person's verdict is the only bar"
        if passed is None
        else "every check passed" if passed
        else "failed: " + "; ".join(
            f"{one['check']} {one.get('failed')}" for one in checks if not one["passed"]
        )
    )
    return {"revision": revision, "item": item, "kind": kind, "checks": checks,
            "passed": passed, "said": said}


#: The tools after which the item's checks run: a write, or a polyweave operation.
WRITES = "Write|Edit|MultiEdit|NotebookEdit|mcp__polyweave__.*"

def paid() -> list[str]:
    """Every tool that draws on a paid balance, read from the registry (§PW308)."""
    from . import describe as D
    from .server import tool_name

    D.load()
    return sorted(
        f"mcp__polyweave__{tool_name(name)}"
        for name, op in D._REGISTRY.items()
        if op.spends
    )


#: The tools a revision's session never has: a verdict is the person's (non-goal).
WITHHELD = ("mcp__polyweave__verdict_judge", "mcp__polyweave__verdict_promote")


@operation("revision.settings")
def settings(
    revision: Annotated[str, Param("the revision, by the id revision.ask gave it")],
    *,
    root: Annotated[str, ROOT] = ".",
) -> dict:
    """The Claude Code settings a session on this revision runs under (§PW307).

    Hooks that run the item's own checks after every write and refuse a verdict tool,
    and a permission denying those tools outright. The window passes them as the
    session's settings; a terminal session gets the same with `claude --settings`.
    """
    import sys

    _asked(revision, root)
    command = (
        f'"{sys.executable}" -m polyweave hook revision --revision {revision} '
        f'--root "{Path(root).resolve()}"'
    )
    hook = [{"hooks": [{"type": "command", "command": command}]}]
    return {
        "permissions": {
            "deny": list(WITHHELD),
            # Asked every time, so a saved allow can never let one through (§PW308).
            "ask": paid(),
        },
        # What the session buys is tied to this revision in the ledger.
        "env": {"POLYWEAVE_REVISION": revision},
        "hooks": {
            "PreToolUse": [{"matcher": "|".join(WITHHELD), **hook[0]},
                           # A write outside the item asks first (§PW309).
                           {"matcher": WRITERS, **hook[0]}],
            "PostToolUse": [{"matcher": WRITES, **hook[0]}],
            # Finishing means a sitting the person answers, never the session's word.
            "Stop": hook,
        },
    }


def hooked(event: dict, revision: str, root: str) -> dict | None:
    """What the revision's hook answers one Claude Code hook event with (§PW307).

    A verdict tool is denied before it runs. After a write, the item's own checks run
    and their result goes back to the session as context it cannot skip; a write that
    did not touch the item, or its declaration, says nothing.
    """
    name = str(event.get("hook_event_name") or "")
    tool = str(event.get("tool_name") or "")
    if name == "PreToolUse" and tool in WITHHELD:
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "a verdict is the person's to give, never the "
            "session's: lay a sitting out and the person answers it",
        }}
    touched = str((event.get("tool_input") or {}).get("file_path") or "")
    if name == "PreToolUse" and touched:
        why = _outside(touched, _asked(revision, root), root)
        if why is None:
            return None
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": f"Outside revision {revision}: {why}.",
        }}
    if name == "PostToolUse" and touched and tool in WRITERS.split("|"):
        # Every file the session wrote is kept, so the closed revision lists them.
        _append({"event": "touched", "revision": revision, "file": touched,
                 "at": _now()}, root)
    if name == "Stop":
        asked = _asked(revision, root)
        if _laid(asked, root) or event.get("stop_hook_active"):
            return None
        return {
            "decision": "block",
            "reason": "This revision ends in a sitting the person answers, not in the "
            f"session's word: lay {asked['item']} out with verdict.sitting (a "
            "picture), "
            "sound.sitting (a sound) or words.sheet (a line), beside what it was.",
        }
    if name != "PostToolUse":
        return None
    asked = _asked(revision, root)
    rows = _rows(root)
    row = rows.get(asked["item"]) or {}
    touched = str((event.get("tool_input") or {}).get("file_path") or "")
    own = [one for one in (row.get("artefact"), row.get("declaration")) if one]
    if not tool.startswith("mcp__polyweave__") and not any(
        touched.replace("\\", "/").endswith(one) for one in own
    ):
        return None
    found = check(revision, root=root)
    return {"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": "The item's own checks after this change: "
        f"{found['said']}.",
    }}


@operation("revision.close")
def close(
    revision: Annotated[str, Param("the revision, by the id revision.ask gave it")],
    *,
    run: Annotated[str, Param("the id of the loop run that answered it")] = "",
    sitting: Annotated[str, Param("the sitting the person judged the answer in")] = "",
    withdrawn: Annotated[str, Param("why it is closed with no answer")] = "",
    root: Annotated[str, ROOT] = ".",
) -> dict:
    """End one revision: answered by a run and a sitting, or withdrawn with a reason.

    It never carries a verdict. Whether the answer is right is the person's to say, in
    the sitting this names.
    """
    still = _open(root)
    if revision not in still:
        closed = any(
            e.get("event") == "closed" and e.get("revision") == revision
            for e in _events(root)
        )
        raise PolyweaveError(
            "review.not-open",
            f"revision {revision!r} is "
            + ("already closed" if closed else "not one revision.ask gave"),
            "close one revision.open lists",
            given=revision,
            allowed=sorted(still),
        )
    answered = bool(run and sitting)
    if answered == bool(withdrawn) or (not answered and (run or sitting)):
        raise PolyweaveError(
            "review.unanswered",
            "a revision closes on a run and the sitting that judged it, or withdrawn",
            "pass run and sitting together, or withdrawn with the reason, not both",
        )
    event = {"event": "closed", "revision": revision, "at": _now()}
    # Every file it wrote, and what made from the item is now out of date (§PW309).
    event.update(_reached(revision, still[revision], root))
    # What the change cost, from the ledger entries its session tied to it (§PW308).
    from . import purchase

    bought = [e for e in purchase.read(root) if e.get("revision") == revision]
    if bought:
        event["spent"] = {
            service: round(sum(float(e.get("credits") or 0) for e in bought
                               if e.get("service") == service), 4)
            for service in sorted({str(e.get("service")) for e in bought})
        }
    if answered:
        event.update(run=run, sitting=sitting)
    else:
        event["withdrawn"] = withdrawn.strip()
    return {**_append(event, root), "item": still[revision]["item"]}
