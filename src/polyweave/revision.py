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
    if answered:
        event.update(run=run, sitting=sitting)
    else:
        event["withdrawn"] = withdrawn.strip()
    return {**_append(event, root), "item": still[revision]["item"]}
