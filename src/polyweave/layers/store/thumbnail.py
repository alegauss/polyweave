"""A thumbnail held to its title and to the size a feed shows it at (§PW699).

The Scion video's thumbnail said what its title already said, word for word, and was
only ever looked at full size; every channel guide read that day says a thumbnail adds
what the title leaves out, and a feed shows it at about 168x94. `store.thumbnail` reads
the text on a thumbnail, from the layout that drew it or off the picture by OCR, and
answers three things a person would otherwise check by eye: how many words it carries,
which meaningful words it shares with the title, and whether each line is still tall
enough and contrasted enough to read at feed size. Which thumbnail is better stays a
person's call.
"""

from __future__ import annotations

import shutil
import subprocess
import unicodedata
from typing import Annotated

import numpy as np

from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

#: Words that carry no meaning of their own, by language: shared with the title, they
#: are not repetition. Folded as the comparison folds them.
STOP = {
    "en": {"a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "at",
           "by", "is", "it", "its", "this", "that", "from", "as", "be", "was", "are",
           "how", "what", "why", "you", "your", "we", "our", "not", "no", "do", "per"},
    "pt": {"a", "o", "as", "os", "um", "uma", "uns", "umas", "de", "do", "da", "dos",
           "das", "e", "ou", "em", "no", "na", "nos", "nas", "por", "pelo", "pela",
           "para", "pra", "com", "sem", "que", "se", "ao", "aos", "eu", "voce", "nao",
           "seu", "sua", "isso", "este", "esta", "como", "mais", "mas", "foi"},
}

#: The size a feed shows a thumbnail at, and the least a line's letters may stand
#: there, in px, and the least contrast between its letters and what is behind them.
FEED = (168, 94)
TALLEST_NEEDED = 8.0
CONTRAST = 3.0

#: The least confidence, out of 100, a word read by OCR is kept at.
CONFIDENT = 60


def _fold(word: str) -> str:
    """A word as the comparison reads it: case and accents folded, so 'Não' meets
    'nao'; punctuation dropped."""
    plain = unicodedata.normalize("NFKD", word.casefold())
    return "".join(c for c in plain if c.isalnum())


def _meaningful(text: str, language: str) -> list[str]:
    stop = STOP.get(language.split("-")[0].lower(), set()) | STOP["en"]
    words = [_fold(one) for one in text.split()]
    return [one for one in words if one and (one.isdigit() or (len(one) > 1
                                                              and one not in stop))]


def _read(path, engine: str, language: str) -> list[dict]:
    """The lines OCR reads off the picture, each with its box, from tesseract's TSV."""
    done = subprocess.run(  # noqa: S603 - the engine is the project's own binary
        [engine, str(path), "stdout", "-l", language, "tsv"],
        capture_output=True, text=True, encoding="utf-8", timeout=120, check=False,
    )
    if done.returncode != 0:
        raise PolyweaveError(
            "fetch.ocr-failed", f"the OCR engine could not read {path}",
            f"check that the {language} language data is installed for it",
            detail=(done.stderr or "")[:400],
        )
    lines: dict[tuple, dict] = {}
    for row in done.stdout.splitlines()[1:]:
        cells = row.split("\t")
        if len(cells) < 12 or not cells[11].strip():
            continue
        try:
            confidence = float(cells[10])
        except ValueError:
            continue
        if confidence < CONFIDENT:
            continue
        key = tuple(cells[2:5])
        left, top, width, height = (int(v) for v in cells[6:10])
        one = lines.setdefault(key, {"text": [], "box": [left, top, left + width,
                                                          top + height]})
        one["text"].append(cells[11].strip())
        box = one["box"]
        one["box"] = [min(box[0], left), min(box[1], top),
                      max(box[2], left + width), max(box[3], top + height)]
    return [{"text": " ".join(one["text"]), "box": one["box"]}
            for one in lines.values()]


def _luminance(rgb: np.ndarray) -> np.ndarray:
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    return linear @ np.array([0.2126, 0.7152, 0.0722])


def _legible(image, box: list, scale: float) -> dict:
    """One line at feed size: its letters' height there, and the contrast between its
    darker and lighter halves of luminance, which is letters against what is behind."""
    left, top, right, bottom = (int(round(v)) for v in box)
    patch = np.asarray(image.convert("RGB").crop((left, top, right, bottom)),
                       dtype=np.float64) / 255.0
    lum = _luminance(patch.reshape(-1, 3)) if patch.size else np.zeros(1)
    # Split at the mean, not the median: letters can be more than half a tight box.
    middle = float(lum.mean())
    dark, light = lum[lum <= middle], lum[lum > middle]
    ratio = ((float(light.mean()) if light.size else middle) + 0.05) / (
        (float(dark.mean()) if dark.size else middle) + 0.05)
    tall = (bottom - top) * scale
    return {"height_px": round(tall, 1), "contrast": round(ratio, 2),
            "passed": tall >= TALLEST_NEEDED and ratio >= CONTRAST}


