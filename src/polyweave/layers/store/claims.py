"""What a narration claims, the evidence behind it and who reviewed it (§PW716).

A storyboard beat carried a source URL, and nothing tied a spoken date, version or
figure to the evidence for it, so each revision researched again, and a 2021 Gutenberg
demonstration shown over a 2018 launch read as proof of the date. A `*.claims.toml`
declares each claim beside the cut that speaks it:

```toml
[[claim]]
id = "gutenberg-launch"
says = "Gutenberg shipped with WordPress 5.0"
kind = "fact"                 # fact, statistic, conclusion or footage
voice = 3                     # the cut's voice line that says it; footage: clip = 4
words = "WordPress 5.0"       # the words it rests on, found in the line's timed words
source = "https://wordpress.org/news/2018/12/bebo/"
excerpt = "WordPress 5.0 ... the new block editor"   # or note, for a conclusion
happened_on = 2018-12-06      # the event; footage also gives published_on, its own date
published_on = 2018-12-06
retrieved_on = 2026-11-20
review_by = 2027-05-20        # a statistic's: past it, the review has expired

[claim.review]                # written on a person's word, never inferred from a URL
by = "Ana"
on = 2026-11-21
verdict = "approved"          # or rejected
fingerprint = "3fa9..."       # the claim's, as video.claims answered it when reviewed
```

`video.claims` reads it against the cut: each claim's moment in the cut, its
fingerprint (its own fields and the bytes of the voice or clip it is anchored in), and
its status. Edited narration or evidence makes an approved claim `stale`, a statistic
past `review_by` is `expired`, and nothing is approved that no person approved.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import tomllib
from pathlib import Path
from typing import Annotated, Any

from polyweave.kernel import provenance
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

KINDS = ("fact", "statistic", "conclusion", "footage")
VERDICTS = ("approved", "rejected")
_KEYS = {"id", "says", "kind", "voice", "words", "clip", "source", "excerpt", "note",
         "happened_on", "published_on", "retrieved_on", "review_by", "review"}
_REVIEW_KEYS = {"by", "on", "verdict", "fingerprint", "note"}
#: What each kind must state: a date it happened, its source's own date, or a deadline.
_NEEDS = {"fact": ("happened_on",), "statistic": ("published_on", "review_by"),
          "conclusion": (), "footage": ("happened_on", "published_on")}


def _bad(message: str, remedy: str, **extra: Any) -> PolyweaveError:
    return PolyweaveError("video.bad-claims", message, remedy, **extra)


def _read(source: Path) -> list[dict]:
    if not source.is_file():
        raise PolyweaveError("video.no-source", f"there is no claims file at {source}",
                             "name a *.claims.toml under the project",
                             given=str(source))
    try:
        declared = tomllib.loads(source.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise PolyweaveError("video.no-source", f"{source.name} is not TOML: {exc}",
                             "fix the line the detail names",
                             given=str(source)) from exc
    claims, seen = [], set()
    for n, one in enumerate(declared.get("claim", []), 1):
        at = f"claim[{n}]"
        stray = sorted(set(one) - _KEYS)
        short = [k for k in ("id", "says", "kind") if not one.get(k)]
        if stray or short:
            raise _bad(f"{at} " + (f"has no {stray[0]}" if stray
                                   else f"names no {', '.join(short)}"),
                       f"a claim takes {', '.join(sorted(_KEYS))}", at=at)
        if one["id"] in seen or one["kind"] not in KINDS:
            raise _bad(f"{at} is {one['id']!r} of kind {one['kind']!r}",
                       f"give each claim its own id, and a kind of {', '.join(KINDS)}",
                       at=at, given="id" if one["id"] in seen else "kind")
        seen.add(one["id"])
        anchor = "clip" if one["kind"] == "footage" else "voice"
        missing = [k for k in _NEEDS[one["kind"]] if not one.get(k)]
        if not isinstance(one.get(anchor), int) or one[anchor] < 1:
            missing.insert(0, anchor)
        if not one.get("source") and not one.get("note"):
            missing.append("source or note")
        if str(one.get("source", "")).startswith("http") and not (
                one.get("excerpt") or one.get("note")) or (
                one.get("source") and not one.get("retrieved_on")):
            missing.append("excerpt and retrieved_on")
        if missing:
            raise _bad(f"{at} ({one['kind']}) names no {', '.join(missing)}",
                       f"a {one['kind']} needs {anchor} (its place in the cut), "
                       + ", ".join([*_NEEDS[one["kind"]], "a source with its excerpt "
                                    "and retrieved_on, or a note"]), at=at,
                       given=missing[0])
        review = one.get("review")
        if review is not None and (
                not isinstance(review, dict) or set(review) - _REVIEW_KEYS
                or review.get("verdict") not in VERDICTS
                or not all(review.get(k) for k in ("by", "on", "fingerprint"))):
            raise _bad(f"{at}.review is {review!r}",
                       "a review is a person's: by, on, verdict (approved or "
                       "rejected) and the fingerprint they reviewed", at=at,
                       given="review")
        claims.append(one)
    return claims


def _cut(cut: Path | None) -> tuple[list[dict], list[dict]]:
    """The cut's voice lines and clips as declared, read without probing a file."""
    if cut is None:
        return [], []
    try:
        declared = tomllib.loads(cut.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise PolyweaveError("video.no-source", f"{cut} is not a cut it can read",
                             "name the *.cut.toml that speaks these claims",
                             detail=str(exc)[:300]) from exc
    return declared.get("voice", []), declared.get("clip", [])


def _digest(path: Path) -> str | None:
    return provenance.sha256_of(path)[0] if path.is_file() else None


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[\w']+", text)]


def _spoken(voice: dict, words: str, here: Path) -> tuple[float | None, str]:
    """Seconds into its line the words begin, and how that was found."""
    file = here / str(voice.get("file", ""))
    kept = file.with_name(file.name + ".words.json")
    try:
        timed = json.loads(kept.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, "untimed"
    if timed.get("sha256") != _digest(file):
        return None, "untimed"
    heard = [(t, w) for w in timed.get("words", []) for t in _tokens(w.get("word", ""))]
    wanted = _tokens(words)
    for i in range(len(heard) - len(wanted) + 1):
        if wanted and [t for t, _ in heard[i:i + len(wanted)]] == wanted:
            return float(heard[i][1].get("start") or 0.0), "timed"
    return None, "unheard"


def _clip_at(clips: list[dict], n: int) -> float:
    """Seconds into the cut clip `n` begins, its fade included."""
    at = 0.0
    for k, clip in enumerate(clips[:n], 1):
        at -= float(clip.get("fade_in", 0.0))
        if k == n:
            return max(0.0, at)
        at += float(clip.get("length", 0.0))
    return at


def _judged(one: dict, voices: list, clips: list, here: Path,
            today: _dt.date) -> dict:
    """One claim's moment, fingerprint and status."""
    anchor = "clip" if one["kind"] == "footage" else "voice"
    rows = clips if anchor == "clip" else voices
    n, at, how, file = one[anchor], None, "uncut", None
    if rows:
        if n > len(rows):
            how = "absent"
        elif anchor == "clip":
            row = rows[n - 1]
            named = next((row[k] for k in ("video", "still", "from") if k in row), "")
            file, at, how = here / str(named), _clip_at(rows, n), "clip"
        else:
            row = rows[n - 1]
            file = here / str(row.get("file", ""))
            start, how = (0.0, "line")
            if one.get("words"):
                start, how = _spoken(row, str(one["words"]), here)
            at = float(row.get("at", 0.0)) + start if start is not None else None
    stated = {k: (str(v) if isinstance(v, _dt.date) else v)
              for k, v in one.items() if k != "review"}
    fingerprint = hashlib.sha256(json.dumps(
        {"claim": stated, "anchored": _digest(file) if file else None},
        sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    review = one.get("review")
    deadline = one.get("review_by")
    if how in ("absent", "unheard"):
        status = "unanchored"
    elif isinstance(deadline, _dt.date) and deadline < today:
        status = "expired"
    elif review is None:
        status = "unreviewed"
    elif review["verdict"] == "rejected":
        status = "rejected"
    elif review["fingerprint"] != fingerprint:
        status = "stale"
    else:
        status = "approved"
    return {"id": one["id"], "kind": one["kind"], "says": one["says"],
            f"{anchor}": n, **({"words": one["words"]} if one.get("words") else {}),
            "at": round(at, 2) if at is not None else None, "anchored": how,
            **{k: str(one[k]) for k in ("source", "excerpt", "note", "happened_on",
                                         "published_on", "retrieved_on", "review_by")
               if one.get(k)},
            "fingerprint": fingerprint, "status": status,
            **({"reviewed": {"by": review["by"], "on": str(review["on"]),
                             "verdict": review["verdict"]}} if review else {})}


def _page(rows: list[dict], name: str) -> str:
    """The claims laid out for a person to review, in the order the cut says them."""
    lines = [f"# Claims in {name}", "",
             "Approve or reject each by its fingerprint; nothing is approved for you.",
             ""]
    for one in rows:
        at = f"{one['at']:.1f}s" if one["at"] is not None else "not placed"
        lines += [f"## {one['id']} ({one['kind']}, {at}): {one['status']}", "",
                  f"> {one['says']}", ""]
        lines += [f"- {key.replace('_', ' ')}: {one[key]}"
                  for key in ("words", "source", "excerpt", "note", "happened_on",
                              "published_on", "retrieved_on", "review_by")
                  if one.get(key)]
        lines += [f"- fingerprint: `{one['fingerprint']}`", ""]
    return "\n".join(lines)


@operation("video.claims")
def claims(
    path: Annotated[str, Param("the *.claims.toml, as a path under the project")],
    *,
    cut: Annotated[str, Param("the *.cut.toml that speaks them, to anchor each")] = "",
    out: Annotated[str, Param("where a Markdown review page is written, if anywhere")
                   ] = "",
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Read a narration's claims against their evidence, anchors and reviews (§PW716).

    Each claim is answered in the cut's order with the second its words are spoken
    (from the voice line's `.words.json`, or the clip's start for footage), its
    `fingerprint` (its fields and the bytes of the line or clip it rests on) and its
    `status`: approved, unreviewed, rejected, stale (edited since its review), expired
    (a statistic past `review_by`) or unanchored (its words or place not found).
    `citations` are the approved claims' sources, for store.description's `cited`.
    """
    from polyweave.kernel.config import load

    here = load(root).root
    source = Path(path) if Path(path).is_absolute() else here / path
    if not source.name.endswith(".claims.toml"):
        raise _bad(f"the claims file is {source.name}", "name it <name>.claims.toml",
                   given="path")
    declared = _read(source)
    where = (Path(cut) if Path(cut).is_absolute() else here / cut) if cut else None
    voices, clips = _cut(where)
    today = _dt.date.today()
    rows = sorted((_judged(one, voices, clips, here, today) for one in declared),
                  key=lambda r: (r["at"] is None, r["at"] or 0.0))
    counts: dict[str, int] = {}
    for one in rows:
        counts[one["status"]] = counts.get(one["status"], 0) + 1
    citations = list(dict.fromkeys(
        f"{one['source']} ({one.get('published_on') or one.get('retrieved_on')})"
        for one in rows if one["status"] == "approved"
        and str(one.get("source", "")).startswith("http")))
    if out:
        target = here / out
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_page(rows, source.name), encoding="utf-8", newline="\n")
    waiting = len(rows) - counts.get("approved", 0)
    return {"claims": rows, "counts": counts, "citations": citations,
            "passed": waiting == 0,
            **({"page": provenance.relative(here / out, here)} if out else {}),
            "says": (f"all {len(rows)} claims approved" if not waiting else
                     f"{waiting} of {len(rows)} claims wait on a person: "
                     + ", ".join(f"{v} {k}" for k, v in sorted(counts.items())
                                 if k != "approved"))}
