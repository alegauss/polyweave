"""The words layer's part of the brief: a line of the string table (§PW505)."""

from __future__ import annotations

from pathlib import Path

from . import words


def read(item: dict, record: dict, here: Path) -> dict:
    """A line of the string table: its text in each locale, who says it, its verdict."""
    from polyweave.kernel.config import load

    where, locales, table = words.table(here)
    key = item["id"][len("line:") :]
    row = next(one for one in table if one["key"] == key)
    sha = words._digest(row, locales)
    latest = [one for one in words.held(here) if one["key"] == key]
    verdict = latest[-1] if latest else None
    speaker = load(here).get("words.speaker")
    return {
        "path": item["declaration"],
        "key": key,
        "row": row["row"],
        "text": {locale: row["cells"].get(locale) or "" for locale in locales},
        "speaker": (row["cells"].get(speaker) or "").strip() or None,
        "verdict": None
        if verdict is None
        else {
            "approved": verdict.get("approved"),
            **verdict.get("verdict", {}),
            # A verdict on the line as it read then; false once the text moved.
            "on_this_text": verdict.get("sha256") == sha,
        },
    }
