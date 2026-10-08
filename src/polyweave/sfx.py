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

A jingle is several effects at the times a game plays them, and a person judges it whole
(§PW313). So the same file may hold arrangements:

    [arrangement.splash]
    cues = [
      { effect = "splash_gather", at = 0.0 },
      { effect = "splash_pop", at = 0.4, pitch = 2, gain = -3 },
    ]

`at` is in seconds, `pitch` in semitones and `gain` in dB; `peak` caps the mix.

An effect may be declared at a note rather than in sfxr's numbers (§PW333):

    [effect.confirm]
    wave = "square"
    note = "A5"                         # or a frequency in Hz: note = 880
    arp = { to = "E6", at = 0.05 }      # jump to a note after a time, in seconds
    slide = { to = "A4", over = 0.4 }   # glide to a note, reached after `over`

which compile to `base_freq`, `arp_mod` and `arp_speed`, and `freq_ramp`: sfxr's pitch
is 3528 x (base_freq^2 + 0.001) Hz at 44.1 kHz, sampled eight times over. A slide keeps
its rate past `over`, as sfxr's does, so the sound's length decides where it stops. Each
arrangement is mixed into one file, placed as an effect is, with
`<name>.arrangement.json` beside it naming every cue's file, time, pitch and gain: what
the game reads, so the times it plays are the ones the person heard.
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

from . import licences, provenance, sfxr
from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

#: What an effect's table may hold besides sfxr's own parameters.
_OWN = {"generator": str, "seed": int, "min_duration": float, "max_duration": float,
        "peak": float, "loudness": float, "match": str, "note": object,
        "arp": dict, "slide": dict}

#: sfxr's pitch: Hz = PITCH x (base_freq^2 + 0.001), at 44.1 kHz and 8x oversampling.
PITCH = sfxr.RATE * 8 / 100.0

#: What a musical declaration replaces, so the two are never mixed (§PW333).
_TUNED = {"note": "base_freq", "arp": "arp_mod", "slide": "freq_ramp"}

_NOTE = __import__("re").compile(r"^([A-Ga-g])([#b]?)(-?\d+)$")
_STEPS = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}


def hz(name: str, value: Any) -> float:
    """A note name such as A5 or C#4, or a number of Hz, as Hz (A4 is 440)."""
    if _number(value):
        if value <= 0:
            raise _bad(name, f"has a pitch of {value!r} Hz",
                       "write a frequency above 0")
        return float(value)
    found = _NOTE.match(str(value).strip())
    if not found:
        raise _bad(name, f"has a note {value!r}",
                   'write a note as a letter, an optional # or b and an octave, "A5"')
    letter, accidental, octave = found.groups()
    steps = _STEPS[letter.upper()] + {"#": 1, "b": -1, "": 0}[accidental]
    steps += (int(octave) - 4) * 12
    return 440.0 * 2 ** (steps / 12)


