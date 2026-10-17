"""A reference video's transcription, checked by a person row by row (§PW383).

Before a level is written from a gameplay video (Spinhold, RK178), the agent writes a
sheet of what it read (per stretch: the second, the side, the count, the formation, how
it ends) and the owner checks it, because a wrong count is cheapest to fix there. The
sheet was free prose: its rows did not say which frames they were read from, and the
owner's corrections lived in a conversation.

A transcription is now a file the agent writes, JSON or TOML: the `frames` folder it was
read from, the `columns` the project reads, and `rows`, each with an `id`, the seconds
`from` and `to` it covers, and the `frames` (by file name) or the `tracks` (by id, from
`reference.objects`) that support it. `reference.transcription` checks every row cites
what exists, records the sheet against the frames, and lays a sitting out: one card a
row, its cited frames side by side beside its values. The person answers each row on
the review page: right, or wrong (or unsure) with the right value in their words, kept
beside the sheet with when, through `verdict.judge`. `reference.transcribed` says which
rows are answered and what was corrected, and the sheet counts as accepted only when
every row has a person's answer. The agent never accepts its own reading.
"""

from __future__ import annotations

import json
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from polyweave.kernel import provenance
from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

from .reference_objects import _manifest

#: The most frames a row's card shows side by side, and each one's width.
SHOWN, WIDE = 6, 320


def _bad(what: str, remedy: str, **extra: Any) -> PolyweaveError:
    return PolyweaveError("capture.bad-transcription", what, remedy, **extra)


def read(sheet: Path) -> dict:
    """The sheet as written, JSON or TOML."""
    try:
        text = sheet.read_text(encoding="utf-8-sig")
        return tomllib.loads(text) if sheet.suffix == ".toml" else json.loads(text)
    except (OSError, ValueError) as exc:  # a TOMLDecodeError is a ValueError
        raise _bad(f"{sheet.name} is not readable as a transcription",
                   "write it as JSON or TOML with frames, columns and rows",
                   detail=str(exc)) from exc


def checked(written: dict, here: Path) -> tuple[Path, list, dict]:
    """The frames folder, the columns and each row with the frame files it cites."""
    if not isinstance(written, dict):
        raise _bad("the transcription is not a table", "write frames, columns and rows")
    manifest, listed = _manifest(str(written.get("frames", "")), here)
    files = {one["file"]: one["ms"] / 1000 for one in listed.get("frames", [])}
    columns = written.get("columns")
    if not isinstance(columns, list) or not all(isinstance(c, str) for c in columns):
        raise _bad("columns is not a list of names", "name each column the rows hold")
    tracks: dict[int, list] = {}
    objects = manifest.parent / "objects.json"
    if objects.is_file():
        for track in json.loads(objects.read_text(encoding="utf-8"))["tracks"]:
            tracks[int(track["id"])] = [at for at, *_ in track["path"]]
    by_second = {at: file for file, at in files.items()}
    rows, seen = written.get("rows"), {}
    if not isinstance(rows, list) or not rows:
        raise _bad("the transcription has no rows", "write one row a stretch you read")
    for index, row in enumerate(rows):
        where = f"row {index + 1}"
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise _bad(f"{where} has no id", "give each row an id, a word")
        if row["id"] in seen:
            raise _bad(f"two rows are {row['id']!r}", "give each row its own id")
        span = (row.get("from"), row.get("to"))
        if not (all(isinstance(v, int | float) for v in span) and span[0] <= span[1]):
            raise _bad(f"{where} ({row['id']}) has no span",
                       "give it from and to, in seconds, from no later than to")
        lacking = [c for c in columns if c not in row]
        if lacking:
            raise _bad(f"{where} ({row['id']}) lacks {', '.join(lacking)}",
                       "give every row a value for every column")
        cited = list(row.get("frames") or [])
        missing = [f for f in cited if f not in files]
        if missing:
            raise _bad(f"{where} ({row['id']}) cites {missing[0]}, which is not a "
                       "frame there", "cite frames by their file name in frames.json",
                       given=missing[0])
        for number in row.get("tracks") or []:
            if int(number) not in tracks:
                raise _bad(f"{where} ({row['id']}) cites track {number}, which "
                           "objects.json does not hold",
                           "run reference.objects first, or cite frames")
            cited += [by_second[at] for at in tracks[int(number)] if at in by_second]
        if not cited:
            raise _bad(f"{where} ({row['id']}) cites no frame and no track",
                       "cite the frames or tracks the row was read from")
        seen[row["id"]] = sorted(set(cited), key=lambda f: files[f])
    return manifest, columns, seen


