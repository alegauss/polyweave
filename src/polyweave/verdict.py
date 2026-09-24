"""One sheet to look at, one call to answer it (§PW109).

The stars waited a day for one sentence from a person, and to get it an agent pointed at
a comparison picture, explained a 99th percentile against a ceiling, and then edited a
spec comment and a ledger entry by hand from the reply. The judgement was quick;
everything around it was not.

    members = [{"name": "star_dim", "spec": "docs/accept/star_dim.accept.toml",
                "new": "renders/star_dim.png", "old": "renders/old/star_dim.png",
                "shown": [96, 96]}]
    sheet(members, out="review/stars.png")          # what the person looks at
    judge(members, "number", "same star at size", run=run)   # what they said

A sheet and a command, never an editor: the person looks at a picture and says one word,
and the agent carries it. The verdict stays theirs — nothing here decides a look.
"""

from __future__ import annotations

from datetime import date as Date
from pathlib import Path

from . import accept, calibrate, loop
from .errors import PolyweaveError

#: What a person can say of a family, and what each one means for the spec.
CHOICES = {
    "accept": "the look is right and the spec agrees with it",
    "look": "the look is wrong: the renders go back, the bounds stay",
    "number": "the look is right and a bound that failed it is wrong: it moves to "
    "what was measured, as the person's",
}


def _checked(member: dict, root: Path) -> tuple[accept.Spec, Path, dict]:
    spec_path = Path(member["spec"])
    spec_path = spec_path if spec_path.is_absolute() else root / spec_path
    spec = accept.read(spec_path)
    found = accept.check(spec, root / member["new"], root=root)
    return spec, spec_path, found


def _said(result: dict) -> str:
    """One failed predicate in words, with where its bound came from."""
    if result.get("why"):
        return result["why"]
    side = result["bound"]["side"]
    return (
        f"{result['id']}: {result['measure']} is {result['value']:g}, past its "
        f"{side} of {result[side]:g}, a bound that does not say where it came from"
    )


def sheet(
    members: list[dict],
    *,
    out: str | Path,
    root: str | Path = ".",
) -> dict:
    """The family on one picture: old beside new at the size shown, and what failed.

    Each member is a row: the old artefact where there is one, the new one, and the
    capture crop where one is given (`capture`: a path, and `box` to crop it), each at
    `shown` — the size the game draws it — or its own. Under the row, every failed
    predicate in words with its bound's origin. The answer carries the same words and
    the choices, so an agent can put the question without opening the picture.
    """
    from PIL import Image, ImageDraw

    here = Path(root).resolve()
    rows, said = [], []
    for member in members:
        _, _, found = _checked(member, here)
        tiles = []
        for key in ("old", "new"):
            if member.get(key):
                tiles.append(Image.open(here / member[key]).convert("RGBA"))
        if member.get("capture"):
            shot = Image.open(here / member["capture"]).convert("RGBA")
            tiles.append(shot.crop(tuple(member["box"])) if member.get("box") else shot)
        if member.get("shown"):
            size = tuple(int(v) for v in member["shown"])
            tiles = [t.resize(size, Image.Resampling.LANCZOS) for t in tiles]
        failed = [_said(r) for r in found["predicates"] if not r["passed"]]
        lines = [f"{member['name']}: " + ("passes" if found["passed"] else "fails")]
        lines += [f"  {one}" for one in failed]
        rows.append((tiles, lines))
        said.append(
            {"name": member["name"], "passed": found["passed"], "failed": failed}
        )

    gap, line = 8, 14
    width = max(
        max(sum(t.width + gap for t in tiles) for tiles, _ in rows),
        max(6 * len(text) for _, lines in rows for text in lines),
    )
    height = sum(max((t.height for t in tiles), default=0) + gap for tiles, _ in rows)
    height += sum(line * len(lines) + gap for _, lines in rows) + line * 4
    canvas = Image.new("RGBA", (width + 2 * gap, height + gap), (40, 40, 40, 255))
    draw = ImageDraw.Draw(canvas)
    y = gap
    for tiles, lines in rows:
        x = gap
        for tile in tiles:
            canvas.alpha_composite(tile, (x, y))
            x += tile.width + gap
        y += max((t.height for t in tiles), default=0) + gap
        for text in lines:
            draw.text((gap, y), text, fill=(235, 235, 235, 255))
            y += line
        y += gap
    for word, meaning in CHOICES.items():
        draw.text((gap, y), f"{word}: {meaning}", fill=(255, 210, 90, 255))
        y += line
    where = Path(out) if Path(out).is_absolute() else here / out
    where.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(where)
    return {"sheet": str(where), "members": said, "choices": dict(CHOICES)}