def tuned(name: str, table: dict) -> dict:
    """The table with its notes compiled to sfxr's parameters (§PW333)."""
    mixed = [f"{own} and {theirs}" for own, theirs in _TUNED.items()
             if own in table and theirs in table]
    if mixed:
        raise _bad(name, f"declares both {mixed[0]}",
                   "keep one: the note, or sfxr's own number")
    if "note" not in table:
        if "arp" in table or "slide" in table:
            raise _bad(name, "declares an arp or a slide without a note to start on",
                       'add note = "A5"')
        return table
    out = {k: v for k, v in table.items() if k not in _TUNED}
    start = hz(name, table["note"])
    base = math.sqrt(max(start / PITCH - 0.001, 0.0))
    if base > 1.0 or start / PITCH <= 0.001:
        raise _bad(name, f"starts at {start:.1f} Hz, which sfxr cannot play",
                   f"keep a note from {PITCH * 0.001:.1f} to {PITCH * 1.001:.0f} Hz")
    out["base_freq"] = round(base, 6)
    if "arp" in table:
        arp = table["arp"]
        if not isinstance(arp, dict) or "to" not in arp or not _number(arp.get("at")):
            raise _bad(name, f"has arp {arp!r}", 'write arp = { to = "E6", at = 0.05 }')
        ratio = hz(name, arp["to"]) / start
        factor = 1.0 / ratio
        mod = (math.sqrt((1.0 - factor) / 0.9) if factor <= 1.0
               else -math.sqrt((factor - 1.0) / 10.0))
        samples = float(arp["at"]) * sfxr.RATE
        if not -1.0 <= mod <= 1.0 or not 32 <= samples <= 20032:
            raise _bad(name, f"arps by {ratio:.3f}x at {arp['at']} s",
                       "keep the jump within ten times up or eleven down, and its "
                       "time from 0.001 to 0.45 s")
        out["arp_mod"] = round(mod, 6)
        out["arp_speed"] = round(1.0 - math.sqrt((samples - 32) / 20000.0), 6)
    if "slide" in table:
        slide = table["slide"]
        if (not isinstance(slide, dict) or "to" not in slide
                or not _number(slide.get("over")) or slide["over"] <= 0):
            raise _bad(name, f"has slide {slide!r}",
                       'write slide = { to = "A4", over = 0.4 }')
        samples = float(slide["over"]) * sfxr.RATE
        step = (start / hz(name, slide["to"])) ** (1.0 / samples)
        cubed = (1.0 - step) / 0.01
        ramp = math.copysign(abs(cubed) ** (1.0 / 3.0), cubed)
        if not -1.0 <= ramp <= 1.0:
            raise _bad(name, f"slides too fast to reach {slide['to']} in "
                       f"{slide['over']} s",
                       "slide further in time, or by less")
        out["freq_ramp"] = round(ramp, 6)
    return out

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
    if "generator" not in table and not any(
        k in sfxr.NAMES or k in _TUNED for k in table
    ):
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
    elif _OWN[key] is str and not isinstance(value, str):
        raise _bad(name, f"sets {key} to {value!r}", f"write {key} as a path")
    elif key == "note":
        hz(name, value)


def _levelled(
    name: str, audio: np.ndarray, table: dict, root: Path
) -> tuple[np.ndarray, dict]:
    """The effect moved to the loudness it declares, under its peak (§PW254).

    Normalised to a peak alone, sfxr's dense explosions came out 10 dB louder in RMS
    than the sounds they replaced, and every hit in the mix jumped. So an effect may
    declare `loudness` (RMS dBFS, as sound.measure reports it) or `match` the sound it
    replaces, and `peak` is then a ceiling, said when it binds.
    """
    if "loudness" in table and "match" in table:
        raise _bad(name, "declares both loudness and match",
                   "keep one: loudness in dBFS, or match naming the sound it replaces")
    if ("loudness" not in table and "match" not in table) or not len(audio):
        return audio, {}
    aimed = table.get("loudness")
    if "match" in table:
        from .sound import measure

        replaced = Path(table["match"])
        replaced = replaced if replaced.is_absolute() else root / replaced
        if not replaced.is_file():
            raise _bad(name, f"matches {table['match']}, which is not there",
                       "name the sound it replaces, relative to the project")
        aimed = float(measure(replaced)["loudness"])
    now = _db(float(np.sqrt(np.mean(audio**2))))
    audio = audio * 10 ** ((float(aimed) - now) / 20.0)
    ceiling = float(table.get("peak", PEAK))
    peak = _db(float(np.abs(audio).max()))
    bound = peak > ceiling
    if bound:
        audio = audio * 10 ** ((ceiling - peak) / 20.0)
    return audio, {"aimed": round(float(aimed), 2), "ceiling_bound": bound}


def _params(table: dict, seed: int) -> sfxr.Params:
    """The generator's draw from this seed, with the parameters the table pins."""
    drawn = sfxr.Params()
    table = tuned("", table)
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


