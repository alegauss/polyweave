"""The text a player reads, held to the world it is set in (§PW197).

Starship shows KEEPERS where its bible says Lattice, and nothing failed. Its text is
literals in GDScript and scenes, and a check that read those with a regular expression
would be a pattern about one project's code. So the contract is a string table: the game
reads its text through Godot's translation CSV with `tr()`, one key per row and one
column per locale, and `[words] table` names that file. A column whose header starts
with an underscore is one Godot skips; `[words] speaker` names the one that says who
speaks the line, as an entity id of the world (§PW196).

`words.check` holds every row, in every locale, to the world:

- every capitalised name is one the world shows (`[words] ordinary` lists the
  capitalised words that are not names, such as START on a title screen);
- no entity's code name reaches the screen;
- no line is longer than `[rules] longest_line`;
- a speaker the world calls silent has no line;
- a name the world keeps unshown never appears.

What it cannot see is a string still written into a scene. `words.unlisted` reports what
it can prove instead: every literal `text` in the project's `.tscn` files that is not a
key of the table, as a count and a list, so moving text into the table has a measure.

**Whether a line keeps the world's tone is a person's call** (§PW199). `words.sheet`
lays out the lines no verdict covers as a sitting on the review page, one family a line,
each beside the world's `[rules] tone` and what the canon holds of its speaker. The
answer goes through `verdict.judge`, which is the only writer of `[words] canon`: every
verdict is kept there, and the approved lines are the canon `world.read` gives a speaker
as examples.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import textwrap
from datetime import date as Date
from pathlib import Path
from typing import Annotated

from . import provenance
from .config import load
from .describe import Param, operation
from .errors import PolyweaveError
from .files import read_text_retrying, write_atomic
from .world import declared

_ROOT = Param("the project whose text this is")
_WORLD = Param("the *.world.toml; needed only where the project holds several")

#: A word as the checks read it: letters first, then letters, digits and apostrophes.
_WORD = re.compile(r"[^\W\d_][\w'’-]*")

#: What is not read as text: a `{placeholder}`, a `%s` and a `[b]` BBCode tag.
_MARKUP = re.compile(r"\{[^}]*\}|%[a-z]|\[/?[a-z_]+(?:=[^\]]*)?\]", re.I)

#: What ends a sentence, so the word after it may be capitalised without being a name.
_ENDS = ".!?:…"


def _words(text: str) -> list[str]:
    return [re.sub(r"['’]s$", "", w) for w in _WORD.findall(text)]


def _plain(text: str) -> str:
    return _MARKUP.sub(" ", text)


def _lines(text: str) -> list[str]:
    """The lines a player reads: a newline, or Godot's escaped one, breaks a line."""
    return _plain(text).replace("\\n", "\n").split("\n")


def _capitalised(text: str) -> list[str]:
    """The words written as names: capitalised mid-sentence, or in capitals anywhere."""
    found = []
    for match in _WORD.finditer(text):
        word = re.sub(r"['’]s$", "", match.group())
        if len(word) < 2 or not word[0].isupper():
            continue
        before = text[: match.start()].rstrip().rstrip("\"'“‘«(")
        opening = not before or before[-1] in _ENDS
        if word.isupper() or not opening:
            found.append(word)
    return found


def table(root: str | Path = ".") -> tuple[Path, list[str], list[dict]]:
    """The string table: where it is, its locales, and its rows with their CSV line."""
    config = load(root)
    if not config.get("words.table"):
        raise PolyweaveError(
            "words.no-table",
            "polyweave.toml names no string table, so there is no text to check",
            "move the player's text into Godot's translation CSV and set "
            "[words] table to its path",
        )
    where = config.path("words.table")
    text = read_text_retrying(where)
    if text is None:
        raise PolyweaveError(
            "words.unreadable-table",
            f"[words] table is {where}, and there is no file there",
            "write the translation CSV there, or correct [words] table",
        )
    reader = csv.reader(text.lstrip("\ufeff").splitlines())
    header = next(reader, None)
    if not header or len(header) < 2:
        raise PolyweaveError(
            "words.unreadable-table",
            f"{where.name} has no header naming a key column and a locale",
            "start it with a header row such as keys,en",
        )
    locales = [h for h in header[1:] if h and not h.startswith("_")]
    rows = []
    for row in reader:
        if not row or not row[0].strip():
            continue
        cells = dict(zip(header, row, strict=False))
        rows.append({"key": row[0], "row": reader.line_num, "cells": cells})
    return where, locales, rows