def sitting(
    families: dict[str, list[dict]],
    *,
    out: str | Path,
    root: str | Path = ".",
) -> dict:
    """Every pending family's sheet in one folder, so a person looks once (§PW110).

    `loop.pending` says which assets wait; the caller groups them into families with
    their members, and this lays each out as `<out>/<family>.png`. The answers come
    back as one `judge` call per family.
    """
    folder = Path(out)
    sheets = {
        name: sheet(members, out=folder / f"{name}.png", root=root)
        for name, members in families.items()
    }
    return {
        "sheets": sheets,
        "says": f"{len(sheets)} famil{'y' if len(sheets) == 1 else 'ies'} to look at "
        f"in one sitting, each answered with judge(<members>, <choice>, <why>)",
    }


def judge(
    members: list[dict],
    choice: str,
    why: str,
    *,
    root: str | Path = ".",
    run: dict | None = None,
    named: tuple[str, ...] | list[str] = (),
    when: str | None = None,
) -> dict:
    """What a person said of a family, carried into the ledger and the spec.

    `choice` is one of `CHOICES` and `why` their sentence. Each member's verdict goes
    into `run` (an open `loop.start`) with its check, and `named` — the predicates the
    person blamed, for a `look` — where a member carries them. On `number`, every bound
    that failed is rewritten to the value measured, with origin `person`, the date and
    the sentence: the person has accepted the look at that value.
    """
    if choice not in CHOICES:
        raise PolyweaveError(
            "loop.unknown-choice",
            f"{choice!r} is not something a person says of a family here",
            f"say one of {', '.join(CHOICES)}",
        )
    if not str(why).strip():
        raise PolyweaveError(
            "loop.no-reason",
            "a verdict came with no sentence",
            "pass the person's own words as `why`; a verdict nobody can read again is "
            "one nobody can learn from",
        )
    here = Path(root).resolve()
    checked = [(member, *_checked(member, here)) for member in members]
    carried = {r["id"] for *_, found in checked for r in found["predicates"]}
    unknown = sorted(set(named) - carried)
    if unknown:
        raise PolyweaveError(
            "loop.unknown-predicate",
            f"the verdict names {', '.join(unknown)}, which no member's spec carries",
            "name predicates from: " + ", ".join(sorted(carried)),
        )
    accepted = choice != "look"
    if choice == "number" and all(found["passed"] for *_, found in checked):
        raise PolyweaveError(
            "loop.no-failed-bound",
            "every member passes, so no bound is wrong for refusing the look",
            "say accept; a bound that passed a look the person rejects is named with "
            "look and named=",
        )
    stamp = when or Date.today().isoformat()
    answers = []
    for member, _spec, spec_path, found in checked:
        mine = [n for n in named if n in {r["id"] for r in found["predicates"]}]
        if run is not None:
            loop.judged(
                run,
                tool_passed=found["passed"],
                person_accepted=accepted,
                why=f"{member['name']}: {why}",
                check=found,
                named=mine,
            )
        rewritten: list[str] = []
        if choice == "number" and not found["passed"]:
            rewritten = calibrate.apply(
                spec_path,
                {"apply": _moved(found, why, stamp)},
                root=here,
                person=True,
            )["written"]
        answers.append(
            {
                "name": member["name"],
                "tool_passed": found["passed"],
                "person_accepted": accepted,
                "named": mine,
                "rewritten": rewritten,
            }
        )
    return {
        "choice": choice,
        "why": why,
        "members": answers,
        # Said rather than left out: a verdict with no run open never reached the
        # ledger, and the caller should know that before assuming it did.
        "ledger": "recorded in the open run"
        if run is not None
        else "not recorded: no run was open; pass run= from loop.start",
    }


def _moved(found: dict, why: str, stamp: str) -> dict:
    """Each failed bound moved to the value a person accepted, rounded outward."""
    out: dict = {}
    for result in found["predicates"]:
        if result["passed"]:
            continue
        side = result["bound"]["side"]
        value = float(result["value"])
        out.setdefault(result["id"], {})[side] = {
            "value": calibrate.placed(value, 0.0, side),
            "origin": "person",
            "measured": round(value, 6),
            "date": stamp,
            "why": why,
            "old": result[side],
        }
    return out