@operation("store.thumbnail")
def thumbnail(
    picture: Annotated[str, Param("the thumbnail, under the project")],
    title: Annotated[str, Param("the video's title, as published")],
    *,
    texts: Annotated[
        list, Param("its lines, as text or {text, box: [l, t, r, b]}; OCR if unset")
    ] = None,
    language: Annotated[str, Param("the title's language, as en or pt-BR")] = "en",
    max_words: Annotated[int, Param("the most words it may carry", lo=1)] = 6,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Hold a thumbnail to its title and to a feed's size, before it is published.

    `words` is how many words it carries, against `max_words`. `shared` names every
    meaningful word it shares with the title, stop words of the language aside, case
    and accents folded: a thumbnail adds what the title leaves out. At 168x94 each line
    with a box answers its letters' height in px (at least 8) and the contrast of its
    letters against what is behind them (at least 3); a line with no box is
    `unmeasured`. The text is `texts`, from the layout that drew it, or what OCR reads
    where none is given; with neither, it is unchecked and never passed.
    """
    from PIL import Image

    config = load(root)
    path = config.root / picture
    if not path.is_file():
        raise PolyweaveError(
            "store.no-thumbnail", f"there is no thumbnail at {picture}",
            "name the picture under the project", given=picture)
    read_by = "layout"
    if texts is None:
        engine = shutil.which(str(config.path("paths.tesseract")))
        if not engine:
            return {"picture": picture, "checked": False, "passed": None,
                    "why": "no text was given and no OCR engine is installed: the "
                    "thumbnail is unchecked, which is not a pass"}
        from polyweave.layers.picture.picture import LANGUAGES

        texts = _read(path, engine, LANGUAGES.get(language.split("-")[0], "eng"))
        read_by = "ocr"
    lines = [one if isinstance(one, dict) else {"text": str(one)} for one in texts]
    words = [w for one in lines for w in str(one.get("text", "")).split()]
    titled = set(_meaningful(title, language))
    shared = sorted({w for one in lines
                     for w in _meaningful(str(one.get("text", "")), language)} & titled)
    with Image.open(path) as opened:
        image = opened.copy()
    scale = min(FEED[0] / image.width, FEED[1] / image.height)
    legible = []
    for one in lines:
        if one.get("box"):
            legible.append({"text": one.get("text", ""), **_legible(image, one["box"],
                                                                     scale)})
        else:
            legible.append({"text": one.get("text", ""), "unmeasured": True})
    failed = []
    if len(words) > max_words:
        failed.append(f"it carries {len(words)} words, past {max_words}")
    if shared:
        failed.append(f"it repeats the title's {', '.join(shared)}")
    failed += [f"{one['text']!r} is {one['height_px']}px tall at contrast "
               f"{one['contrast']} at feed size" for one in legible
               if one.get("passed") is False]
    return {
        "picture": picture, "checked": True, "read_by": read_by,
        "words": len(words), "max_words": max_words, "shared": shared,
        "feed": list(FEED), "lines": legible,
        "failed": failed, "passed": not failed,
    }


@operation("store.thumbnails")
def thumbnails(
    variants: Annotated[
        list, Param("the variants the layout drew, each a path or {picture, texts}")
    ],
    title: Annotated[str, Param("the video's title, as published")],
    *,
    language: Annotated[str, Param("the title's language, as en or pt-BR")] = "en",
    max_words: Annotated[int, Param("the most words each may carry", lo=1)] = 6,
    keep: Annotated[int, Param("how many passing variants are laid out", lo=1)] = 3,
    out: Annotated[str, Param("the sitting's folder; the project's if unset")] = None,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Hold each variant to store.thumbnail and lay the first passing ones for a person.

    The variants are what the project's own layout drew from its choices (which words,
    which picture, which number). Each is checked as `store.thumbnail` checks one; the
    first `keep` that pass, in the order given, are laid in a sitting on the review
    page, where a person picks the ones to put to the platform's own A/B test. The
    agent never picks: the answer names what was laid and why the rest were not.
    """
    from pathlib import Path

    from polyweave.loop import verdict

    config = load(root)
    checked, laid = [], []
    for one in variants:
        asked = one if isinstance(one, dict) else {"picture": str(one)}
        said = thumbnail(asked.get("picture", ""), title, texts=asked.get("texts"),
                         language=language, max_words=max_words, root=root)
        checked.append(said)
        if said.get("passed") and len(laid) < keep:
            laid.append(said["picture"])
    rest = [{"picture": one["picture"],
             "why": "; ".join(one["failed"]) if one.get("failed")
             else one.get("why") or f"it passed, past the {keep} laid out"}
            for one in checked if one["picture"] not in laid]
    if not laid:
        return {"laid": [], "rest": rest, "sitting": None,
                "says": "no variant passed, so nothing was laid for a person; change "
                "the layout's choices the failures name and draw them again"}
    folder = Path(out) if out else verdict._sitting_folder(
        config, "thumbnails", config.path("paths.work") / "thumbnails")
    if not folder.is_absolute():
        folder = config.root / folder
    sat = verdict.sitting(
        {"thumbnail": [{"name": Path(one).stem, "new": one} for one in laid]},
        out=str(folder), root=str(config.root),
        about=f"Thumbnails for “{title}”: pick the ones to put to the platform's A/B "
        "test. Each passed its word count, its title and the feed size.")
    return {"laid": laid, "rest": rest, "sitting": sat["page"],
            "says": f"{len(laid)} variant(s) laid for a person at {sat['page']}; "
            f"{len(rest)} not laid, each with why"}
