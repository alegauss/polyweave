"""Buying a realistic effect from a service, under the project's ceiling (§PW190).

Footsteps, glass or rain are not what a synthesiser does well, and a paid fetch without
a ceiling is the surprise Block D exists to prevent. So a bought sound goes through the
doors a picture and a mesh go through:

    1. the price is the project's `prices` row for the model, never the caller's figure
    2. `purchase.allow` is asked against the service's own ceiling, before any request
    3. the answer is captured before anything else: written, hashed and ledgered

The service is ElevenLabs' sound generation: one JSON request, answered with the audio.
It answers MP3, so a sound bought for a cue declared in another format is transcoded by
ffmpeg before it is captured, and the file on record is the one the game plays.

No budget means no spend, and the decision to spend stays with a person: a ceiling is
written into `[budget.<name>]` by a person and never proposed by the plugin.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Annotated

from . import picture, purchase, sound
from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

#: The service's route, and the format it is asked to answer in.
ROUTE = "/v1/sound-generation"
FORMAT = "mp3_44100_128"

TIMEOUT = 120

_CUE = Param("a cue [sound] declares; the file lands where it does")
_OUT = Param("or a path for it under the project, with its suffix")
_SECONDS = Param("how long, 0.5 to 30; the service's choice if unset", lo=0.5, hi=30)


@operation("sound.buy", kind="fetch", injects=("report",))
def buy(
    report=None,
    prompt: Annotated[str, Param("the sound, in words: footsteps on gravel")] = None,
    *,
    cue: Annotated[str, _CUE] = None,
    out: Annotated[str, _OUT] = None,
    seconds: Annotated[float, _SECONDS] = None,
    influence: Annotated[
        float, Param("how closely it follows the words, 0 to 1", lo=0.0, hi=1.0)
    ] = 0.3,
    loop: Annotated[bool, Param("ask for a sound that loops, such as rain")] = False,
    model: Annotated[str, Param("the service's model, priced in [service]")] = (
        "eleven_text_to_sound_v2"
    ),
    service: Annotated[str, purchase.SERVICE] = None,
    root: Annotated[str, Param("the project whose ledger this is")] = ".",
) -> dict:
    """Buy one sound effect from words, at a declared cue's file, against the ceiling.

    Returns the ledger entry and where the file landed. The `prices` row for `model`
    decides whether it may be spent, and nothing is sent when it may not.
    """
    if not prompt:
        raise PolyweaveError(
            "fetch.missing-field",
            "a sound was asked for without words",
            "pass prompt, the sound described as a sound designer would",
        )
    config = load(root)
    here = config.root
    target = _target(config, cue, out)
    name = config.service(service)
    about = config.services()[name]
    base, key = picture._reached(name, about)
    price = picture._price(name, about.get("prices") or {}, model, None)
    if target.suffix.lower() != ".mp3" and not shutil.which("ffmpeg"):
        raise PolyweaveError(
            "sound.no-encoder",
            f"{target.name} wants {target.suffix[1:]}, the service answers MP3, and "
            f"there is no ffmpeg on PATH to transcode it",
            "put ffmpeg on PATH before spending, or ask for an .mp3",
        )
    request: dict = {"text": prompt, "model_id": model, "prompt_influence": influence}
    if seconds is not None:
        request["duration_seconds"] = float(seconds)
    if loop:
        request["loop"] = True

    purchase.allow(price, root=here, service=name)
    if report is not None:
        report.stage("building", progress=0.2, note="asking the service for the sound")
    body, asked = _post(f"{base}{ROUTE}?output_format={FORMAT}", key, request)
    if not body:
        raise PolyweaveError(
            "fetch.nothing-arrived",
            "the service answered with no audio",
            "ask again; nothing was ledgered",
        )
    if report is not None:
        report.stage("downloading", progress=0.9, note="taking delivery of the sound")
    played = body if target.suffix.lower() == ".mp3" else _transcoded(body, target)
    entry = purchase.capture(
        played,
        out=target.relative_to(here).as_posix(),
        task_id=f"{name}:{asked or hashlib.sha256(body).hexdigest()[:16]}",
        credits=price,
        prompt=prompt,
        bought="sound",
        engine={"name": name, "model": model},
        service=name,
        details={"cue": cue, "seconds": seconds, "influence": influence, "loop": loop,
                 "format": target.suffix[1:]},
        root=here,
    )
    return {**entry, "file": target.relative_to(here).as_posix(),
            "measured": _measured(target)}


def _target(config, cue: str | None, out: str | None) -> Path:
    """Where the sound lands: its declared cue's file, or the path the call names."""
    if (cue is None) == (out is None):
        raise PolyweaveError(
            "fetch.missing-field",
            "a sound lands at a cue or a path, and this call gave "
            + ("neither" if cue is None else "both"),
            "pass cue, a name [sound] declares, or out, a path under the project",
        )
    if cue is not None:
        declared = config.cue_files()
        if cue not in declared:
            raise PolyweaveError(
                "sound.unknown-cue",
                f"no [sound] family declares a cue named {cue!r}",
                "add it to a family's cues, or pass out instead",
                given=cue,
                allowed=sorted(declared),
            )
        return declared[cue]
    target = config.path("paths.work", out)
    if target.suffix.lower() not in sound.SUFFIXES:
        raise PolyweaveError(
            "fetch.missing-field",
            f"{out} is not a sound file's name",
            f"end it in one of {', '.join(sound.SUFFIXES)}",
        )
    return target


