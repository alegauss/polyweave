"""One still per declared beat, labelled with what is said and shown there (§PW708).

A video's review before a full render needs each shot's still at its exact time beside
the narration over it, its captions, the source interval it came from and its tags:
`reference.frames` samples one video at a rate and labels nothing. `video.sheet` takes
records, each a source (a video or a picture), the exact second to sample and the
editorial labels, writes each still and a portable HTML sheet that shows them in order,
and says for each whether it is a source's still or the composited output's.
"""

from __future__ import annotations

import html
import json
import shutil
import subprocess
from pathlib import Path
from typing import Annotated, Any

from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

from .video import _ffmpeg

#: What a still is of: a source before composition, or the composited output.
KINDS = ("source", "output")

#: The pictures a sample's source may be, taken as they are.
PICTURES = (".png", ".jpg", ".jpeg", ".webp")

_KEYS = {"source", "at", "label", "words", "captions", "interval", "tags", "kind"}


def _bad(message: str, remedy: str, **extra: Any) -> PolyweaveError:
    return PolyweaveError("video.bad-sheet", message, remedy, **extra)


def _checked(one: Any, n: int, here: Path) -> dict:
    at = f"samples[{n}]"
    if not isinstance(one, dict):
        raise _bad(f"{at} is not a record", "give each sample as {source, at, label}")
    stray = sorted(set(one) - _KEYS)
    if stray:
        raise _bad(f"{at} has {stray[0]!r}", f"use only {', '.join(sorted(_KEYS))}",
                   given=stray[0], allowed=sorted(_KEYS))
    source = here / str(one.get("source") or "")
    if not one.get("source") or not source.is_file():
        raise _bad(f"{at} names no source under the project",
                   "give source as a video or picture path", at=at)
    picture = source.suffix.lower() in PICTURES
    when = one.get("at", 0.0)
    if not picture and (isinstance(when, bool) or not isinstance(when, int | float)
                        or when < 0):
        raise _bad(f"{at}.at is {when!r}", "give at as seconds into the video, from 0",
                   at=at)
    kind = one.get("kind", "source")
    if kind not in KINDS:
        raise _bad(f"{at}.kind is {kind!r}", f"give kind as one of {', '.join(KINDS)}",
                   at=at, allowed=KINDS)
    return {**one, "source": source, "at": float(when), "kind": kind,
            "picture": picture}


def _still(sample: dict, target: Path) -> bool:
    """The sample's frame at its exact time, or its picture as it is."""
    if sample["picture"]:
        shutil.copyfile(sample["source"], target.with_suffix(sample["source"].suffix))
        return True
    done = subprocess.run(
        [_ffmpeg(), "-v", "error", "-y", "-i", str(sample["source"]), "-ss",
         f"{sample['at']:.3f}", "-frames:v", "1", str(target)],
        capture_output=True, check=False)
    return not done.returncode and target.is_file()


def _page(rows: list[dict], title: str) -> str:
    """The sheet as one HTML file that opens anywhere: stills beside their labels."""
    def text(value: Any) -> str:
        if isinstance(value, dict):
            return "; ".join(f"{k}: {v}" for k, v in value.items())
        if isinstance(value, list | tuple):
            return ", ".join(str(one) for one in value)
        return "" if value is None else str(value)

    cards = []
    for row in rows:
        facts = "".join(
            f"<dt>{html.escape(name)}</dt><dd>{html.escape(text(row.get(key)))}</dd>"
            for key, name in (("words", "said"), ("captions", "captions"),
                              ("interval", "source interval"), ("tags", "tags"))
            if row.get(key) not in (None, "", [], {}))
        picture = (f'<img src="{html.escape(row["still"])}" alt="">' if row["still"]
                   else '<p class="missing">no frame at this time</p>')
        cards.append(
            f'<figure class="{row["kind"]}">{picture}<figcaption>'
            f'<b>{html.escape(row["label"] or "")}</b> '
            f'<span>{html.escape(row["kind"])} · {html.escape(row["from"])} '
            f'@ {row["at"]:.3f}s</span><dl>{facts}</dl></figcaption></figure>')
    return (
        "<!doctype html><meta charset='utf-8'><title>" + html.escape(title) +
        "</title><style>body{font:14px system-ui,sans-serif;margin:16px;"
        "background:#fafafa;color:#111}main{display:grid;grid-template-columns:"
        "repeat(auto-fill,minmax(320px,1fr));gap:16px}figure{margin:0;background:#fff;"
        "border:1px solid #ddd;border-radius:6px;overflow:hidden}figure.output"
        "{border-color:#2563eb}img{width:100%;display:block}figcaption{padding:8px}"
        "span{color:#555;font-size:12px}dt{font-weight:600;margin-top:4px}dd{margin:0}"
        ".missing{padding:24px;color:#b91c1c}</style><h1>" + html.escape(title) +
        "</h1><main>" + "".join(cards) + "</main>\n")


@operation("video.sheet", kind="capture")
def sheet(
    samples: Annotated[
        list, Param("each {source, at, label, words, captions, interval, tags, kind}")
    ],
    out: Annotated[str, Param("the folder the stills and index.html are written to")],
    *,
    title: Annotated[str, Param("the sheet's heading")] = "Review sheet",
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """One still per declared beat, beside its narration and labels (§PW708).

    Each sample's `source` is a video, sampled at exactly `at` seconds, or a picture,
    taken as it is. `label`, `words` (the narration over it), `captions`, `interval`
    (the source stretch it came from) and `tags` (people, events, topics) are shown
    beside it, and `kind` says whether it is a `source` still or the composited
    `output`. The stills are numbered in order; `index.html` holds them with their
    labels and opens with no server; `sheet.json` lists the same. A time a video has no
    frame at is shown as missing, never as another frame.
    """
    from polyweave.kernel import provenance
    from polyweave.kernel.config import load

    here = load(root).root
    if not isinstance(samples, list) or not samples:
        raise _bad("no sample was given", "give samples, each {source, at, label}")
    checked = [_checked(one, n, here) for n, one in enumerate(samples)]
    folder = here / out
    folder.mkdir(parents=True, exist_ok=True)
    rows, missing = [], []
    for n, one in enumerate(checked, 1):
        target = folder / f"{n:03d}.png"
        made = _still(one, target)
        written = target.with_suffix(one["source"].suffix) if one["picture"] else target
        if not made:
            missing.append(n)
        rows.append({
            "n": n, "still": written.name if made else None,
            "from": provenance.relative(one["source"], here), "at": one["at"],
            "kind": one["kind"], "label": one.get("label", ""),
            **{k: one[k] for k in ("words", "captions", "interval", "tags")
               if k in one},
        })
    (folder / "index.html").write_text(_page(rows, title), encoding="utf-8",
                                       newline="\n")
    (folder / "sheet.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False)
                                       + "\n", encoding="utf-8", newline="\n")
    sources = sorted({one["source"] for one in checked})
    provenance.write(provenance.build(
        "capture", folder / "sheet.json", engine={"name": "video.sheet"},
        inputs=[provenance.source("source", one, here) for one in sources],
        params={"samples": len(rows), "title": title}, root=here), root=here)
    return {"sheet": provenance.relative(folder / "index.html", here),
            "stills": [row["still"] for row in rows], "missing": missing,
            "samples": len(rows)}
