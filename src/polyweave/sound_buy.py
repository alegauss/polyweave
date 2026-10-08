"""Buying a realistic effect, or a line spoken aloud, under the project's ceiling.

§PW190 bought effects; §PW314 speaks a given line in a named voice, through the same
doors and the same service.

Footsteps, glass or rain are not what a synthesiser does well, and a paid fetch without
a ceiling is the surprise Block D exists to prevent. So a bought sound goes through the
doors a picture and a mesh go through:

    1. the price is the project's `prices` row for the model, never the caller's figure
    2. `purchase.allow` is asked against the service's own ceiling, before any request
    3. the answer is captured before anything else: written, hashed and ledgered

The service is ElevenLabs' sound generation: one JSON request, answered with the audio.
It answers MP3, so a sound bought for a cue declared in another format is transcoded by
ffmpeg before it is captured, and the file on record is the one the game plays.

A `prices` row may be by the character, `{ per = "character", rate }` (§PW320): the
words sent are counted before anything is, and where the service's subscription answers
its `character_count` before and after, the spend is the difference times the rate and
the entry is `measured`. The quoted rate stays as the fallback, and says it was quoted.

No budget means no spend, and the decision to spend stays with a person: a ceiling is
written into `[budget.<name>]` by a person and never proposed by the plugin.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Annotated

from . import picture, provenance, purchase, sound
from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

#: The service's route, and the format it is asked to answer in.
ROUTE = "/v1/sound-generation"

#: Where the service says how many characters the account has used (§PW320).
USAGE = "/v1/user/subscription"
FORMAT = "mp3_44100_128"

TIMEOUT = 120

_CUE = Param("a cue [sound] declares; the file lands where it does")
_OUT = Param("or a path for it under the project, with its suffix")
_SECONDS = Param("how long, 0.5 to 30; the service's choice if unset", lo=0.5, hi=30)


@operation("sound.buy", kind="fetch", injects=("report",), spends=True)
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
    request: dict = {"text": prompt, "model_id": model, "prompt_influence": influence}
    if seconds is not None:
        request["duration_seconds"] = float(seconds)
    if loop:
        request["loop"] = True
    return _bought(
        report, f"{ROUTE}?output_format={FORMAT}", request, words=prompt, cue=cue,
        out=out, model=model, service=service, root=root,
        details={"cue": cue, "seconds": seconds, "influence": influence, "loop": loop},
    )


#: Where a line is spoken, by the voice the route names (§PW314).
SPEAK = "/v1/text-to-speech/{voice}"

#: How each delivery setting is named in the service's `voice_settings`.
DELIVERY = {
    "stability": "stability",
    "similarity": "similarity_boost",
    "style": "style",
    "speed": "speed",
}

_UNIT = Param("0 to 1; the voice's own if unset", lo=0.0, hi=1.0)


@operation("sound.speak", kind="fetch", injects=("report",), spends=True)
def speak(
    report=None,
    text: Annotated[str, Param("the line, word for word: Viglet Games")] = None,
    *,
    voice: Annotated[str, Param("the service's voice id that speaks it")] = None,
    cue: Annotated[str, _CUE] = None,
    out: Annotated[str, _OUT] = None,
    stability: Annotated[float, _UNIT] = None,
    similarity: Annotated[float, _UNIT] = None,
    style: Annotated[float, _UNIT] = None,
    speed: Annotated[
        float, Param("how fast, 0.7 to 1.2; the voice's own if unset", lo=0.7, hi=1.2)
    ] = None,
    model: Annotated[str, Param("the service's model, priced in [service]")] = (
        "eleven_multilingual_v2"
    ),
    entity: Annotated[str, Param("a world entity, whose voice speaks it")] = None,
    world: Annotated[str, Param("the *.world.toml, where the project has several")] = (
        None
    ),
    service: Annotated[str, purchase.SERVICE] = None,
    root: Annotated[str, Param("the project whose ledger this is")] = ".",
) -> dict:
    """Speak one line aloud in a named voice, at a cue's file, against the ceiling.

    `entity` speaks it in the voice the world gives that entity (§PW321), its delivery
    the voice's own where the call sets none; an entity with no voice id is refused.

    Text to speech is billed by the character, so its `prices` row is one by the
    character (§PW320) and the line is counted before anything is sent. The record
    keeps the words, the voice, the model and the delivery, so the take can be made
    again (§PW314).
    """
    if not text or not text.strip():
        raise PolyweaveError(
            "fetch.missing-field",
            "a line was asked to be spoken without its words",
            "pass text, the line exactly as it is to be said",
        )
    drawn_from, own = None, {}
    if entity:
        from .world import voiced

        drawn_from, own = voiced(entity, world, root)
        if voice and voice != own["id"]:
            raise PolyweaveError(
                "world.voice-mismatch",
                f"{entity} speaks in {own['id']!r} in the world, and the call named "
                f"{voice!r}",
                "leave voice unset, so every line of theirs is in their own voice",
                given=voice,
                allowed=[own["id"]],
            )
        voice = own["id"]
    if not voice:
        raise PolyweaveError(
            "fetch.missing-field",
            "a line was asked to be spoken in no voice",
            "pass voice, the id of one of the service's voices, or entity, one the "
            "world gives a voice",
        )
    called = {"stability": stability, "similarity": similarity, "style": style,
              "speed": speed}
    delivery = {
        DELIVERY[name]: float(called[name] if called[name] is not None else own[name])
        for name in DELIVERY
        if called[name] is not None or own.get(name) is not None
    }
    request: dict = {"text": text, "model_id": model}
    if delivery:
        request["voice_settings"] = delivery
    route = SPEAK.format(voice=urllib.parse.quote(voice, safe=""))
    return _bought(
        report, f"{route}?output_format={FORMAT}", request, words=text, cue=cue,
        out=out, model=model, service=service, root=root,
        details={"cue": cue, "voice": voice, "delivery": delivery, "spoken": True,
                 "entity": drawn_from},
        inputs=[provenance.source("world", drawn_from["world"], root=load(root).root)]
        if drawn_from
        else None,
    )


def _bought(
    report, route: str, request: dict, *, words: str, cue, out, model: str,
    service, root, details: dict, inputs: list | None = None,
) -> dict:
    """One paid request for audio, priced, allowed, captured and ledgered.

    What `sound.buy` and `sound.speak` share: the price by the project's row for the
    model, counted by the words where it is by the character, the ceiling asked before
    anything is sent, and the spend read off the service's usage where it answers
    (§PW320).
    """
    config = load(root)
    here = config.root
    target = _target(config, cue, out)
    name = config.service(service, model=model)
    about = config.services()[name]
    base, key = picture._reached(name, about)
    priced = picture._priced(
        name, about.get("prices") or {}, model, None, len(words)
    )
    price = priced["price"]
    if target.suffix.lower() != ".mp3" and not shutil.which("ffmpeg"):
        raise PolyweaveError(
            "sound.no-encoder",
            f"{target.name} wants {target.suffix[1:]}, the service answers MP3, and "
            f"there is no ffmpeg on PATH to transcode it",
            "put ffmpeg on PATH before spending, or ask for an .mp3",
        )

    purchase.allow_priced(priced, root=here, service=name)
    by_character = priced["per"] == "character"
    before = _used(base, key) if by_character else None
    if report is not None:
        report.stage("building", progress=0.2, note="asking the service for the sound")
    body, asked = _post(f"{base}{route}", key, request)
    after = _used(base, key) if before is not None else None
    reported = (
        round((after - before) * priced["rate"], 6)
        if before is not None and after is not None and after >= before
        else None
    )
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
        reported=reported,
        prompt=words,
        bought="sound",
        engine={"name": name, "model": model},
        service=name,
        details={**details, "format": target.suffix[1:]},
        inputs=inputs,
        root=here,
    )
    answer = {**entry, "file": target.relative_to(here).as_posix(),
              "measured": _measured(target)}
    if details.get("spoken"):
        # Held to its line before a person hears it (§PW323); a take that fails is
        # kept and said, never bought again here.
        answer["speech"] = _speech(target, words, config)
    return answer


def _speech(target: Path, words: str, config) -> dict:
    """What a spoken take measures against its line, or why it cannot be measured."""
    try:
        found = sound.speech(target, words, sound._names(config.root))
    except PolyweaveError as refused:
        return {"unmeasured": refused.message}
    return {**found, "failed": sound.held(found, config.table("voice"))}


#: Where a voice is designed from words, and where a chosen preview is kept (§PW321).
DESIGN = "/v1/text-to-voice/design"
SAVE = "/v1/text-to-voice"


@operation("voice.design", kind="fetch", injects=("report",), spends=True)
def design(
    report=None,
    entity: Annotated[str, Param("the world entity whose voice is described")] = None,
    *,
    sample: Annotated[str, Param("the line the previews speak; the voice's own")] = (
        None
    ),
    out: Annotated[str, Param("the folder the previews and the sitting go in")] = (
        None
    ),
    model: Annotated[str, Param("the service's model, priced in [service]")] = (
        "eleven_multilingual_ttv_v2"
    ),
    world: Annotated[str, Param("the *.world.toml, where the project has several")] = (
        None
    ),
    service: Annotated[str, purchase.SERVICE] = None,
    root: Annotated[str, Param("the project whose ledger this is")] = ".",
) -> dict:
    """Previews of an entity's described voice, laid out for a person to hear.

    Sends the world's `description` of the voice, speaking its `sample`, to the
    service's voice design, priced and ledgered as any purchase. Each preview lands as a
    sound with its record, and a sitting plays them; the person's verdict, not the
    agent's, is what `voice.choose` saves (§PW321).
    """
    from .world import brief

    if not entity:
        raise PolyweaveError(
            "fetch.missing-field",
            "a voice was asked to be designed for no entity",
            "pass entity, one the world describes a voice for",
        )
    source, found = brief(entity, world, root)
    voice = found.get("voice") or {}
    if not voice.get("description"):
        raise PolyweaveError(
            "world.no-voice",
            f"{entity} has no words about a voice to design it from",
            f'write description = "..." under [entity.{entity}.voice]',
            given=entity,
        )
    sample = sample or voice.get("sample")
    if not sample:
        raise PolyweaveError(
            "fetch.missing-field",
            f"no line to hear {entity}'s voice on",
            f'pass sample, or write sample = "..." under [entity.{entity}.voice]',
        )
    config = load(root)
    here = config.root
    folder = config.path("paths.work", out or f"voices/{entity}")
    name = config.service(service, model=model)
    about = config.services()[name]
    base, key = picture._reached(name, about)
    priced = picture._priced(
        name, about.get("prices") or {}, model, None, len(sample)
    )
    purchase.allow_priced(priced, root=here, service=name)
    before = _used(base, key) if priced["per"] == "character" else None
    if report is not None:
        report.stage("building", progress=0.2, note="asking the service for voices")
    answer = _asked(
        f"{base}{DESIGN}", key,
        {"voice_description": voice["description"], "text": sample, "model_id": model},
    )
    after = _used(base, key) if before is not None else None
    previews = [one for one in answer.get("previews") or () if one.get("audio_base_64")]
    if not previews:
        raise PolyweaveError(
            "fetch.nothing-arrived",
            "the service answered with no preview of the voice",
            "reword the description; nothing was ledgered",
        )
    spent = (
        (after - before) * priced["rate"]
        if before is not None and after is not None and after >= before
        else None
    )
    drawn_from = {
        "id": entity,
        "world": provenance.relative(source, here),
        "description": voice["description"],
    }
    heard = []
    for index, preview in enumerate(previews, start=1):
        body = base64.b64decode(preview["audio_base_64"])
        target = folder / f"{entity}_{index}.mp3"
        # One call answers every preview, so each carries its share of the price.
        entry = purchase.capture(
            body,
            out=target.relative_to(here).as_posix(),
            task_id=f"{name}:{preview.get('generated_voice_id') or index}",
            credits=round(priced["price"] / len(previews), 6),
            reported=None if spent is None else round(spent / len(previews), 6),
            prompt=sample,
            bought="sound",
            engine={"name": name, "model": model},
            service=name,
            details={"voice_preview": preview.get("generated_voice_id"),
                     "entity": drawn_from, "format": "mp3"},
            inputs=[provenance.source("world", source, root=here)],
            root=here,
        )
        heard.append({"name": target.stem, "new": entry["artefact"], "line": sample})
    laid = sound.sitting(
        heard, out=provenance.relative(folder, here), root=str(here)
    )
    return {
        "entity": entity,
        "description": voice["description"],
        "sample": sample,
        "previews": [one["new"] for one in heard],
        "sitting": laid["sitting"],
        "says": f"{len(heard)} previews of {entity}'s voice for a person to hear; "
        "voice.choose saves the one they accept",
    }


@operation("voice.choose", kind="fetch")
def choose(
    preview: Annotated[str, Param("the preview a person accepted, as a path")],
    *,
    world: Annotated[str, Param("the *.world.toml, where the project has several")] = (
        None
    ),
    service: Annotated[str, purchase.SERVICE] = None,
    root: Annotated[str, Param("the project whose ledger this is")] = ".",
) -> dict:
    """Keep the preview a person accepted as its entity's voice, written in the world.

    Refused unless the preview's record holds a person's `accept` on those very bytes:
    the agent never picks a voice (§PW321). The service saves it as a voice, and its id
    is written under `[entity.<id>.voice]` with the preview it came from.
    """
    config = load(root)
    here = config.root
    where = config.path("paths.work", preview)
    try:
        record = provenance.read(str(where), root=here)
    except PolyweaveError as missing:
        raise PolyweaveError(
            "world.voice-unchosen",
            f"{preview} has no record, so no one chose it",
            "run voice.design and choose from the previews it lays out",
            given=preview,
        ) from missing
    details = record.get("details") or {}
    drawn = details.get("entity") or {}
    if not details.get("voice_preview") or not drawn.get("id"):
        raise PolyweaveError(
            "world.voice-unchosen",
            f"{preview} is not a preview voice.design made",
            "choose from the previews voice.design lays out",
            given=preview,
        )
    digest = provenance.sha256_of(where)[0]
    said = [v for v in record.get("verdicts") or () if v.get("sha256") == digest]
    if not said or said[-1].get("choice") != "accept":
        raise PolyweaveError(
            "world.voice-unchosen",
            f"no person has accepted {preview} as {drawn['id']}'s voice",
            "lay the previews out with voice.design and let a person accept one on "
            "the review page; an agent does not choose a voice",
            given=preview,
        )
    name = config.service(service, model=str((record.get("engine") or {}).get("model")))
    base, key = picture._reached(name, config.services()[name])
    saved = _asked(
        f"{base}{SAVE}", key,
        {"voice_name": drawn["id"], "voice_description": drawn.get("description", ""),
         "generated_voice_id": details["voice_preview"]},
    )
    if not saved.get("voice_id"):
        raise PolyweaveError(
            "fetch.nothing-arrived",
            "the service kept no voice from the preview",
            "ask again; the world was not changed",
        )
    from .world import keep_voice

    kept = keep_voice(
        drawn["id"], saved["voice_id"], provenance.relative(where, here),
        world or drawn.get("world"), here,
    )
    return {"entity": drawn["id"], "voice": saved["voice_id"], "world": kept,
            "from": provenance.relative(where, here)}


@operation("voice.lines", kind="fetch", injects=("report",), spends=True)
def lines(
    report=None,
    speaker: Annotated[str, Param("only this entity's lines; all if unset")] = None,
    *,
    locale: Annotated[str, Param("only this locale's column; every one if unset")] = (
        None
    ),
    keys: Annotated[list, Param("only these keys of the table")] = None,
    spend: Annotated[bool, Param("send them; false answers the plan alone")] = False,
    model: Annotated[str, Param("the service's model, priced in [service]")] = (
        "eleven_multilingual_v2"
    ),
    world: Annotated[str, Param("the *.world.toml, where the project has several")] = (
        None
    ),
    service: Annotated[str, purchase.SERVICE] = None,
    root: Annotated[str, Param("the project whose ledger this is")] = ".",
) -> dict:
    """Voice the string table's lines as a set, each in its speaker's voice (§PW322).

    Without `spend` it sends nothing: each row it would voice with its characters and
    price, the takes still current, and the rows whose speaker has no voice. With it,
    the same selection is spoken until the ceiling stops it, the rest named as not
    voiced, and a sitting lays the new takes out by speaker for a person to hear.
    """
    from . import words
    from .world import declared, voice_digest

    config = load(root)
    here = config.root
    if not config.get("words.voiced"):
        raise PolyweaveError(
            "words.no-voiced",
            "the project says nowhere for a spoken line to land",
            'set [words] voiced = "audio/voice/{locale}/{key}.ogg" in polyweave.toml',
        )
    source, locales, rows = words.table(here)
    column = config.get("words.speaker")
    world_file, entities, _ = declared(world, here)
    if locale is not None and locale not in locales:
        raise PolyweaveError(
            "fetch.missing-field",
            f"the table has no {locale!r} column",
            f"name one of {', '.join(locales)}",
            given=locale,
            allowed=locales,
        )
    name = config.service(service, model=model)
    prices = config.services()[name].get("prices") or {}
    plan, current, unvoiced = [], [], []
    for row in rows:
        who = (row["cells"].get(column) or "").strip()
        if not who or (speaker and who != speaker):
            continue
        if keys and row["key"] not in keys:
            continue
        voice = (entities.get(who) or {}).get("voice") or {}
        for one in [locale] if locale else locales:
            text = (row["cells"].get(one) or "").strip()
            if not text:
                continue
            at = {"key": row["key"], "locale": one, "speaker": who}
            if not voice.get("id"):
                unvoiced.append({**at, "code": "world.no-voice"})
                continue
            out = config.get("words.voiced").format(
                locale=one, key=re.sub(r"[^\w.-]+", "_", row["key"])
            )
            line = {"key": row["key"], "locale": one, "sha256": words.said_digest(text)}
            if _still(here / out, line, voice_digest(entities[who]), model, here):
                current.append({**at, "out": out})
                continue
            price = picture._priced(name, prices, model, None, len(text))["price"]
            plan.append({**at, "out": out, "text": text, "characters": len(text),
                         "price": price, "line": line})
    total = round(sum(one["price"] for one in plan), 6)
    left = purchase.remaining(str(here), service=name)
    answer = {
        "voice": [{k: v for k, v in one.items() if k != "line"} for one in plan],
        "current": current,
        "unvoiced": unvoiced,
        "characters": sum(one["characters"] for one in plan),
        "price": total,
        "left": left["left"],
        "unit": left["unit"],
        "spent": False,
    }
    if not spend or not plan:
        return answer
    table_at = provenance.relative(source, here)
    voiced, stopped = [], []
    for index, one in enumerate(plan):
        drawn_from, own = (
            {"id": one["speaker"], "world": provenance.relative(world_file, here),
             "sha256": voice_digest(entities[one["speaker"]]), "of": "voice"},
            entities[one["speaker"]]["voice"],
        )
        delivery = {
            DELIVERY[k]: float(own[k]) for k in DELIVERY if own.get(k) is not None
        }
        request: dict = {"text": one["text"], "model_id": model}
        if delivery:
            request["voice_settings"] = delivery
        route = SPEAK.format(voice=urllib.parse.quote(own["id"], safe=""))
        try:
            took = _bought(
                report, f"{route}?output_format={FORMAT}", request, words=one["text"],
                cue=None, out=one["out"], model=model, service=name, root=here,
                details={"voice": own["id"], "delivery": delivery, "spoken": True,
                         "entity": drawn_from, "line": {**one["line"],
                                                        "table": table_at}},
                inputs=[provenance.source("world", world_file, root=here),
                        provenance.source("words", source, root=here)],
            )
        except PolyweaveError as refused:
            if refused.code not in ("fetch.over-budget", "fetch.budget-closed"):
                raise
            stopped = [{k: one[k] for k in ("key", "locale", "speaker", "price")}
                       for one in plan[index:]]
            answer["stopped_by"] = refused.message
            break
        voiced.append({**one, "failed": took["speech"].get("failed", [])})
    if voiced:
        heard = [
            {"name": f"{one['speaker']}.{one['key']}.{one['locale']}",
             "new": one["out"], "line": one["text"]}
            for one in sorted(voiced, key=lambda one: one["speaker"])
        ]
        folder = config.path("paths.work", "voices/lines")
        answer["sitting"] = sound.sitting(
            heard, out=provenance.relative(folder, here), root=str(here)
        )["sitting"]
    answer.update({
        "spent": True,
        "voiced": [{k: one[k] for k in ("key", "locale", "speaker", "out", "failed")}
                   for one in voiced],
        "not_voiced": stopped,
    })
    return answer


def _still(where: Path, line: dict, voice: str, model: str, here: Path) -> bool:
    """Whether a take already says this line, in this voice, on this model."""
    if not where.is_file():
        return False
    try:
        record = provenance.read(str(where), root=here)
    except PolyweaveError:
        return False
    details = record.get("details") or {}
    said = details.get("line") or {}
    return (
        said.get("sha256") == line["sha256"]
        and (details.get("entity") or {}).get("sha256") == voice
        and (record.get("engine") or {}).get("model") == model
        and provenance.sha256_of(where)[0] == (record.get("artefact") or {}).get(
            "sha256"
        )
    )


def _asked(url: str, key: str, payload: dict) -> dict:
    """One JSON request with the service's key header, answered with JSON."""
    request = urllib.request.Request(  # noqa: S310
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"xi-api-key": key, "Content-Type": "application/json",
                 "Accept": "application/json", "User-Agent": picture.AGENT},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:  # noqa: S310
            said = json.loads(answer.read() or b"{}")
    except urllib.error.HTTPError as refused:
        raise PolyweaveError(
            "fetch.service-error",
            f"the service answered {refused.code}",
            "read the detail; a 401 is a key the service does not accept, or an "
            "account out of credits, and a 422 words it would not use",
            detail=refused.read()[:400].decode("utf-8", "replace"),
        ) from refused
    except urllib.error.URLError as exc:
        raise PolyweaveError(
            "fetch.service-error",
            f"the service could not be reached at {url}",
            "check the base under [service] and the network",
            detail=str(exc.reason),
        ) from exc
    return said if isinstance(said, dict) else {}


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


def _used(base: str, key: str) -> int | None:
    """The characters the account has used, or None where the service will not say.

    Read before and after a call priced by the character, so its spend is measured; a
    reading that fails leaves the quoted price standing, never a guess (§PW320).
    """
    request = urllib.request.Request(  # noqa: S310
        f"{base}{USAGE}",
        headers={"xi-api-key": key, "Accept": "application/json",
                 "User-Agent": picture.AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:  # noqa: S310
            said = json.loads(answer.read())
    except (urllib.error.URLError, OSError, ValueError):
        return None
    count = said.get("character_count") if isinstance(said, dict) else None
    return count if isinstance(count, int) and not isinstance(count, bool) else None


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