def kit(path: Path) -> dict[str, np.ndarray]:
    """Every effect of a `*.sfx.toml` made once, by name: a chip kit's hits (§PW223).

    Made exactly as `sound.synth` makes them, so a hit heard alone and a hit heard in a
    score are the same sound.
    """
    try:
        effects = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise PolyweaveError(
            "sound.no-source",
            f"the kit at {path.name} cannot be read",
            "name a *.sfx.toml of [effect.<drum>] tables",
            detail=str(exc),
        ) from exc
    tables = effects.get("effect")
    if not isinstance(tables, dict) or not tables:
        raise PolyweaveError("sound.no-source", f"{path.name} holds no [effect.<name>]",
                             "write each hit as [effect.bd], [effect.sd] and so on")
    return {
        name: _made(name, _checked(name, table))[0] for name, table in tables.items()
    }


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
        effects = tomllib.loads(where.read_text(encoding="utf-8-sig"))
    except tomllib.TOMLDecodeError as exc:
        raise PolyweaveError("sound.no-source", f"{source} is not TOML",
                             "fix the syntax the detail names",
                             detail=str(exc)) from exc
    stray = sorted(set(effects) - {"effect", "arrangement"})
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
    arranged = _arrangements(effects.get("arrangement"), tables)
    chosen = {effect: tables[effect]} if effect else tables
    checked = {name: _checked(name, table) for name, table in chosen.items()}
    declared = config.cue_files()
    made = {}
    heard: dict[str, np.ndarray] = {}
    for name, table in checked.items():
        audio, seed, tries = _made(name, table)
        audio, levelled = _levelled(name, audio, table, config.root)
        heard[name] = audio
        target = declared.get(name, where.parent / f"{name}.wav")
        made[name] = _placed(target, audio, config.root)
        measured = {
            "duration": round(len(audio) / sfxr.RATE, 4),
            "peak": _db(float(np.abs(audio).max()) if len(audio) else 0.0),
            "loudness": _db(float(np.sqrt(np.mean(audio**2))) if len(audio) else 0.0),
        }
        made[name].update({
            "generator": table.get("generator"),
            "seed": seed,
            "tries": tries,
            "declared": name in declared,
            **measured,
            **levelled,
        })
        # What made it and what it owes, beside it (§PW191).
        provenance.write(provenance.build(
            "sound", config.root / made[name]["file"], engine={"name": "sound.synth"},
            inputs=[provenance.source("effects", where, config.root)],
            params={"effect": name, "generator": table.get("generator"),
                    "seed": seed},
            measurements=measured,
            extra={"instruments": [licences.engine("sfxr", [name])]},
            root=config.root,
        ), config.root)
    answer = {"source": where.relative_to(config.root).as_posix(), "effects": made}
    if arranged and effect is None:
        answer["arrangements"] = {
            name: _arranged(name, held, tables, heard, made, where, declared, config)
            for name, held in arranged.items()
        }
    return answer


#: What one cue of an arrangement may say, and what each is when left out.
_CUE = {"effect": None, "at": None, "pitch": 0.0, "gain": 0.0}

#: The ceiling a mix is held under unless its arrangement says otherwise, in dBFS.
MIX_PEAK = -1.0


def _arrangements(declared: Any, tables: dict) -> dict[str, dict]:
    """Each arrangement's cues and ceiling, refused unless every cue means something."""
    if declared is None:
        return {}
    if not isinstance(declared, dict):
        raise PolyweaveError("sound.bad-effect", "arrangement is not a table",
                             "write each one as [arrangement.<name>] with cues")
    out = {}
    for name, table in declared.items():
        own = table if isinstance(table, dict) else {}
        stray = sorted(set(own) - {"cues", "peak"})
        cues = own.get("cues")
        if stray or not isinstance(cues, list) or not cues:
            said = f"has no key {stray[0]!r}" if stray else "has no cues"
            raise PolyweaveError(
                "sound.bad-effect", f"arrangement {name}: {said}",
                'write cues = [{ effect = "<name>", at = 0.0 }, ...], and peak if the '
                "mix needs another ceiling",
                **({"given": stray[0], "allowed": ["cues", "peak"]} if stray else {}),
            )
        if "peak" in own and not _number(own["peak"]):
            raise PolyweaveError("sound.bad-effect", f"arrangement {name}: sets peak "
                                 f"to {own['peak']!r}", "write peak in dBFS, as -1.0")
        out[name] = {
            "cues": [_cue(name, index, cue, tables) for index, cue in enumerate(cues)],
            "peak": float(own.get("peak", MIX_PEAK)),
        }
    return out


