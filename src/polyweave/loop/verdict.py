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
from typing import Annotated, Any

from polyweave.kernel.describe import Param, operation
from polyweave.kernel.doors import Blank, door
from polyweave.kernel.errors import PolyweaveError
from polyweave.kernel.layer import judge_of, judges

from . import accept, calibrate, loop, person

#: What a person can say of a family, and what each one means for the spec.
CHOICES = {
    "accept": "the look is right and the spec agrees with it",
    "look": "the look is wrong: the renders go back, the bounds stay",
    "number": "the look is right and a bound that failed it is wrong: it moves to "
    "what was measured, as the person's",
}

#: The choices for a family no spec holds (§PW338): nothing agreed or failed it, so
#: nothing speaks of a spec, and no bound is there to move.
UNHELD_CHOICES = {
    "accept": "the look is right",
    "look": "the look is wrong: it goes back to be made again",
}


def _checked(member: dict, root: Path) -> tuple[accept.Spec | None, Path | None, dict]:
    if not member.get("spec"):
        # A picture the gate refused has no acceptance spec: what the tool said of it
        # is the gate's verdict, which the member carries (§PW175).
        # A picture with no spec was measured against nothing, so nothing failed it:
        # only a gate's own refusal, which the member says, fails it (§PW291). And
        # nothing passed it either: with no gate's word it is unheld, not passed
        # (§PW338).
        if "passed" in member:
            return None, None, {"passed": bool(member["passed"]), "predicates": []}
        return None, None, {"passed": None, "checked": False, "predicates": []}
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
    "canon, the style family an accepted picture joins, motion, a loop to play, and "
    "model, a .glb to turn"
)

#: What a member's `motion` may be: a short muted loop the review page plays (§PW600).
MOTION = (".mp4", ".webm")


def members_of(members: Any) -> list[dict]:
    """Every member as a table, checked before any picture is opened (§PW261).

    A bare path is the commonest first guess at a member, and it is read as the
    picture it names, shown with no spec. Anything else that is not a table with a
    `name`, and a `new` unless it is a line of text, is refused with its index.
    """
    if not isinstance(members, list | tuple):
        raise PolyweaveError(
            "verdict.bad-member",
            f"members is a {type(members).__name__}, and it is a list",
            f"pass a list; {MEMBERS}",
        )
    found = []
    for index, member in enumerate(members):
        if isinstance(member, str) and member.strip():
            # Nothing checked it, so nothing failed it: the ear or the eye alone judges.
            found.append({"name": Path(member).stem, "new": member})
            continue
        if not isinstance(member, dict):
            said = f"is a {type(member).__name__}"
        else:
            # A line of text laid out by words.sheet has no picture to be new.
            needed = ("name",) if member.get("line") else ("name", "new")
            lacking = [key for key in needed if not member.get(key)]
            said = f"has no {' or '.join(lacking)}" if lacking else ""
            # A look that moves is a loop the page plays, beside its still (§PW600).
            moving = str(member.get("motion") or "")
            if moving and not said and Path(moving).suffix.lower() not in MOTION:
                said = f"names motion {moving}, which is not a {' or '.join(MOTION)}"
            # A model is turned on the page beside its still (§PW601).
            shaped = str(member.get("model") or "")
            if shaped and not said and Path(shaped).suffix.lower() != ".glb":
                said = f"names model {shaped}, which is not a .glb"
        if said:
            raise PolyweaveError(
                "verdict.bad-member",
                f"member {index} {said}",
                f"write each member as a table or a picture's path; {MEMBERS}",
                at=f"members[{index}]",
            )
        found.append(member)
    return found


