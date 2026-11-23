"""A video's published description, from the credits its records hold (§PW711).

A platform bounds a description (YouTube at 5,000 characters) and the WordPress video's
ran to 15,791 because every credit was listed whole. `store.description` writes the text
from a summary, chapter times and the records of the files the video uses: a credit a
licence requires is kept whole, word for word, and the rest are grouped by the service
and licence they came under, with their authors. A text that cannot fit without
dropping a required credit is refused, never truncated, and a file whose licence no
record states is named, never given one.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated, Any

from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

_WATCH = re.compile(r"https?://(?:www\.)?youtube\.com/watch\?v=([\w-]{6,})[^\s)]*")


def _short(text: str) -> str:
    """A YouTube watch URL as its short form: the same link in fewer characters."""
    return _WATCH.sub(lambda m: f"https://youtu.be/{m.group(1)}", text)


def _clock(seconds: float) -> str:
    whole = int(seconds)
    hours, rest = divmod(whole, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def _chapters(chapters: Any) -> list[str]:
    if not chapters:
        return []
    if not isinstance(chapters, list) or not all(
            isinstance(c, dict) and isinstance(c.get("at"), int | float)
            and str(c.get("title") or "").strip() for c in chapters):
        raise PolyweaveError(
            "store.bad-chapters", "chapters are not {at, title} records",
            "give chapters as [{at = seconds, title = ...}]")
    times = [float(c["at"]) for c in chapters]
    if times[0] != 0 or any(b <= a for a, b in zip(times, times[1:], strict=False)):
        raise PolyweaveError(
            "store.bad-chapters", f"chapters start at {times[0]:g}s and run "
            f"{', '.join(f'{t:g}' for t in times)}",
            "start the first chapter at 0 and give each later one a later time")
    return [f"{_clock(c['at'])} {str(c['title']).strip()}" for c in chapters]


@operation("store.description")
def description(
    files: Annotated[list, Param("the files the video uses, under the project")],
    *,
    summary: Annotated[str, Param("what the video is, as its first paragraph")] = "",
    chapters: Annotated[list, Param("each {at, title}, the first at 0 seconds")] = None,
    limit: Annotated[int, Param("the platform's character limit", lo=1)] = 5000,
    out: Annotated[str, Param("where the text is written, if anywhere")] = None,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """A bounded description: summary, chapters and the credits the used files owe.

    A file whose record carries a `credit` (an attribution its licence requires) has it
    kept whole. The others are grouped under their service and licence, naming their
    authors once each. YouTube watch URLs are shortened. A file whose licence no record
    states is in `unstated` and left out, never given a licence. A text longer than
    `limit` is refused with its length and the required credits' share; nothing is cut.
    """
    from polyweave.kernel import provenance
    from polyweave.kernel.config import load

    here = load(root).root
    wanted = {provenance.relative(here / str(one), here) for one in files or ()}
    if not wanted:
        raise PolyweaveError("store.bad-chapters", "no file was named",
                             "give files, the media the video uses")
    listed = {one["file"]: one for one in provenance.credits(
        root=str(here), all=True).get("artefacts", [])}
    records = {record["artefact"]["path"]: record
               for _, record in provenance.own_records(here)}
    absent = sorted(wanted - set(records))
    required, grouped, unstated = [], {}, []
    for path in sorted(wanted & set(records)):
        record = records[path]
        if record.get("credit"):
            required.append(_short(str(record["credit"])))
            continue
        licence = (listed.get(path) or {}).get("licence") or record.get("licence")
        if not licence:
            unstated.append(path)
            continue
        service = (record.get("engine") or {}).get("name") or "made for this video"
        authors = grouped.setdefault((service, licence), [])
        author = str(record.get("author") or "").strip()
        if author and author not in authors:
            authors.append(author)
    lines = [summary.strip()] if summary.strip() else []
    stamps = _chapters(chapters)
    if stamps:
        lines += ["", *stamps]
    credits = [*required, *(
        f"{service} ({licence})" + (f": {', '.join(authors)}" if authors else "")
        for (service, licence), authors in sorted(grouped.items()))]
    if credits:
        lines += ["", "Credits:", *credits]
    text = "\n".join(lines).strip() + "\n"
    if len(text) > limit:
        owed = sum(len(one) + 1 for one in required)
        raise PolyweaveError(
            "store.description-long",
            f"the description is {len(text)} characters, past the {limit} allowed; "
            f"{owed} of them are credits a licence requires",
            "shorten the summary or the chapters, or use fewer files; no required "
            "credit is cut", given=len(text))
    if out:
        target = here / out
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
    return {"text": text, "characters": len(text), "limit": limit,
            "required": len(required), "grouped": len(grouped),
            "unstated": unstated, "unrecorded": absent,
            **({"file": provenance.relative(Path(here / out), here)} if out else {})}
