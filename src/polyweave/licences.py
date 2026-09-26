"""What a rendered sound's instruments are, and what their licences owe (§PW191).

A render uses engines and libraries whose licences differ: CC0, CC-BY needing credit, or
terms that forbid redistribution, and a game cannot ship credits nobody recorded. So
every sound polyweave makes carries, in its provenance record, the instruments that made
it: each with its licence, the credit it requires and anything a person should know.

**The engines are the plugin's to state**, since the plugin chose them, and none of
their licences reaches the audio they render. **A library is the project's to
declare**, under `[licence."<file name>"]`, because the project chose it: a render that
plays through a library nobody declared is refused before anything plays, rather than
shipped with a credit missing.

The PW184 spike's stack set the first entries: GeneralUser GS v2.0.3 allows any music
use, commercial included, with no credit required, but its author cannot vouch for the
origin of every sample, which a project records as a note rather than a clean bill.
"""

from __future__ import annotations

from pathlib import Path

from .config import Config
from .errors import PolyweaveError

#: The note every engine carries: its licence is on the code, not on what it makes.
_TOOL = "the licence covers the software, not the audio it renders"

#: The engines polyweave renders through, and their licences.
ENGINES: dict[str, dict] = {
    "surge": {"name": "Surge XT", "licence": "GPL-3.0", "credit": "", "note": _TOOL},
    "fluidsynth": {"name": "FluidSynth", "licence": "LGPL-2.1", "credit": "",
                   "note": _TOOL},
    "pedalboard": {"name": "Pedalboard", "licence": "GPL-3.0", "credit": "",
                   "note": _TOOL},
    "sfxr": {"name": "sfxr (DrPetter), ported", "licence": "MIT", "credit": "",
             "note": _TOOL},
}

#: What a declared licence may say. `terms` is required; an empty `credit` owes none.
KEYS = {"terms": True, "credit": False, "note": False, "url": False}


def engine(name: str, used_by: list[str] | None = None) -> dict:
    """One engine as an instrument entry in a record."""
    return {**ENGINES[name], "role": "engine", "used_by": sorted(used_by or [])}


def library(config: Config, file: Path, used_by: list[str]) -> dict:
    """A library as an instrument entry, from what the project declared of it.

    Refused where the project declared nothing: a credit nobody wrote down is one the
    game ships without.
    """
    stated = config.table("licence").get(file.name)
    if not isinstance(stated, dict):
        raise PolyweaveError(
            "music.licence-undeclared",
            f"the render plays {file.name}, and polyweave.toml declares no licence "
            f"for it",
            f'declare [licence."{file.name}"] with its terms, and the credit it '
            f"requires if any, from the library's own licence file",
            given=file.name,
        )
    missing = [k for k, required in KEYS.items() if required and not stated.get(k)]
    stray = sorted(set(stated) - set(KEYS))
    if missing or stray:
        raise PolyweaveError(
            "config.bad-type",
            f'[licence."{file.name}"] '
            + (f"has no {missing[0]}" if missing
               else f"has {stray[0]}, which it does not take"),
            f"write {', '.join(KEYS)}, with terms stated",
            at=f"licence.{file.name}",
        )
    return {
        "name": file.name,
        "role": "library",
        "licence": str(stated["terms"]),
        "credit": str(stated.get("credit", "")),
        "note": str(stated.get("note", "")),
        "url": str(stated.get("url", "")),
        "used_by": sorted(used_by),
    }


def patches(names: dict[str, list[str]]) -> list[dict]:
    """Surge patches written in the score: the project's own, owing nothing."""
    return [
        {"name": f"patch {name}", "role": "patch", "licence": "the project's own",
         "credit": "", "note": "", "used_by": sorted(parts)}
        for name, parts in sorted(names.items())
    ]