def _from_git(members: list[dict], here: Path) -> list[dict]:
    """Each member whose `old` names a committed version, `<rev>:<path>` as
    sound.sitting reads it, with that version checked out into the work area and where
    it came from kept as `old_from`; and each picture a member names, there (§PW481)."""
    from polyweave.kernel import git
    from polyweave.kernel.config import load

    out = []
    for member in members:
        committed = git.committed(str(member["old"])) if member.get("old") else None
        if committed:
            landed, came = git.checked_out(*committed, here,
                                           load(here).path("paths.work"),
                                           kind="picture", code="verdict.no-old")
            member = {**member, "old": landed, "old_from": came}
        for key in ("old", "new", "capture"):
            if member.get(key) and not (here / str(member[key])).is_file():
                raise PolyweaveError(
                    "verdict.bad-member",
                    f"{member.get('name')}'s {key} names {member[key]}, which is not a "
                    "file",
                    "name a picture under the project, or a committed one as "
                    "HEAD:<path>",
                    given=str(member[key]),
                )
        out.append(member)
    return out


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
    members = _from_git(members_of(members), here)
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
        held = found["passed"] is not None
        state = ("passes" if found["passed"] else "fails") if held else (
            "nothing holds it: no spec measured it")
        lines = [f"{member['name']}: {state}", *[f"  {one}" for one in failed]]
        rows.append((tiles, lines))
        said.append(
            {"name": member["name"], "passed": found["passed"], "checked": held,
             "failed": failed,
             **({"old_from": member["old_from"]} if member.get("old_from") else {})}
        )
    # A family nothing holds is offered no choice that speaks of a spec (§PW338).
    offered = CHOICES if any(one["checked"] for one in said) else UNHELD_CHOICES

    gap, line = 8, 14
    # Every line is measured with the font that draws it, the choices under the rows
    # included: a choice cut off at the sheet's edge is one a person is never offered
    # (§PW182), and a guess at a character's width is what cut them off.
    measuring = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    choices = [f"{word}: {meaning}" for word, meaning in offered.items()]
    texts = [text for _, lines in rows for text in lines] + choices
    width = max(
        max(sum(t.width + gap for t in tiles) for tiles, _ in rows),
        max(int(measuring.textlength(text)) + gap for text in texts),
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
    for word, meaning in offered.items():
        draw.text((gap, y), f"{word}: {meaning}", fill=(255, 210, 90, 255))
        y += line
    where = Path(out) if Path(out).is_absolute() else here / out
    where.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(where)
    return {"sheet": str(where), "members": said, "choices": dict(offered)}


@operation("verdict.sitting")
def sitting(
    families: Annotated[
        dict, Param("each family's name to its members, as for a sheet")
    ],
    *,
    out: Annotated[str, Param("the folder every family's sheet is written into")],
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
    about: Annotated[str, Param("what the person should know, under the summary")] = "",
    asset: Annotated[
        str, Param("the loop ledger's asset the sitting answers for, as port.run's "
                   "family is named")
    ] = "",
) -> dict:
    """Every pending family's sheet in one folder, so a person looks once (§PW110).

    `loop.pending` says which assets wait; the caller groups them into families with
    their members, and this lays each out as `<out>/<family>.png`. The answers come
    back as one `judge` call per family. With `asset`, an answer given on the page is
    a verdict in the ledger for that asset too, as one given in conversation is
    (§PW465).
    """
    if not isinstance(families, dict):
        raise PolyweaveError(
            "verdict.bad-member",
            f"families is a {type(families).__name__}, and it maps a name to members",
            f'pass {{"<family>": [<member>, ...]}}; {MEMBERS}',
        )
    # Every family checked before any sheet is drawn, so a bad one is refused whole, and
    # a committed old checked out, so the page shows the picture it names (§PW481).
    here = Path(root).resolve()
    families = {name: _with_model(_from_git(members_of(one), here), here)
                for name, one in families.items()}
    folder = Path(out)
    sheets = {
        name: sheet(members, out=folder / f"{name}.png", root=root)
        for name, members in families.items()
    }
    # A sitting nothing holds is put to the person in words that claim no spec
    # (§PW338).
    held = any(one["checked"] for laid in sheets.values() for one in laid["members"])
    listed = _manifest(folder, families, sheets, root, about=about,
                       kind="look" if held else "unheld", asset=asset)
    return {
        "sheets": sheets,
        "manifest": listed,
        # Where the review page opens this sitting alone (§PW459), after the address
        # `python -m polyweave review` prints: what a person is linked to, and what a
        # screenshot before handing over should show.
        "page": address(listed),
        "says": f"{len(sheets)} famil{'y' if len(sheets) == 1 else 'ies'} to look at "
        f"in one sitting, at {address(listed)} on the review page, each answered with "
        "judge(<members>, <choice>, <why>)",
    }


def _with_model(members: list[dict], here: Path) -> list[dict]:
    """Each member whose still's record names a .glb it was drawn from, carrying it as
    `model`, so the page turns it beside the still (§PW601). A member naming its own, or
    with no record or no model in it, is left as it is."""
    from polyweave.kernel import provenance

    found = []
    for member in members:
        if member.get("model") or not member.get("new"):
            found.append(member)
            continue
        try:
            record = provenance.read(str(member["new"]), root=str(here))
        except PolyweaveError:
            found.append(member)
            continue
        drawn = next((one["path"] for one in record.get("inputs") or ()
                      if str(one.get("path", "")).lower().endswith(".glb")
                      and (here / one["path"]).is_file()), None)
        found.append({**member, "model": drawn} if drawn else member)
    return found


def address(manifest: str) -> str:
    """The path the review page opens one sitting at, by its manifest (§PW459)."""
    from urllib.parse import quote

    return f"/?sitting={quote(manifest, safe='')}"


#: What a sitting leaves beside its sheets, so the page can put it in front of a person
#: and answer it with the members it was laid out from (§PW172).
MANIFEST = "sitting.json"


def _manifest(
    folder: Path, families: dict, sheets: dict, root, kind: str = "look",
    about: str = "", abouts: dict | None = None, tone: list | None = None,
    asset: str = "", pick: tuple = (),
) -> str:
    """The sitting as data, and its place in the project's index of sittings.

    Answers the manifest as the index lists it, which is what the page opens it by.

    `kind` is what is judged, a look, a line, an effect or a sound, and says the words
    the page offers (§PW199): each choice with what it means and what it leads to, and
    a summary of the sitting, in the project's `[review] language` (§PW287). `about` is
    what only the caller knows, added under the summary; `abouts` one family's. A family
    named in `pick` holds alternatives for one slot, `"pick": "one"`: an accept of it
    names the one member chosen, and the page offers no batch accept of it (§PW547).
    """
    import json
    from datetime import UTC, datetime

    from polyweave.kernel.config import load
    from polyweave.kernel.files import read_text_retrying, write_atomic
    from polyweave.kernel.provenance import relative

    from . import review_text

    config = load(root)
    here = config.root
    where = folder if folder.is_absolute() else here / folder
    abouts = abouts or {}
    manifest = {
        # To the microsecond, as an answer is: an answer counts from the moment its
        # sitting was laid out, and one in the same second must fall on the right side.
        "at": datetime.now(tz=UTC).isoformat(timespec="microseconds"),
        **review_text.told(kind, review_text.language(here), about),
        **({"tone": list(tone)} if tone else {}),
        # The ledger's asset the page's answers are recorded against (§PW465).
        **({"asset": str(asset)} if asset else {}),
        "families": {
            name: {
                "members": list(members),
                "sheet": relative(Path(sheets[name]["sheet"]), here),
                "said": sheets[name]["members"],
                **({"about": abouts[name]} if abouts.get(name) else {}),
                **({"pick": "one"} if name in pick else {}),
            }
            for name, members in families.items()
        },
    }
    write_atomic(where / MANIFEST, json.dumps(manifest, indent=2) + "\n")
    index = config.path("paths.work") / "sittings.json"
    held = json.loads(read_text_retrying(index) or "[]")
    mine = relative(where / MANIFEST, here)
    write_atomic(
        index, json.dumps([*[h for h in held if h != mine], mine], indent=2) + "\n"
    )
    return mine


#: What `code` is, on each door that can accept a look (§PW443).
CODE = (
    "the code the review page shows for the sitting, as the person said it; an accept "
    "from conversation needs it"
)


def _judges() -> dict:
    """Where each kind of member's verdict is kept, by the key it is reported under."""
    return {"judges": {name: one.about for name, one in sorted(judges().items())}}


@operation("verdict.judge", guard=person.judging, declares=_judges)
def judge(
    members: Annotated[list, Param(MEMBERS)],
    choice: Annotated[
        str, Param("what the person said of the family", choices=tuple(CHOICES))
    ],
    why: Annotated[str, Param("the person's own sentence, as they said it")],
    *,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
    run: Annotated[dict, Param("the open loop run the verdict is recorded in")] = None,
    asset: Annotated[
        str, Param("with no run: the asset a run is opened and closed for, here")
    ] = None,
    named: Annotated[list, Param("the predicates the person blamed, for look")] = (),
    when: Annotated[str, Param("the date of the verdict; today where empty")] = "",
    code: Annotated[str, Param(CODE)] = "",
) -> dict:
    """What a person said of a family, carried into the ledger and the spec.

    With no `run`, `asset` opens one for that asset, records the verdict and closes
    it, so a verdict given in a conversation lands in the ledger in one call (§PW332).
    Called as a tool, an `accept` or `number` needs `code`, the one the review page
    shows for a sitting laying out these members (§PW443): only a person accepts a look.

    `choice` is one of `CHOICES` and `why` their sentence. Each member's verdict goes
    into `run` (an open `loop.start`) with its check, and `named` — the predicates the
    person blamed, for a `look` — where a member carries them. On `number`, every bound
    that failed is rewritten to the value measured, with origin `person`, the date and
    the sentence: the person has accepted the look at that value.

    A member carrying `canon` names a style family, and on a verdict that accepts the
    look its `new` picture joins that family's canon, with this verdict on its record
    (§PW166). This is the only door into a canon. A member carrying `line`, laid out by
    `words.sheet`, is a line of text, and its verdict goes into the lines canon. One
    carrying `sound`, laid out by `sound.sitting`, has its verdict kept in its record.
    """
    members = members_of(members)
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
    # Each member's judge, settled before anything is written: two that claim one
    # member are refused here, not after the ledger already holds the verdict (§PW501).
    judging = [judge_of(member) for member in members]
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
    if choice == "number" and any(spec is None for _, spec, *_ in checked):
        raise PolyweaveError(
            "loop.no-failed-bound",
            "a member has no acceptance spec, so there is no bound for number to move",
            "say accept to overrule the gate that refused it; the tolerance that did "
            "is the project's, in [tolerance]",
        )
    stamp = when or Date.today().isoformat()
    opened = run is None and bool(asset)
    if opened:
        run = loop.judging(str(asset), root=str(here))
    answers = []
    for (member, _spec, spec_path, found), judge in zip(checked, judging, strict=True):
        mine = [n for n in named if n in {r["id"] for r in found["predicates"]}]
        if run is not None:
            loop.judged(
                run,
                tool_passed=found["passed"],
                person_accepted=accepted,
                why=f"{member['name']}: {why}",
                check=found,
                named=mine,
                root=str(here),
                member=member["name"],
            )
        rewritten: list[str] = []
        if choice == "number" and not found["passed"]:
            rewritten = calibrate.apply(
                spec_path,
                {"apply": _moved(found, why, stamp)},
                root=here,
                person=True,
            )["written"]
        # What the member's own layer kept of the verdict, under its judge's name: a
        # picture's canon, a line's, a transcription row, a sound's record (§PW501).
        kept = {}
        if judge is not None:
            kept[judge.name] = judge.judged(
                member, accepted=accepted, choice=choice, why=why, when=stamp,
                root=here,
            )
        answers.append(
            {
                "name": member["name"],
                "tool_passed": found["passed"],
                "person_accepted": accepted,
                "named": mine,
                "rewritten": rewritten,
                **kept,
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
    if opened:
        loop.finish(run, root=str(here))
    return {
        "choice": choice,
        "why": why,
        "members": answers,
        # Said rather than left out: a verdict with no run open never reached the
        # ledger, and the caller should know that before assuming it did.
        "ledger": f"recorded in a run opened and closed for {asset}"
        if opened
        else "recorded in the open run"
        if run is not None
        else "not recorded: no run was open; pass run= from loop.start, or asset=",
    }


@operation("verdict.promote", guard=person.promoting)
def promote(
    gate: Annotated[str, Param("the gate run the picture was refused in, by its id")],
    picture: Annotated[str, Param("the refused picture, as the gate run lists it")],
    why: Annotated[str, Param("the person's own sentence, as they said it")],
    *,
    canon: Annotated[
        str, Param("a style family it joins too, if the person said so")
    ] = None,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
    code: Annotated[
        str, Param("the code the review page shows above its lanes, as the person "
                   "said it")
    ] = "",
) -> dict:
    """A refused picture a person accepted after all, from wherever they said it.

    The same write the review page's refused lane makes (§PW175), for a verdict given
    in conversation (§PW265): a `judge` whose record says the tool refused what the
    person accepted, appended to the answers, which is what `mesh.buy` reads before it
    models from the picture. A gate or picture the project has no record of is refused
    with the ones it has. Called as a tool it needs `code`, the one the page shows above
    its lanes (§PW443).
    """
    from . import review

    body = {"gate": gate, "picture": picture, "choice": "accept", "why": why}
    if canon:
        body["canon"] = canon
    return review.answer(root, body)


#: Where every answer given on the review page lands, one line each, appended and never
#: rewritten, so it is the simplest thing an agent can wait on (§PW173).
ANSWERS = "answers.jsonl"


def record_answer(
    said: dict, *, sitting: str, family: str, root, marks: list | None = None,
    chosen: str = "", moments: list | None = None, views: list | None = None,
) -> dict:
    """Append one answer from the page, for the agent that offered the sitting.

    `marks` are where the person said it is wrong, each a mask the size of the picture
    it was drawn on, with that picture's digest (§PW174). `chosen` is the member a
    person picked of a family of alternatives, the others passed over (§PW547).
    `moments` are when a loop is wrong, seconds into it (§PW600); `views` where a model
    is, as the camera that saw it (§PW601).
    """
    import json
    from datetime import UTC, datetime

    from polyweave.kernel.config import load

    line = {
        "at": datetime.now(tz=UTC).isoformat(timespec="microseconds"),
        "sitting": sitting,
        "family": family,
        "choice": said["choice"],
        "why": said["why"],
        "members": said["members"],
        "marks": list(marks or ()),
        **({"chosen": chosen} if chosen else {}),
        **({"moments": list(moments)} if moments else {}),
        **({"views": list(views)} if views else {}),
    }
    path = load(root).path("paths.work") / ANSWERS
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as appended:
        appended.write(json.dumps(line, sort_keys=True) + "\n")
    return line


def kept_answers(root) -> list[dict]:
    """Every answer kept, each naming its sitting where it is now (§PW436).

    The file is append-only, so a sitting moved is a `moved` line from its old manifest
    to its new one, never a rewrite: an answer kept before the move is read as one for
    the sitting where it went, through any number of moves.
    """
    import json

    from polyweave.kernel.config import load
    from polyweave.kernel.files import read_text_retrying

    path = load(root).path("paths.work") / ANSWERS
    lines = [json.loads(line)
             for line in (read_text_retrying(path) or "").splitlines() if line.strip()]
    went = {one["moved"]["from"]: one["moved"]["to"] for one in lines if "moved" in one}

    def now(sitting: str) -> str:
        seen = set()
        while sitting in went and sitting not in seen:
            seen.add(sitting)
            sitting = went[sitting]
        return sitting

    return [{**one, "sitting": now(one["sitting"])} if "sitting" in one else one
            for one in lines if "moved" not in one]


def _when(stamp: str | None):
    from datetime import datetime

    try:
        return datetime.fromisoformat(str(stamp))
    except ValueError:
        return None


def answering(sitting: dict, answers: list[dict]) -> list[dict]:
    """The answers given to a sitting as it is laid out now (§PW615).

    A sitting laid again in its folder keeps its manifest's path, so the answers to the
    members it held before were read as answers to the new ones, and a sitting nobody
    had looked at read as finished. An answer counts from the moment the sitting was
    laid out; one with no time, from before answers kept one, still counts.
    """
    laid = _when(sitting.get("at"))

    def counts(one: dict) -> bool:
        given = _when(one.get("at")) if one.get("at") else None
        return laid is None or given is None or given >= laid

    return [one for one in answers
            if one.get("sitting") == sitting.get("manifest") and counts(one)]


def unanswered(sitting: dict, answers: list[dict]) -> list[str]:
    """The families of a sitting nothing has answered since it was laid out."""
    done = {one.get("family") for one in answering(sitting, answers)}
    return [name for name in sitting.get("families") or {} if name not in done]


@operation("verdict.move")
def move(
    sitting: Annotated[
        str, Param("the sitting, as its manifest or the folder the page lists it in")
    ],
    to: Annotated[str, Param("the folder it moves to, under the project, not there")],
    *,
    root: Annotated[str, Param("the project the sitting belongs to")] = ".",
) -> dict:
    """Move a sitting laid out in the wrong folder, its answers with it (§PW436).

    The folder moves; the paths inside its manifest and its row in the index are
    rewritten; and one `moved` line is appended to the answers, which stay append-only,
    so every answer given before reads as one for the sitting where it is now. A target
    that exists, lies outside the project or inside the sitting itself is refused.
    """
    import json
    import shutil

    from polyweave.kernel.config import load
    from polyweave.kernel.files import read_text_retrying, write_atomic
    from polyweave.kernel.provenance import relative

    from . import review

    config = load(root)
    here = config.root
    listed = sitting.replace("\\", "/").rstrip("/")
    if not listed.endswith(MANIFEST):
        listed = f"{listed}/{MANIFEST}"
    offered = {one["manifest"] for one in review.sittings(here)}
    if listed not in offered:
        raise PolyweaveError(
            "loop.unknown-sitting",
            f"{sitting!r} is not a sitting this project laid out",
            "name a sitting the review page lists",
            given=sitting,
            allowed=sorted(offered),
        )
    old = (here / listed).parent
    target = (here / to).resolve() if not Path(to).is_absolute() else Path(to).resolve()
    try:
        target.relative_to(here.resolve())
    except ValueError:
        raise PolyweaveError(
            "verdict.bad-move", f"{to} is outside the project",
            "move it to a folder under the project, such as art/review/<name>",
            given=to) from None
    if target.exists():
        raise PolyweaveError(
            "verdict.bad-move", f"{relative(target, here)} is already there",
            "name a folder that does not exist yet", given=to)
    if target.is_relative_to(old.resolve()):
        raise PolyweaveError(
            "verdict.bad-move", f"{to} is inside the sitting it would move",
            "name a folder beside it, not within it", given=to)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(old), str(target))
    was, now = relative(old, here), relative(target, here)

    def moved(value):
        if isinstance(value, str):
            inside = value == was or value.startswith(was + "/")
            return now + value[len(was):] if inside else value
        if isinstance(value, list):
            return [moved(one) for one in value]
        if isinstance(value, dict):
            return {key: moved(one) for key, one in value.items()}
        return value

    manifest = target / MANIFEST
    write_atomic(manifest, json.dumps(
        moved(json.loads(manifest.read_text(encoding="utf-8"))), indent=2) + "\n")
    landed = relative(manifest, here)
    index = config.path("paths.work") / "sittings.json"
    held = json.loads(read_text_retrying(index) or "[]")
    write_atomic(index, json.dumps(
        [landed if one == listed else one for one in held], indent=2) + "\n")
    from datetime import UTC, datetime

    answers_path = config.path("paths.work") / ANSWERS
    answers_path.parent.mkdir(parents=True, exist_ok=True)
    with answers_path.open("a", encoding="utf-8") as appended:
        appended.write(json.dumps({
            "at": datetime.now(tz=UTC).isoformat(timespec="microseconds"),
            "moved": {"from": listed, "to": landed}}, sort_keys=True) + "\n")
    carried = sum(1 for one in kept_answers(here) if one.get("sitting") == landed)
    return {"from": listed, "to": landed, "answers": carried,
            "says": f"moved to {now}; {carried} answer(s) given there before read as "
            "this sitting's"}


@operation("verdict.place")
def place(
    sitting: Annotated[str, Param("the sitting's manifest or folder")],
    member: Annotated[str, Param("the accepted member's name")],
    to: Annotated[str, Param("where the game loads it, under the project")],
    *,
    root: Annotated[str, Param("the project the sitting belongs to")] = ".",
) -> dict:
    """Put an accepted member where the game loads it, with its own record (§PW549).

    Refused unless a person accepted it. The copy's record keeps the member's own, adds
    the member and the verdict, and names the copy's path, so verify checks the game's
    file. Placing again replaces both.
    """
    import json
    import shutil

    from polyweave.kernel import provenance
    from polyweave.kernel.config import load

    from . import review

    config = load(root)
    here = config.root
    listed = sitting.replace("\\", "/").rstrip("/")
    if not listed.endswith(MANIFEST):
        listed = f"{listed}/{MANIFEST}"
    offered = {one["manifest"]: one for one in review.sittings(here)}
    if listed not in offered:
        raise PolyweaveError(
            "loop.unknown-sitting",
            f"{sitting!r} is not a sitting this project laid out",
            "name a sitting the review page lists",
            given=sitting,
            allowed=sorted(offered),
        )
    found = {str(one["name"]): one for laid in offered[listed]["families"].values()
             for one in laid["members"]}
    if member not in found or not found[member].get("new"):
        raise PolyweaveError(
            "verdict.bad-member",
            f"the sitting has no member {member!r} with a file to place",
            "name a member the sitting laid out",
            given=member,
            allowed=sorted(found),
        )
    take = here / str(found[member]["new"])
    landed = (here / to).resolve() if not Path(to).is_absolute() else Path(to).resolve()
    try:
        landed.relative_to(here.resolve())
    except ValueError:
        raise PolyweaveError(
            "verdict.bad-place", f"{to} is outside the project",
            "name the path under the project the game loads it from",
            given=to) from None
    if landed == take.resolve():
        raise PolyweaveError(
            "verdict.bad-place", f"{to} is the member itself",
            "name the path the game loads it from, apart from the review copy",
            given=to)
    accepted = _accepted(take, member, listed, here)
    if accepted is None:
        raise PolyweaveError(
            "verdict.unaccepted",
            f"no person has accepted {member} in {listed}",
            "let a person accept it on the review page first; an agent does not "
            "choose what the game ships",
            given=member,
        )
    landed.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(take, landed)
    try:
        own = provenance.read(str(take), root=here)
    except PolyweaveError:
        own = None
    placed = provenance.source("placed", take, root=here)
    if own:
        digest, length = provenance.sha256_of(landed)
        record = {**json.loads(json.dumps(own)),
                  "artefact": {"path": provenance.relative(landed, here),
                               "sha256": digest, "bytes": length}}
        record["inputs"] = [*(own.get("inputs") or ()), placed]
    else:
        record = provenance.build("borrow", landed, engine={"name": "verdict.place"},
                                  inputs=[placed], root=here)
    record["placed"] = {"from": placed["path"], "sitting": listed, "verdict": accepted}
    written = provenance.write(record, here)
    at = provenance.relative(landed, here)
    return {"placed": at, "record": provenance.relative(written, here),
            "from": placed["path"], "verdict": accepted,
            "says": f"{member} placed at {at}, its record naming its own path and the "
            "take it came from"}


def _accepted(take: Path, member: str, listed: str, here: Path) -> dict | None:
    """The verdict that accepted `member`: its record's last on these bytes, or where it
    has none the latest answer naming it; None where neither is an accept (§PW549)."""
    from polyweave.kernel import provenance

    try:
        own = provenance.read(str(take), root=here)
    except PolyweaveError:
        own = {}
    digest = provenance.sha256_of(take)[0]
    said = [v for v in own.get("verdicts") or () if v.get("sha256") == digest]
    if said:
        last = said[-1]
        return ({"choice": "accept", "why": last.get("why"), "at": last.get("at")}
                if last.get("choice") == "accept" else None)
    from . import review

    laid = next((one for one in review.sittings(here) if one["manifest"] == listed),
                {"manifest": listed})
    named = [(one, kept) for one in answering(laid, kept_answers(here))
             for kept in one.get("members") or () if kept.get("name") == member]
    if not named or not named[-1][1].get("person_accepted"):
        return None
    one = named[-1][0]
    return {"choice": one["choice"], "why": one.get("why"), "at": one.get("at")}


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
    from polyweave.kernel.config import load

    path = load(root).path("paths.work") / ANSWERS
    held = kept_answers(root)
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
                    member=member["name"],
                )
    return {
        "answers": fresh,
        "latest": fresh[-1]["at"] if fresh else str(since),
        "file": str(path),
        "run": run,
    }


@operation("verdict.answer", guard=person.answering)
def answer(
    sitting: Annotated[
        str, Param("the sitting, as its manifest or the folder the page lists it in")
    ],
    choice: Annotated[
        str, Param("what the person said of it", choices=tuple(CHOICES))
    ],
    why: Annotated[str, Param("the person's own sentence, as they said it")],
    *,
    family: Annotated[str, Param("one family; every family where empty")] = "",
    member: Annotated[str, Param("the alternative picked")] = "",
    root: Annotated[str, Param("the project the sitting belongs to")] = ".",
    code: Annotated[str, Param(CODE)] = "",
) -> dict:
    """A verdict a person gave in conversation, answering a sitting by name (§PW375).

    The page's own write, run for the family named or every family of the sitting, so
    the ledger, the spec and `verdict.answers` take it as they take a click. A family
    already answered is skipped and named, not judged twice. Called as a tool, an
    `accept` or `number` needs `code`, the one the page shows for the sitting (§PW443).
    An accept of a family of alternatives names `member`, the one picked (§PW547).
    """

    from polyweave.kernel.config import load

    from . import review

    if not str(why).strip():
        # The page keeps a silent click as one; a sentence carried from chat has words.
        raise PolyweaveError(
            "loop.no-reason",
            "a verdict carried from conversation came with no sentence",
            "pass the person's own words as `why`, as they said them",
        )
    config = load(root)
    listed = sitting.replace("\\", "/").rstrip("/")
    if not listed.endswith(MANIFEST):
        listed = f"{listed}/{MANIFEST}"
    offered = {one["manifest"]: one for one in review.sittings(config.root)}
    if listed not in offered:
        raise PolyweaveError(
            "loop.unknown-sitting",
            f"{sitting!r} is not a sitting this project laid out",
            "name a sitting the review page lists; verdict.sitting lays one out",
            given=sitting,
            allowed=sorted(offered),
        )
    families = list(offered[listed]["families"])
    if family and family not in families:
        raise PolyweaveError(
            "loop.unknown-sitting",
            f"the sitting has no family {family!r}",
            f"name one of {', '.join(sorted(families))}, or none for every family",
            given=family,
            allowed=sorted(families),
        )
    done = {one["family"]
            for one in answering(offered[listed], kept_answers(config.root))}
    answered, skipped = [], []
    for one in [family] if family else families:
        if one in done:
            skipped.append(one)
            continue
        said = review.answer(
            config.root,
            {"sitting": listed, "family": one, "choice": choice, "why": why,
             **({"member": member} if member else {})},
        )
        answered.append({"family": one, "members": said["members"]})
    return {"sitting": listed, "choice": choice, "why": why, "answered": answered,
            "skipped": skipped}


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