@operation("words.check")
def check(
    world: Annotated[str, _WORLD] = None,
    root: Annotated[str, _ROOT] = ".",
) -> dict:
    """Hold every line of the string table, in every locale, to the world's names and
    rules; each finding names the key, the locale and the rule."""
    config = load(root)
    where, locales, rows = table(root)
    source, entities, rules = declared(world, root)
    unshown = set(rules.get("unshown") or [])
    silent = set(rules.get("silent") or [])
    shown = {
        w.casefold()
        for i, e in entities.items()
        if i not in unshown
        for w in _words(e["name"])
    }
    hidden = {
        i: {w.casefold() for w in _words(entities[i]["name"])} - shown
        for i in unshown
        if i in entities
    }
    codes = {
        e["code"].casefold(): i
        for i, e in entities.items()
        if e["code"].casefold() not in shown
    }
    ordinary = {str(w).casefold() for w in config.get("words.ordinary")}
    longest = rules.get("longest_line")
    speaker = config.get("words.speaker")
    findings: list[dict] = []

    def found(error: PolyweaveError, row: dict, locale: str | None, rule: str) -> None:
        findings.append(
            {
                **error.as_dict(),
                "key": row["key"],
                "locale": locale,
                "rule": rule,
                "row": row["row"],
            }
        )

    for row in rows:
        said = (row["cells"].get(speaker) or "").strip()
        if said and said not in entities:
            found(
                PolyweaveError(
                    "words.unknown-speaker",
                    f"{row['key']} is spoken by {said!r}, which the world does not "
                    "declare",
                    f"name an entity id as its {speaker}, or declare [entity.{said}]",
                    given=said,
                    allowed=list(entities),
                ),
                row,
                None,
                "speaker",
            )
        elif said in silent:
            found(
                PolyweaveError(
                    "words.silent-speaks",
                    f"{row['key']} is spoken by {said}, who the world says never "
                    "speaks",
                    f"give the line to another speaker, or take {said} out of "
                    "[rules] silent",
                ),
                row,
                None,
                "silent",
            )
        for locale in locales:
            text = row["cells"].get(locale) or ""
            if text.strip():
                _held(text, row, locale, found, shown, hidden, codes, ordinary, longest)
    judged = verdicts(root)
    return {
        "table": provenance.relative(where, config.root),
        "world": provenance.relative(source, Path(root)),
        "locales": locales,
        "rows": len(rows),
        "passed": not findings,
        "findings": findings,
        # Whether a line sounds like the world is a person's call and never this
        # check's (§PW199): a line no verdict covers is named, and passes all the same.
        "unjudged": [
            r["key"] for r in rows if (r["key"], _digest(r, locales)) not in judged
        ],
    }


def _held(text, row, locale, found, shown, hidden, codes, ordinary, longest) -> None:
    """One locale's text of one row, against every rule that reads text."""
    plain = _plain(text)
    lowered = {w.casefold() for w in _words(plain)}
    for code in sorted(c for c in codes if c in lowered):
        found(
            PolyweaveError(
                "words.code-name",
                f"{row['key']} ({locale}) shows {code!r}, the code name of "
                f"{codes[code]}",
                "write the name a player reads instead, as the world declares it",
            ),
            row,
            locale,
            "code_names",
        )
    for ident, words in sorted(hidden.items()):
        if words & lowered:
            found(
                PolyweaveError(
                    "words.hidden-name",
                    f"{row['key']} ({locale}) names {ident}, whose name the world "
                    "keeps unshown",
                    "refer to it without its name, or take it out of [rules] unshown",
                ),
                row,
                locale,
                "unshown",
            )
    kept = set().union(*hidden.values()) | set(codes) | shown | ordinary
    for word in dict.fromkeys(_capitalised(plain)):
        if word.casefold() not in kept:
            found(
                PolyweaveError(
                    "words.unknown-name",
                    f"{row['key']} ({locale}) names {word!r}, which is no name the "
                    "world shows",
                    f"use the world's name for it; if {word} is not a name, add it to "
                    "[words] ordinary; if it is a new one, declare it in the world",
                    given=word,
                    allowed=sorted(shown),
                ),
                row,
                locale,
                "names",
            )
    if longest:
        for line in _lines(text):
            if len(line.strip()) > longest:
                found(
                    PolyweaveError(
                        "words.too-long",
                        f"{row['key']} ({locale}) has a line of {len(line.strip())} "
                        f"characters, and the world allows {longest}",
                        "shorten it or break it with \\n",
                    ),
                    row,
                    locale,
                    "longest_line",
                )


