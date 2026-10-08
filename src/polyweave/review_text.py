"""What a sitting says to the person answering it, in the project's language (§PW287).

Starship's owner opened a sitting of seven trails and could not tell what they were
voting on: the page showed the sheets and two words, `accept` and `look`, each with a
clause in English. A verdict is a person's, and a person who does not know what a choice
sets in motion is not giving one. So every kind of sitting carries

- a `title` and an `about`: what is judged, and how to read the card;
- each choice as a `label`, what it `means`, and what happens `then` if it is chosen;
- for an effect, a `legend` of the numbers under it;

in the language `[review] language` names. The words live in one catalog per language,
`review_page/locales/<language>.json`, beside the page, which reads its own words from
the same file: a language is added by adding a file, and no sentence a person reads is
kept in code. The keys of the choices never change with the language, since they are
what `verdict.judge` records.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

from .errors import PolyweaveError

#: Where the catalogs are, one `<language>.json` each.
LOCALES = Path(__file__).with_name("review_page") / "locales"


def languages() -> tuple[str, ...]:
    """The languages a catalog exists for, English first."""
    found = sorted(one.stem for one in LOCALES.glob("*.json"))
    return tuple(sorted(found, key=lambda one: one != "en"))


@cache
def catalog(speaks: str) -> dict:
    """One language's catalog, the page's words and every kind of sitting's."""
    return json.loads((LOCALES / f"{speaks}.json").read_text(encoding="utf-8-sig"))


def language(root: str | Path = ".") -> str:
    """The language the project reads its sittings in, refused where it is not one."""
    from .config import load

    said = str(load(root).get("review.language") or "en")
    offered = languages()
    if said not in offered:
        raise PolyweaveError(
            "config.bad-language",
            f"[review] language is {said!r}, and the review page is written in "
            f"{', '.join(offered)}",
            f"set [review] language to one of {', '.join(offered)}, or add "
            f"review_page/locales/{said}.json",
            given=said,
            allowed=offered,
        )
    return said


def kind(name: str, speaks: str) -> dict:
    """One kind of sitting's words in one language."""
    return catalog(speaks)["kinds"][name]


def told(name: str, speaks: str, about: str = "") -> dict:
    """A sitting's title, summary and choices, each choice with what it leads to."""
    text = kind(name, speaks)
    summary = text["about"] + (f"\n\n{about.strip()}" if about.strip() else "")
    return {
        "language": speaks,
        "kind": name,
        "title": text["title"],
        "about": summary,
        **({"legend": dict(text["legend"])} if text.get("legend") else {}),
        "choices": {word: dict(choice) for word, choice in text["choices"].items()},
    }