def _cue(name: str, index: int, cue: Any, tables: dict) -> dict:
    where = f"arrangement {name}, cue {index + 1}"
    extra = sorted(set(cue) - set(_CUE)) if isinstance(cue, dict) else []
    if not isinstance(cue, dict) or extra:
        raise PolyweaveError(
            "sound.bad-effect",
            f"{where} " + (f"has no key {extra[0]!r}" if extra else "is not a table"),
            'write it as { effect = "<name>", at = <seconds>, pitch = <semitones>, '
            "gain = <dB> }",
            **({"given": extra[0], "allowed": sorted(_CUE)} if extra else {}),
        )
    if cue.get("effect") not in tables:
        raise PolyweaveError(
            "sound.bad-effect",
            f"{where} names effect {cue.get('effect')!r}, which this file does not "
            "declare",
            f"name one of {', '.join(sorted(tables))}",
            given=str(cue.get("effect")), allowed=sorted(tables),
        )
    for key in ("at", "pitch", "gain"):
        if key in cue and not _number(cue[key]):
            raise PolyweaveError("sound.bad-effect",
                                 f"{where} sets {key} to {cue[key]!r}",
                                 f"write {key} as a number")
    if "at" not in cue or cue["at"] < 0:
        raise PolyweaveError("sound.bad-effect",
                             f"{where} has no time, or one before 0",
                             "give it at, in seconds from the start")
    return {**_CUE, **cue}


def _pitched(audio: np.ndarray, semitones: float) -> np.ndarray:
    """Played faster or slower, as a game's pitch_scale does: higher is shorter."""
    if not semitones or not len(audio):
        return audio
    ratio = 2.0 ** (semitones / 12.0)
    count = max(1, int(round(len(audio) / ratio)))
    return np.interp(np.arange(count) * ratio, np.arange(len(audio)), audio)


def _arranged(
    name: str, held: dict, tables: dict, heard: dict, made: dict, where: Path,
    declared: dict, config,
) -> dict:
    """One arrangement mixed as the game plays it, and the plan the game reads."""
    import json

    cues = held["cues"]
    for cue in cues:
        effect = cue["effect"]
        if effect not in heard:
            table = _checked(effect, tables[effect])
            heard[effect] = _levelled(effect, _made(effect, table)[0], table,
                                      config.root)[0]
    placed = [
        (int(round(cue["at"] * sfxr.RATE)),
         _pitched(heard[cue["effect"]], cue["pitch"]) * 10 ** (cue["gain"] / 20.0))
        for cue in cues
    ]
    mix = np.zeros(max(start + len(audio) for start, audio in placed))
    for start, audio in placed:
        mix[start:start + len(audio)] += audio
    peak = _db(float(np.abs(mix).max()) if len(mix) else 0.0)
    bound = peak > held["peak"]
    if bound:
        mix = mix * 10 ** ((held["peak"] - peak) / 20.0)
    target = declared.get(name, where.parent / f"{name}.wav")
    answer = _placed(target, mix, config.root)
    measured = {
        "duration": round(len(mix) / sfxr.RATE, 4),
        "peak": _db(float(np.abs(mix).max()) if len(mix) else 0.0),
        "loudness": _db(float(np.sqrt(np.mean(mix**2))) if len(mix) else 0.0),
    }
    played = [
        {"effect": cue["effect"], "file": (made.get(cue["effect"]) or {}).get("file"),
         "at": float(cue["at"]), "pitch": float(cue["pitch"]),
         "gain": float(cue["gain"])}
        for cue in cues
    ]
    plan = (config.root / answer["file"]).with_suffix(".arrangement.json")
    plan.write_text(json.dumps({"arrangement": name, "cues": played}, indent=1) + "\n",
                    encoding="utf-8", newline="\n")
    provenance.write(provenance.build(
        "sound", config.root / answer["file"], engine={"name": "sound.synth"},
        inputs=[provenance.source("effects", where, config.root)],
        params={"arrangement": name, "cues": played},
        measurements=measured,
        extra={"instruments": [
            licences.engine("sfxr", sorted({c["effect"] for c in cues}))
        ]},
        root=config.root,
    ), config.root)
    return {**answer, "plan": plan.relative_to(config.root).as_posix(),
            "cues": played, **measured, "ceiling_bound": bound}


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
