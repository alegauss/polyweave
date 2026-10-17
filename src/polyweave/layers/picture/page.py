"""The picture layer's part of the brief, the review page and the report (§PW505).

The shared surfaces call these by the names `layer.py` gives them, so the page, the
brief and `loop.report` name no medium.
"""

from __future__ import annotations

from pathlib import Path

from polyweave.kernel.config import load
from polyweave.kernel.errors import PolyweaveError

from . import picture, style

#: The canon a style holds, under a name a local `style` table cannot shadow.
admitted_to = style.admitted


def gates(root) -> list[dict]:
    """Every gate run, each candidate with what is left of its service's ceiling.

    The refused beside the kept (§PW175), with the numbers the agent used and what is
    left to spend, read now rather than when the gate ran.
    """
    from polyweave.services import purchase

    left: dict = {}
    found = picture.gates(root)
    for run in found:
        for one in run["candidates"]:
            service = (one.get("bought") or {}).get("service")
            if service and service not in left:
                try:
                    left[service] = purchase.remaining(str(root), service=service)
                except PolyweaveError:
                    left[service] = None
            one["ceiling"] = left.get(service)
            one["compare"] = _compared_with(root, run, one)
    return found


def _compared_with(root, run: dict, one: dict) -> dict | None:
    """What a candidate is best compared against, and how (§PW176).

    A variation against its parent, as a slider with its mask outlined; anything else
    against its family's first canon picture, as a difference map.
    """
    from polyweave.kernel import provenance

    config = load(root)
    here = config.root
    try:
        details = provenance.read(one["picture"], root=here).get("details") or {}
    except PolyweaveError:
        details = {}
    if (details.get("parent") or {}).get("path"):
        return {
            "old": details["parent"]["path"],
            "mode": "slider",
            "mask": details.get("mask"),
        }
    try:
        _, declared = config.style(run.get("family"))
    except PolyweaveError:
        return None
    canon = style.admitted(declared)
    if not canon:
        return None
    first = provenance.relative(Path(declared["canon"]) / canon[0]["picture"], here)
    return {"old": first, "mode": "difference", "mask": None}


def overruled(root, body: dict) -> tuple[list[dict], str, str]:
    """A refused picture promoted by a person: the members, the sitting and family."""
    ran = {one["id"]: one for one in picture.gates(root)}
    run = ran.get(str(body.get("gate") or ""))
    held = {one["picture"]: one for one in (run or {}).get("candidates", ())}
    if run is None:
        # The runs themselves, where the gate is the unknown one (§PW265).
        raise PolyweaveError(
            "loop.unknown-sitting",
            f"there is no gate run {body.get('gate')!r} in this project",
            f"name one of the gate runs: {', '.join(sorted(ran)) or 'there are none'}",
            given=str(body.get("gate")),
            allowed=sorted(ran),
        )
    chosen = held.get(str(body.get("picture") or ""))
    if chosen is None:
        raise PolyweaveError(
            "loop.unknown-sitting",
            f"gate run {run['id']} has no picture {body.get('picture')!r}",
            f"name one of its pictures: {', '.join(sorted(held))}",
            given=str(body.get("picture")),
            allowed=sorted(held),
        )
    name = Path(chosen["picture"]).stem
    member = {"name": name, "new": chosen["picture"], "passed": chosen["passed"]}
    return [member], f"gate:{run['id']}", name


def admitted(root, body: dict) -> tuple[list[dict], str, str]:
    """A candidate admitted to a canon by a person, never gated (§PW266).

    Only a picture the family's own `candidates` lists: the page can admit what the
    project pointed at, and not any file a request names.
    """
    config = load(root)
    name, declared = config.style(body.get("canon") or None)
    offered = {
        one["path"]: one
        for one in style.candidates(declared, style.admitted(declared), config.root)
    }
    chosen = str(body.get("admit") or "")
    if chosen not in offered:
        raise PolyweaveError(
            "style.not-a-candidate",
            f"{chosen!r} is not a candidate of the {name} canon",
            f"admit one of {', '.join(sorted(offered))}"
            if offered
            else f"point [style.{name}] candidates at the pictures a person may admit",
            given=chosen,
            allowed=sorted(offered),
        )
    stem = Path(chosen).stem
    member = {"name": stem, "new": chosen, "passed": True, "canon": name}
    return [member], f"canon:{name}", stem


def withdraw(root, body: dict) -> dict:
    """A picture out of its canon, by the page's withdraw (§PW266)."""
    return style.withdraw(
        str(body["withdraw"]),
        family=body.get("canon") or None,
        why=str(body.get("why") or ""),
        root=Path(root),
    )


def boards(root) -> list:
    """Each style family's canon board, as the page's canon tab draws it."""
    config = load(root)
    families = config.styles() if config.states("style") else {}
    return [style.board(name, config.root) for name in families]


def family(record: dict, here: Path) -> dict | None:
    """The style family a picture is held to: the one it was bought for, or the one."""
    from polyweave.kernel.config import load

    config = load(here)
    if not config.states("style"):
        return None
    family = (record.get("details") or {}).get("family")
    try:
        name, style = config.style(family)
    except PolyweaveError as refused:
        return {"refused": refused.as_dict()}
    return {
        "family": name,
        "palette": style["palette"],
        "skeleton": style["skeleton"],
        "cell": style["cell"],
        "filter": style["filter"],
        "canon": style["canon"] or None,
        "admitted": len(admitted_to(style)),
    }


def read(item: dict, record: dict, here: Path) -> dict | None:
    """A picture in the brief: the style family it is held to."""
    return family(record, here)


def gate(path: str | None, here: Path) -> dict | None:
    """The last gate run that weighed this picture, in its two lanes (§PW175, §PW304).

    The refused beside the kept, each refused one with what failed it, so a person sees
    what the filter turned away and not only what it let through.
    """
    from polyweave.kernel import provenance

    if not path:
        return None
    runs = [
        run
        for run in picture.gates(here)
        if any(
            provenance.relative(one["picture"], here) == path
            for one in run.get("candidates") or ()
        )
    ]
    if not runs:
        return None
    run = runs[-1]
    lanes = [
        (provenance.relative(one["picture"], here), one) for one in run["candidates"]
    ]
    return {
        "run": run.get("id"),
        "at": run.get("at"),
        "kept": [where for where, one in lanes if one.get("passed")],
        "refused": [
            {"picture": where, "failed": one.get("failed") or []}
            for where, one in lanes
            if not one.get("passed")
        ],
    }


def report_gate(root) -> dict | None:
    """How many candidates the picture gate refused before a person saw any."""
    from polyweave.kernel.provenance import relative

    config = load(root)
    looked = [c for run in picture.gates(root) for c in run.get("candidates", ())]
    if not looked:
        return None
    return {
        "candidates": len(looked),
        "refused": sum(1 for c in looked if c.get("passed") is False),
        "unchecked": sum(1 for c in looked if c.get("passed") is None),
        "from": relative(config.path("paths.work") / picture.GATES, config.root),
    }
