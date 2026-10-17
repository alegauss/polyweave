"""What the shared surfaces call: a measure, a sample, a verdict and three parts."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from . import wave

MEASURES = {
    "pitch_hz": "how high the tone is, in hertz",
    "tone_seconds": "how long the tone lasts, in seconds",
}


def predicate(p, subject, root, seen):
    where = Path(root) / (p.of or subject)
    if str(where) not in seen:
        seen[str(where)] = wave.read(where)
    return {"value": seen[str(where)][p.measure], "of": str(where)}


def sample(report, *, out, rung=None, root=".", inline=True, pitch=440.0):
    where = wave.write(Path(root) / out, pitch=float(pitch), seconds=0.25)
    return {"artefact": str(where)}


def still(source, record, one):
    """A changed declaration still describes the tone while its pitch is the same."""
    said = tomllib.loads(Path(source).read_text(encoding="utf-8"))
    return float(said.get("pitch", 0)) == record["details"]["pitch"]


def behind(root):
    """Each declaration with no tone beside it."""
    return sorted(
        one.name for one in Path(root).glob("*.tone.toml")
        if not one.with_name(one.name.removesuffix(".tone.toml") + ".wav").exists()
    )


def judged(member, *, accepted, choice, why, when, root):
    kept = Path(root) / "tone.verdicts.json"
    held = json.loads(kept.read_text(encoding="utf-8")) if kept.exists() else {}
    held[member["name"]] = {"hz": member["hz"], "accepted": accepted, "why": why}
    kept.write_text(json.dumps(held), encoding="utf-8")
    return held[member["name"]]


def briefed(path, here):
    return {"declared": len(list(Path(here).glob("*.tone.toml")))}


def reported(root):
    declared = list(Path(root).glob("*.tone.toml"))
    return {"declared": len(declared), "from": "*.tone.toml"}


def shown(here):
    return [{"tone": one.name} for one in sorted(Path(here).glob("*.wav"))]
