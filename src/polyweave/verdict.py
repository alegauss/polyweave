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
from typing import Annotated

from . import accept, calibrate, loop, style
from .describe import Param, operation
from .doors import Blank, door
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


MEMBERS = (
    "each member: name, spec and new, and optionally old, capture with box, shown, "
    "and canon, the style family an accepted picture joins"
)


@operation("verdict.sheet")
def sheet(
    members: Annotated[list, Param(MEMBERS)],
    *,
    out: Annotated[str, Param("where the sheet is written, under the project")],
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
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


@operation("verdict.sitting")
def sitting(
    families: Annotated[
        dict, Param("each family's name to its members, as for a sheet")
    ],
    *,
    out: Annotated[str, Param("the folder every family's sheet is written into")],
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
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
    _manifest(folder, families, sheets, root)
    return {
        "sheets": sheets,
        "says": f"{len(sheets)} famil{'y' if len(sheets) == 1 else 'ies'} to look at "
        f"in one sitting, each answered with judge(<members>, <choice>, <why>)",
    }


#: What a sitting leaves beside its sheets, so the page can put it in front of a person
#: and answer it with the members it was laid out from (§PW172).
MANIFEST = "sitting.json"


def _manifest(folder: Path, families: dict, sheets: dict, root) -> None:
    """The sitting as data, and its place in the project's index of sittings."""
    import json
    from datetime import UTC, datetime

    from .config import load
    from .files import read_text_retrying, write_atomic
    from .provenance import relative

    config = load(root)
    here = config.root
    where = folder if folder.is_absolute() else here / folder
    manifest = {
        "at": datetime.now(tz=UTC).isoformat(timespec="seconds"),
        "families": {
            name: {
                "members": list(members),
                "sheet": relative(Path(sheets[name]["sheet"]), here),
                "said": sheets[name]["members"],
            }
            for name, members in families.items()
        },
        "choices": dict(CHOICES),
    }
    write_atomic(where / MANIFEST, json.dumps(manifest, indent=2) + "\n")
    index = config.path("paths.work") / "sittings.json"
    held = json.loads(read_text_retrying(index) or "[]")
    mine = relative(where / MANIFEST, here)
    write_atomic(
        index, json.dumps([*[h for h in held if h != mine], mine], indent=2) + "\n"
    )


@operation("verdict.judge")
def judge(
    members: Annotated[list, Param(MEMBERS)],
    choice: Annotated[
        str, Param("what the person said of the family", choices=tuple(CHOICES))
    ],
    why: Annotated[str, Param("the person's own sentence, as they said it")],
    *,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
    run: Annotated[dict, Param("the open loop run the verdict is recorded in")] = None,
    named: Annotated[list, Param("the predicates the person blamed, for look")] = (),
    when: Annotated[str, Param("the date of the verdict; today where empty")] = "",
) -> dict:
    """What a person said of a family, carried into the ledger and the spec.

    `choice` is one of `CHOICES` and `why` their sentence. Each member's verdict goes
    into `run` (an open `loop.start`) with its check, and `named` — the predicates the
    person blamed, for a `look` — where a member carries them. On `number`, every bound
    that failed is rewritten to the value measured, with origin `person`, the date and
    the sentence: the person has accepted the look at that value.

    A member carrying `canon` names a style family, and on a verdict that accepts the
    look its `new` picture joins that family's canon, with this verdict on its record
    (§PW166). This is the only door into a canon.
    """
    if choice not in CHOICES:
        raise PolyweaveError(
            "loop.unknown-choice",
            f"{choice!r} is not something a person says of a family here",
            f"say one of {', '.join(CHOICES)}",
            given=choice,
            allowed=CHOICES,
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
            given=unknown[0],
            allowed=carried,
        )
    accepted = choice != "look"
    if choice == "number" and all(found["passed"] for *_, found in checked):
        raise PolyweaveError(
            "loop.no-failed-bound",
            "every member passes, so no bound is wrong for refusing the look",
            "say accept; a bound that passed a look the person rejects is named with "
            "look and named=",
            call=door(
                "verdict.judge",
                members=members,
                choice="accept",
                why=Blank("the person's own words"),
            ),
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
        joined = None
        if accepted and member.get("canon"):
            joined = style.admit(
                member["new"],
                family=member["canon"],
                why=why,
                choice=choice,
                when=stamp,
                root=here,
            )
        answers.append(
            {
                "name": member["name"],
                "tool_passed": found["passed"],
                "person_accepted": accepted,
                "named": mine,
                "rewritten": rewritten,
                "canon": joined,
                # What the check said, as `loop.judged` takes it, so an answer given
                # where no run was open can still be carried into one (§PW173).
                "check": {
                    "predicates": [
                        {
                            "id": one["id"],
                            "value": one.get("value"),
                            "passed": bool(one.get("passed")),
                            "bound": {"side": (one.get("bound") or {}).get("side")},
                        }
                        for one in found["predicates"]
                    ]
                },
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


#: Where every answer given on the review page lands, one line each, appended and never
#: rewritten, so it is the simplest thing an agent can wait on (§PW173).
ANSWERS = "answers.jsonl"


def record_answer(said: dict, *, sitting: str, family: str, root) -> dict:
    """Append one answer from the page, for the agent that offered the sitting."""
    import json
    from datetime import UTC, datetime

    from .config import load

    line = {
        "at": datetime.now(tz=UTC).isoformat(timespec="microseconds"),
        "sitting": sitting,
        "family": family,
        "choice": said["choice"],
        "why": said["why"],
        "members": said["members"],
    }
    path = load(root).path("paths.work") / ANSWERS
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as appended:
        appended.write(json.dumps(line, sort_keys=True) + "\n")
    return line


@operation("verdict.answers")
def answers(
    since: Annotated[
        str, Param("the `latest` of the last read; everything if empty")
    ] = (""),
    *,
    run: Annotated[dict, Param("the open loop run to carry each answer into")] = None,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """The answers a person gave on the review page since a time, to resume from.

    Each carries the sitting, the family, the choice, the sentence and every member's
    verdict, so the agent resumes from what was said without re-reading the ledger.
    Given `run`, each member's verdict is also carried into it, as `judge` would have
    with a run open. Nothing is marked or moved: the next read passes `latest` as
    `since`, because a file two sessions both edit is a file they race on. The file is
    `[paths] work/answers.jsonl`, which a background wait can watch instead of polling.
    """
    import json

    from .config import load
    from .files import read_text_retrying

    path = load(root).path("paths.work") / ANSWERS
    held = [
        json.loads(line)
        for line in (read_text_retrying(path) or "").splitlines()
        if line.strip()
    ]
    fresh = [one for one in held if one["at"] > str(since)]
    if run is not None:
        for one in fresh:
            for member in one["members"]:
                loop.judged(
                    run,
                    tool_passed=member["tool_passed"],
                    person_accepted=member["person_accepted"],
                    why=f"{member['name']}: {one['why']}",
                    check=member.get("check"),
                    named=member.get("named") or (),
                )
    return {
        "answers": fresh,
        "latest": fresh[-1]["at"] if fresh else str(since),
        "file": str(path),
        "run": run,
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