#: A `text` property in a scene file, with Godot's escapes inside the quotes.
_TEXT = re.compile(r'^text = "((?:[^"\\]|\\.)*)"', re.M | re.S)
_NODE = re.compile(r'^\[node name="([^"]*)"', re.M)


@operation("words.unlisted")
def unlisted(root: Annotated[str, _ROOT] = ".") -> dict:
    """The literal texts in the project's scenes that are not keys of the string table.

    This is what `words.check` cannot see, counted, so moving it has a measure."""
    here = load(root).root
    try:
        keys = {row["key"] for row in table(root)[2]}
    except PolyweaveError as refused:
        if refused.code != "words.no-table":
            raise
        keys = set()
    scenes = sorted(
        s
        for s in here.rglob("*.tscn")
        if not any(p.startswith(".") for p in s.relative_to(here).parts[:-1])
    )
    literals = []
    for scene in scenes:
        text = read_text_retrying(scene) or ""
        nodes = [(m.start(), m.group(1)) for m in _NODE.finditer(text)]
        for match in _TEXT.finditer(text):
            said = match.group(1)
            if not said.strip() or said in keys:
                continue
            node = next((n for at, n in reversed(nodes) if at < match.start()), None)
            literals.append(
                {
                    "scene": provenance.relative(scene, here),
                    "line": text.count("\n", 0, match.start()) + 1,
                    "node": node,
                    "text": said,
                }
            )
    return {"scenes": len(scenes), "count": len(literals), "literals": literals}


# -- a line's tone, judged by a person (§PW199) --------------------------------------

#: What a person can say of a line on the review page, in `verdict.judge`'s words.
LINE_CHOICES = {
    "accept": "the line sounds like the world: it joins the lines canon",
    "look": "it does not: say why, and it stays out of the canon",
}