def _card(folder: Path, cited: list, target: Path) -> Path:
    """A row's cited frames side by side, evenly picked where there are more."""
    from PIL import Image as Pil
    from PIL import ImageDraw, ImageFont

    step = max(1, -(-len(cited) // SHOWN))
    chosen = cited[::step][:SHOWN]
    font = ImageFont.load_default(size=14)
    tiles = []
    for file in chosen:
        with Pil.open(folder / file) as frame:
            image = frame.convert("RGB")
        tile = image.resize((WIDE, max(1, round(image.height * WIDE / image.width))))
        ImageDraw.Draw(tile).text((4, 2), file, fill=(255, 220, 90), font=font)
        tiles.append(tile)
    tall = max(t.height for t in tiles)
    card = Pil.new("RGB", (WIDE * len(tiles), tall), (20, 20, 20))
    for i, tile in enumerate(tiles):
        card.paste(tile, (i * WIDE, 0))
    target.parent.mkdir(parents=True, exist_ok=True)
    card.save(target)
    return target


def _answers_of(sheet: Path) -> Path:
    return sheet.with_name(sheet.stem + ".answers.jsonl")


def judged(member: dict, *, accepted: bool, choice: str, why: str, when: str,
           root: Path) -> dict:
    """A person's answer on one row, kept beside the sheet with when (§PW383)."""
    held = member["transcription"]
    sheet = Path(held["sheet"])
    sheet = sheet if sheet.is_absolute() else root / sheet
    line = {"row": held["row"], "choice": choice, "accepted": accepted, "why": why,
            "when": when, "at": datetime.now(tz=UTC).isoformat(timespec="seconds")}
    with _answers_of(sheet).open("a", encoding="utf-8", newline="\n") as out:
        out.write(json.dumps(line, ensure_ascii=False) + "\n")
    return line


@operation("reference.transcription")
def transcription(
    sheet: Annotated[
        str, Param("the transcription file, JSON or TOML, under the project")
    ],
    *,
    out: Annotated[
        str, Param("the folder the sitting is laid out in; review/<sheet> if empty")
    ] = "",
    root: Annotated[str, Param("the project the sheet is under")] = ".",
) -> dict:
    """A transcription read from a reference video, laid out for a person row by row.

    Every row must cite frames, or reference.objects tracks, that exist; the sheet is
    recorded against the frames, and a sitting holds one card a row, its frames side by
    side beside its values. The person answers each row on the review page; the agent
    never accepts its own reading. reference.transcribed reads the answers back.
    """
    from polyweave.loop import verdict

    config = load(root)
    here = config.root
    where = Path(sheet) if Path(sheet).is_absolute() else here / sheet
    if not where.is_file():
        raise _bad(f"there is no transcription at {sheet}",
                   "name the file the agent wrote, under the project")
    written = read(where)
    manifest, columns, rows = checked(written, here)
    work = Path(config.get("paths.work"))
    folder = Path(out) if out else work / "review" / where.stem
    folder = folder if folder.is_absolute() else here / folder
    families, abouts, sheets = {}, {}, {}
    stated = {row["id"]: row for row in written["rows"]}
    for row_id, cited in rows.items():
        card = _card(manifest.parent, cited, folder / "rows" / f"{row_id}.png")
        members = [{"name": row_id, "new": provenance.relative(card, here),
                    "transcription": {"sheet": provenance.relative(where, here),
                                      "row": row_id}}]
        families[row_id] = members
        row = stated[row_id]
        abouts[row_id] = (f"{row['from']:g}–{row['to']:g} s: " + ", ".join(
            f"{c} {row[c]}" for c in columns))
        sheets[row_id] = verdict.sheet(members, out=folder / f"{row_id}.png", root=here)
    verdict._manifest(folder, families, sheets, here, kind="transcription",
                      abouts=abouts)
    provenance.write(provenance.build(
        "capture", where, engine={"name": "reference.transcription"},
        inputs=[provenance.source("frames", manifest, root=here)],
        params={"columns": columns, "rows": len(rows)}, root=here,
    ), here)
    return {
        "sitting": provenance.relative(folder / verdict.MANIFEST, here),
        "rows": len(rows),
        "says": f"{len(rows)} rows laid out with their frames; the person answers each "
        "on the review page, and reference.transcribed reads what they said",
    }


@operation("reference.transcribed")
def transcribed(
    sheet: Annotated[
        str, Param("the transcription file the sitting was laid out from")
    ],
    *,
    root: Annotated[str, Param("the project the sheet is under")] = ".",
) -> dict:
    """Which rows of a transcription a person answered, and what they corrected.

    Each row's latest answer: right, or wrong with the person's words. The sheet is
    accepted only when every row has an answer and none is wrong.
    """
    here = load(root).root
    where = Path(sheet) if Path(sheet).is_absolute() else here / sheet
    rows = [row["id"] for row in read(where).get("rows", [])]
    latest: dict[str, dict] = {}
    answers = _answers_of(where)
    if answers.is_file():
        for line in answers.read_text(encoding="utf-8").splitlines():
            if line.strip():
                one = json.loads(line)
                latest[one["row"]] = one
    unanswered = [r for r in rows if r not in latest]
    corrected = [{"row": r, "why": latest[r]["why"], "when": latest[r]["when"]}
                 for r in rows if r in latest and not latest[r]["accepted"]]
    return {
        "rows": len(rows),
        "answered": len(rows) - len(unanswered),
        "unanswered": unanswered,
        "corrected": corrected,
        "accepted": not unanswered and not corrected,
    }