def _post(url: str, key: str, payload: dict) -> tuple[bytes, str]:
    """One request with the service's key header, answered with audio and its id."""
    request = urllib.request.Request(  # noqa: S310
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"xi-api-key": key, "Content-Type": "application/json",
                 "Accept": "audio/mpeg", "User-Agent": picture.AGENT},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:  # noqa: S310
            return answer.read(), answer.headers.get("request-id", "")
    except urllib.error.HTTPError as refused:
        said = refused.read()[:400].decode("utf-8", "replace")
        if refused.code == 422:
            raise PolyweaveError(
                "fetch.prompt-refused",
                "the service would not make a sound from those words",
                "reword the prompt; nothing was ledgered",
                detail=said,
            ) from refused
        if refused.code == 429:
            raise PolyweaveError(
                "fetch.rate-limited",
                "the service has more requests from this account than it allows",
                "wait, then ask again",
                detail=said,
            ) from refused
        raise PolyweaveError(
            "fetch.service-error",
            f"the service answered {refused.code}",
            "read the detail; a 401 is a key the service does not accept, or an "
            "account out of credits, and a 400 a request it does not",
            detail=said,
        ) from refused
    except urllib.error.URLError as exc:
        raise PolyweaveError(
            "fetch.service-error",
            f"the service could not be reached at {url}",
            "check the base under [service] and the network",
            detail=str(exc.reason),
        ) from exc


def _transcoded(body: bytes, target: Path) -> bytes:
    """The service's MP3 in the format the cue declares, through ffmpeg's pipes."""
    shaped = {".wav": ["-f", "wav", "-c:a", "pcm_s16le"],
              ".ogg": ["-f", "ogg", "-c:a", "libvorbis", "-q:a", "6"],
              ".flac": ["-f", "flac"], ".opus": ["-f", "opus", "-c:a", "libopus"]}
    done = subprocess.run(
        [shutil.which("ffmpeg"), "-v", "error", "-i", "pipe:0",
         *shaped[target.suffix.lower()], "pipe:1"],
        input=body, capture_output=True, check=False,
    )
    if done.returncode or not done.stdout:
        raise PolyweaveError(
            "fetch.nothing-arrived",
            f"ffmpeg could not turn the service's MP3 into {target.suffix[1:]}",
            "read the detail; nothing was ledgered",
            detail=done.stderr[:400].decode("utf-8", "replace"),
        )
    return done.stdout


def _measured(target: Path) -> dict:
    """What the sound measures, or why it cannot be measured yet."""
    try:
        return sound.measure(target)
    except PolyweaveError as refused:
        return {"unmeasured": refused.message}
    except subprocess.CalledProcessError:
        # sound.read lets ffmpeg's own failure out on audio it cannot decode (PW224).
        return {"unmeasured": f"ffmpeg could not decode {target.name}"}