def _digest(row: dict, locales: list[str]) -> str:
    """What a verdict on a line was given to: its text in every locale."""
    said = {locale: row["cells"].get(locale) or "" for locale in locales}
    text = json.dumps(said, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canon(root) -> Path | None:
    config = load(root)
    return config.path("words.canon") if config.get("words.canon") else None


def held(root=".") -> list[dict]:
    """Every verdict a person gave on a line, oldest first."""
    where = _canon(root)
    return json.loads(read_text_retrying(where) or "[]") if where else []


def verdicts(root=".") -> dict[tuple[str, str], dict]:
    """The latest verdict on each line as it read, by key and text digest."""
    return {(one["key"], one["sha256"]): one for one in held(root)}


def approved(speaker: str, root=".") -> list[dict]:
    """The lines a person approved for one speaker, which a new one starts from."""
    return [
        {"key": one["key"], "text": one["text"], "why": one["verdict"]["why"]}
        for one in verdicts(root).values()
        if one.get("speaker") == speaker and one.get("approved")
    ]


def judged(
    member: dict, *, accepted: bool, choice: str, why: str, when: str = "", root="."
) -> dict:
    """Keep a person's verdict on one line, and grow the canon by it.

    Called by `verdict.judge` and by nothing else, as `style.admit` is: an agent that
    could approve its own line would make its tone the world's.
    """
    where = _canon(root)
    if where is None:
        raise PolyweaveError(
            "words.no-canon",
            "polyweave.toml names no lines canon, so a verdict on a line has nowhere "
            "to be kept",
            "set [words] canon to a JSON file under the project",
        )
    entry = {
        "key": member["line"],
        "speaker": member.get("speaker"),
        "text": member["text"],
        "sha256": member["sha256"],
        "approved": bool(accepted),
        "verdict": {
            "choice": choice,
            "why": why,
            "when": when or Date.today().isoformat(),
        },
    }
    write_atomic(
        where, json.dumps([*held(root), entry], indent=2, sort_keys=True) + "\n"
    )
    return entry


@operation("words.sheet")
def sheet(
    out: Annotated[str, Param("the folder the sitting is laid out in")],
    examples: Annotated[
        int, Param("approved lines shown beside each, per speaker", lo=0, hi=12)
    ] = 3,
    world: Annotated[str, _WORLD] = None,
    root: Annotated[str, _ROOT] = ".",
) -> dict:
    """Put every line no verdict covers on the review page, one family a line.

    Each sheet shows the line in every locale, its speaker, the world's tone and the
    speaker's approved lines, and any rule `words.check` says it breaks. Lines are laid
    out by speaker. The person answers on the page: accept joins the canon, look keeps
    it out with their reason.
    """
    from . import verdict

    if _canon(root) is None:
        raise PolyweaveError(
            "words.no-canon",
            "polyweave.toml names no lines canon, so a verdict on a line has nowhere "
            "to be kept",
            "set [words] canon to a JSON file under the project, then lay out again",
        )
    config = load(root)
    _, locales, rows = table(root)
    _, entities, rules = declared(world, root)
    broken: dict[str, list[str]] = {}
    for found in check(world, root)["findings"]:
        broken.setdefault(found["key"], []).append(found["message"])
    judged_ = verdicts(root)
    column = config.get("words.speaker")
    pending = sorted(
        (r for r in rows if (r["key"], _digest(r, locales)) not in judged_),
        key=lambda r: ((r["cells"].get(column) or "").strip(), r["row"]),
    )
    folder = config.root / out
    families: dict = {}
    sheets: dict = {}
    for row in pending:
        speaker = (row["cells"].get(column) or "").strip() or None
        member = {
            "name": row["key"],
            "line": row["key"],
            "speaker": speaker,
            "text": {locale: row["cells"].get(locale) or "" for locale in locales},
            "sha256": _digest(row, locales),
            "passed": row["key"] not in broken,
        }
        name = re.sub(r"[^\w.-]", "_", f"{speaker or 'unspoken'}.{row['key']}")
        drawn = folder / f"{name}.png"
        shown = approved(speaker, root)[-examples:] if speaker and examples else []
        who = (entities.get(speaker) or {}).get("name") if speaker else None
        _draw(drawn, member, who, rules.get("tone") or [], shown, broken)
        families[name] = [member]
        sheets[name] = {
            "sheet": str(drawn),
            "members": [
                {
                    "name": row["key"],
                    "passed": member["passed"],
                    "failed": broken.get(row["key"], []),
                }
            ],
        }
    if families:
        verdict._manifest(folder, families, sheets, root, choices=LINE_CHOICES)
    return {
        "sitting": provenance.relative(folder / verdict.MANIFEST, config.root)
        if families
        else None,
        "lines": len(pending),
        "families": list(families),
        "choices": dict(LINE_CHOICES),
        "says": f"{len(pending)} line{'' if len(pending) == 1 else 's'} for a person "
        "to judge on the review page; verdict.answers resumes from what they said",
    }


def _draw(where: Path, member: dict, who, tone: list, shown: list, broken) -> None:
    """One line's sheet: the line, its speaker, the tone and the approved examples."""
    from PIL import Image, ImageDraw

    said = [f"{member['line']}, spoken by {who or member['speaker'] or 'nobody'}"]
    for locale, text in member["text"].items():
        said += textwrap.wrap(f"{locale}: {text}", 90) or [f"{locale}:"]
    if tone:
        said += ["", "The world's tone:"]
        said += [w for rule in tone for w in textwrap.wrap(f"- {rule}", 90)]
    if shown:
        said += ["", "Lines a person approved for this speaker:"]
        for one in shown:
            first = next(iter(one["text"].values()), "")
            said += textwrap.wrap(f"- {first}", 90)
    if broken.get(member["line"]):
        said += ["", "Rules it breaks:"]
        said += [w for m in broken[member["line"]] for w in textwrap.wrap(f"- {m}", 90)]
    said += [""] + [f"{word}: {meaning}" for word, meaning in LINE_CHOICES.items()]
    gap, line = 8, 16
    measuring = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    width = max(int(measuring.textlength(text)) for text in said) + 2 * gap
    canvas = Image.new("RGBA", (width, line * len(said) + 2 * gap), (40, 40, 40, 255))
    draw = ImageDraw.Draw(canvas)
    for index, text in enumerate(said):
        colour = (255, 210, 90, 255) if index >= len(said) - 2 else (235, 235, 235, 255)
        draw.text((gap, gap + index * line), text, fill=colour)
    where.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(where)
