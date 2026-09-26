"""Retro effects from a seed (§PW189).

Cottony synthesised its effects with its own `tools/audio/make_sfx.py`, which a second
project would have had to copy. This is that generator made the plugin's: sfxr, driven
by a `*.sfx.toml` of effects, so a person tunes one by editing a number.

    [effect.pop_candy]
    generator = "pickup"   # one of sfxr's seven; left out, every parameter is by hand
    seed = 12              # the effect's name's CRC32 when left out
    min_duration = 0.15    # a draw outside the bounds moves to the next seed
    base_freq = 0.45       # any sfxr parameter pins the draw's value

The same seed gives the same bytes, so a verdict on an effect holds across runs. A first
draw can miss its purpose: in the PW184 spike a powerup meant for a won level came out
at 0.11 s. So a duration bound refuses a draw and moves to the next seed, and the answer
says which seed was kept and after how many tries.

An effect whose name is a cue declared under `[sound]` lands at that cue's file, in its
format; any other lands beside the `*.sfx.toml`.
"""

from __future__ import annotations

import difflib
import math
import shutil
import subprocess
import tomllib
import wave
import zlib
from dataclasses import replace
from pathlib import Path
from typing import Annotated, Any

import numpy as np

from . import sfxr
from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

#: What an effect's table may hold besides sfxr's own parameters.
_OWN = {"generator": str, "seed": int, "min_duration": float, "max_duration": float,
        "peak": float}

#: How many seeds a bound may try before the effect is refused.
TRIES = 64

#: The peak an effect is normalised to, in dBFS, unless it says otherwise.
PEAK = -3.0

#: The fade at an effect's end, so it stops on silence rather than a click.
FADE = 0.005


def _bad(name: str, what: str, remedy: str, **extra: Any) -> PolyweaveError:
    return PolyweaveError("sound.bad-effect", f"effect {name}: {what}", remedy, **extra)


#: Every key an effect's table may hold.
_ALLOWED = sorted(set(_OWN) | set(sfxr.NAMES))


def _checked(name: str, table: Any) -> dict:
    """One effect's table, every key and value refused unless it means something."""
    if not isinstance(table, dict):
        raise _bad(name, "is not a table", f"write it as [effect.{name}]")
    for key, value in table.items():
        _check_key(name, key, value)
    if "generator" not in table and not any(k in sfxr.NAMES for k in table):
        raise _bad(name, "has neither a generator nor a parameter",
                   f"set generator to one of {', '.join(sfxr.GENERATORS)}")
    return table


def _number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _check_key(name: str, key: str, value: Any) -> None:
    if key not in _ALLOWED:
        near = difflib.get_close_matches(key, _ALLOWED, n=1)
        raise _bad(name, f"has no key {key!r}",
                   f"did you mean {near[0]!r}?" if near
                   else f"name one of {', '.join(_ALLOWED)}",
                   given=key, allowed=_ALLOWED)
    if key == "generator":
        if value not in sfxr.GENERATORS:
            raise _bad(name, f"names generator {value!r}",
                       f"name one of {', '.join(sfxr.GENERATORS)}",
                       given=str(value), allowed=sorted(sfxr.GENERATORS))
    elif key == "wave":
        if value not in sfxr.WAVES and value not in sfxr.WAVES.values():
            raise _bad(name, f"has wave {value!r}",
                       f"name one of {', '.join(sfxr.WAVES)}")
    elif key in sfxr.NAMES:
        low = -1.0 if key in sfxr.SIGNED else 0.0
        if not _number(value) or not low <= value <= 1.0:
            raise _bad(name, f"sets {key} to {value!r}",
                       f"write a number from {low:g} to 1, as sfxr does")
    elif _OWN[key] is int and (isinstance(value, bool) or not isinstance(value, int)):
        raise _bad(name, f"sets {key} to {value!r}", f"write {key} as a whole number")
    elif _OWN[key] is float and not _number(value):
        raise _bad(name, f"sets {key} to {value!r}", f"write {key} as a number")


def _params(table: dict, seed: int) -> sfxr.Params:
    """The generator's draw from this seed, with the parameters the table pins."""
    drawn = sfxr.Params()
    if "generator" in table:
        drawn = sfxr.drawn(table["generator"], seed)
    pinned = {k: v for k, v in table.items() if k in sfxr.NAMES}
    if isinstance(pinned.get("wave"), str):
        pinned["wave"] = sfxr.WAVES[pinned["wave"]]
    return replace(drawn, **pinned)


def _finished(samples: list[float], peak: float) -> np.ndarray:
    """Centred, faded out and normalised to its peak: what a game plays."""
    audio = np.asarray(samples, dtype=np.float64)
    if not len(audio) or not np.abs(audio).max():
        return audio
    audio = audio - audio.mean()
    fade = min(len(audio), int(FADE * sfxr.RATE))
    audio[len(audio) - fade:] *= np.linspace(1.0, 0.0, fade)
    return audio * (10 ** (peak / 20.0) / np.abs(audio).max())


