"""Editorial labels held against each other and against the footage under them (§PW709).

A caption and a spoken highlight can be on screen at once with two versions of one
fact, or the same words twice, and a highlight naming a person or an event can sit over
stock footage of someone else, implying that is them. `video.labels` reads the labels a
cut declares, each with its time and the entities it names, and the footage with the
entities each stretch is declared to show, and reports every overlap and every named
entity the footage under it does not declare. It is read-only and mechanical: it never
infers who is in a picture, and a match it reports is the declarations agreeing, not a
fact about the image.
"""

from __future__ import annotations

import unicodedata
from typing import Annotated, Any

from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

#: What a label or a stretch of footage may carry besides its times.
_LABEL = {"id", "kind", "text", "start", "end", "entities", "source", "take", "beat"}
_FOOTAGE = {"id", "start", "end", "source", "entities"}


def _bad(message: str, remedy: str, **extra: Any) -> PolyweaveError:
    return PolyweaveError("video.bad-labels", message, remedy, **extra)


def _checked(rows: Any, keys: set, what: str) -> list[dict]:
    if not isinstance(rows, list):
        raise _bad(f"{what} is not a list", f"give {what} as a list of records")
    found = []
    for n, one in enumerate(rows):
        at = f"{what}[{n}]"
        if not isinstance(one, dict):
            raise _bad(f"{at} is not a record", "give each as a table", at=at)
        stray = sorted(set(one) - keys)
        if stray:
            raise _bad(f"{at} has {stray[0]!r}", f"use only {', '.join(sorted(keys))}",
                       given=stray[0], allowed=sorted(keys))
        start, end = one.get("start"), one.get("end")
        if not all(isinstance(v, int | float) and not isinstance(v, bool)
                   for v in (start, end)) or end <= start:
            raise _bad(f"{at} runs {start!r} to {end!r}",
                       "give start and end seconds, end after start", at=at)
        entities = one.get("entities") or []
        if not isinstance(entities, list):
            raise _bad(f"{at}.entities is not a list", "list the entities it names",
                       at=at)
        found.append({**one, "id": str(one.get("id") or f"{what}[{n}]"),
                      "entities": [str(e) for e in entities]})
    return found


def _folded(text: Any) -> str:
    apart = unicodedata.normalize("NFKD", str(text or "").casefold())
    return " ".join("".join(c for c in apart if c.isalnum() or c.isspace()).split())


def _named(one: dict) -> dict:
    """A label as the report names it: its id and where it came from."""
    return {k: one[k] for k in ("id", "kind", "text", "source", "take", "beat",
                                "start", "end") if k in one}


@operation("video.labels")
def labels(
    labels: Annotated[
        list, Param("each {id, kind, text, start, end, entities, source, take, beat}")
    ],
    footage: Annotated[
        list, Param("each stretch {id, start, end, source, entities} it is shown over")
    ] = None,
) -> dict:
    """Every pair of labels on screen at once, and every named entity left unshown.

    Two labels whose times overlap are reported with both and the overlap, as
    `duplicate` where their words are the same (case, accents and punctuation folded)
    and `versions` where they differ. A label naming `entities` is held to the footage
    under it: each stretch it overlaps that does not declare one of them is reported
    under `unverified`, with the label and the stretch. Nothing is inferred from a
    picture; the declarations are what is compared.
    """
    said = _checked(labels, _LABEL, "labels")
    shown = _checked(footage or [], _FOOTAGE, "footage")
    overlaps = []
    ordered = sorted(said, key=lambda one: (one["start"], one["end"]))
    for i, one in enumerate(ordered):
        for other in ordered[i + 1:]:
            if other["start"] >= one["end"]:
                break
            overlaps.append({
                "labels": [_named(one), _named(other)],
                "from": round(max(one["start"], other["start"]), 3),
                "to": round(min(one["end"], other["end"]), 3),
                "same": "duplicate" if _folded(one.get("text")) == _folded(
                    other.get("text")) else "versions",
            })
    unverified = []
    for one in said:
        if not one["entities"]:
            continue
        under = [s for s in shown
                 if s["start"] < one["end"] and one["start"] < s["end"]]
        for stretch in under:
            missing = [e for e in one["entities"] if e not in stretch["entities"]]
            if missing:
                unverified.append({"label": _named(one), "footage": {
                    k: stretch[k] for k in ("id", "source", "start", "end")
                    if k in stretch}, "entities": missing})
        if not under and shown:
            unverified.append({"label": _named(one), "footage": None,
                               "entities": one["entities"]})
    return {"labels": len(said), "footage": len(shown), "overlaps": overlaps,
            "unverified": unverified, "passed": not overlaps and not unverified}