def _made(name: str, table: dict) -> tuple[np.ndarray, int, int]:
    """The effect's samples, the seed kept and how many seeds were tried."""
    seed = table.get("seed", zlib.crc32(name.encode()))
    low, high = table.get("min_duration", 0.0), table.get("max_duration", math.inf)
    bounded = "min_duration" in table or "max_duration" in table
    tries = TRIES if bounded and "generator" in table else 1
    for attempt in range(tries):
        audio = _finished(sfxr.synth(_params(table, seed + attempt), seed + attempt),
                          table.get("peak", PEAK))
        if low <= len(audio) / sfxr.RATE <= high:
            return audio, seed + attempt, attempt + 1
    raise PolyweaveError(
        "sound.no-draw",
        f"effect {name}: no seed from {seed} to {seed + tries - 1} gave a length from "
        f"{low:g} to {high:g} s",
        "widen the bounds, or pin env_sustain and env_decay, which set the length"
        if "generator" in table else
        "change env_sustain and env_decay, which set the length",
    )


def _write(where: Path, audio: np.ndarray) -> None:
    pcm = np.clip(np.round(audio * 32767.0), -32768, 32767).astype("<i2")
    with wave.open(str(where), "wb") as held:
        held.setnchannels(1)
        held.setsampwidth(2)
        held.setframerate(sfxr.RATE)
        held.writeframes(pcm.tobytes())


@operation("sound.synth")
def synth(
    source: Annotated[str, Param("the *.sfx.toml, relative to the project")],
    effect: Annotated[str, Param("one effect; left out, every one")] = None,
    root: Annotated[str, Param("the project the effects belong to")] = ".",
) -> dict:
    """Make retro effects from a seed with sfxr, each at its declared cue's file.

    A duration bound moves a draw to the next seed; each answer says the seed kept,
    the tries, and the effect's length, peak and loudness.
    """
    config = load(root)
    where = config.path("paths.work", source)
    if not where.is_file():
        raise PolyweaveError("sound.no-source", f"there is no effects file at {source}",
                             "name a *.sfx.toml relative to the project root")
    try:
        effects = tomllib.loads(where.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise PolyweaveError("sound.no-source", f"{source} is not TOML",
                             "fix the syntax the detail names",
                             detail=str(exc)) from exc
    stray = sorted(set(effects) - {"effect"})
    if stray or not isinstance(effects.get("effect"), dict) or not effects["effect"]:
        raise PolyweaveError("sound.no-source",
                             f"{source} holds no [effect.<name>] tables",
                             "write each effect as [effect.<name>] with a generator")
    tables = effects["effect"]
    if effect is not None and effect not in tables:
        near = difflib.get_close_matches(effect, tables, n=1)
        raise PolyweaveError(
            "sound.bad-effect", f"{source} has no effect {effect!r}",
            f"did you mean {near[0]!r}?" if near
            else f"name one of {', '.join(tables)}",
            given=effect, allowed=sorted(tables),
        )
    chosen = {effect: tables[effect]} if effect else tables
    checked = {name: _checked(name, table) for name, table in chosen.items()}
    declared = config.cue_files()
    made = {}
    for name, table in checked.items():
        audio, seed, tries = _made(name, table)
        target = declared.get(name, where.parent / f"{name}.wav")
        made[name] = _placed(target, audio, config.root)
        made[name].update({
            "generator": table.get("generator"),
            "seed": seed,
            "tries": tries,
            "declared": name in declared,
            "duration": round(len(audio) / sfxr.RATE, 4),
            "peak": _db(float(np.abs(audio).max()) if len(audio) else 0.0),
            "loudness": _db(float(np.sqrt(np.mean(audio**2))) if len(audio) else 0.0),
        })
    return {"source": where.relative_to(config.root).as_posix(), "effects": made}


def _placed(target: Path, audio: np.ndarray, root: Path) -> dict:
    """The effect written where its cue lands: WAV, or encoded from one by ffmpeg."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.suffix.lower() == ".wav":
        _write(target, audio)
        return {"file": target.relative_to(root).as_posix()}
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise PolyweaveError(
            "sound.no-encoder",
            f"{target.name} is declared {target.suffix[1:]}, and there is no ffmpeg "
            f"on PATH to encode it",
            "put ffmpeg on PATH, or declare the family's format as wav",
        )
    held = target.with_suffix(".synth.wav")
    _write(held, audio)
    try:
        subprocess.run([ffmpeg, "-v", "error", "-y", "-i", str(held), str(target)],
                       check=True, capture_output=True)
    finally:
        held.unlink(missing_ok=True)
    return {"file": target.relative_to(root).as_posix()}


def _db(value: float) -> float:
    return round(20.0 * math.log10(max(value, 1e-12)), 3)
