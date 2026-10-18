"""Buying a picture, which is the cheap step in front of the dear one (§PW163).

The plugin prefers a drawing to a photograph (§PW21), and until now every drawing came
from a person, because the agent cannot draw. Ideogram generates one, and its
transparent endpoint delivers a PNG with a real alpha channel, which is the form
`reference.pick` reads as a drawing. A picture costs cents where the mesh it steers
costs thirty credits.

**This is the first service the plugin speaks to itself.** Until now a consumer's own
client fetched and the plugin captured. The client is `services/ideogram.py`, and a
picture goes through `services.service.buy`, the doors a mesh goes through, in the same
order (§PW516):

    1. the payload is checked against the learned schema, where one is learned (§PW19)
    2. `purchase.allow` is asked, against this service's own ceiling (§PW18, §PW162)
    3. the request is sent, and a refusal is a code rather than a traceback
    4. the picture is captured before anything else happens (§PW17), because the
       service's links expire and that order is the only one that cannot leave a
       receipt without an asset

On 4.0 the call is asynchronous: the answer is a generation id, asked after until the
picture is drawn; 3.0 answers with the picture's link at once.
"""

from __future__ import annotations

import json
from typing import Annotated

import numpy as np

from polyweave.kernel import provenance
from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.doors import Blank, door
from polyweave.kernel.errors import PolyweaveError
from polyweave.kernel.files import write_atomic
from polyweave.layers.words.world import ENTITY, WORLD, from_world
from polyweave.services import ideogram, purchase, schema
from polyweave.services import service as S
from polyweave.services.client import AGENT, sent_bytes  # noqa: F401
from polyweave.services.client import mime as _mime
from polyweave.services.client import price as _price
from polyweave.services.client import priced as _priced  # noqa: F401
from polyweave.services.client import reached as _reached
from polyweave.services.ideogram import MODELS

from . import style


@operation("picture.buy", kind="fetch", injects=("report",), spends=True)
def buy(
    report=None,
    out: Annotated[str, Param("where it is written, under the project")] = None,
    prompt: Annotated[
        str, Param("what it shows, as text the service may rewrite")
    ] = None,
    *,
    json_prompt: Annotated[
        dict, Param("what it shows, structured, which 4.0 draws without rewriting")
    ] = None,
    transparent: Annotated[bool, Param("a PNG with alpha, read as a drawing")] = True,
    model: Annotated[str, Param("the model", choices=tuple(MODELS))] = "4.0",
    aspect_ratio: Annotated[str, Param("as the service spells it")] = None,
    rendering_speed: Annotated[str, Param("as the service spells it")] = None,
    seed: Annotated[int, Param("for a picture that can be asked for again")] = None,
    family: Annotated[
        str, Param("the asset family whose [style] it is held to")
    ] = None,
    entity: Annotated[str, ENTITY] = None,
    world: Annotated[str, WORLD] = None,
    service: Annotated[str, purchase.SERVICE] = None,
    root: Annotated[str, Param("the project whose ledger this is")] = ".",
) -> dict:
    """Buy one picture against the service's ceiling and keep it before anything else.

    Returns the ledger entry, with where the picture landed. Nothing is spent where the
    ceiling would not allow it, where the key is not set, where no price is declared for
    the model and speed, or where the payload names a field the learned schema does not
    carry. The price is the project's `prices` table, never the caller's figure, and the
    entry says it was quoted rather than measured (§PW164).

    The record holds what a second call needs (§PW165): the prompt sent, the prompt the
    service says it drew from, the seed it reports, the model, speed and resolution. A
    text prompt on 4.0 is rewritten before drawing, so `json_prompt` is the one that
    makes the same picture again; `picture.describe` turns an approved picture into one.

    Where the project declares a `[style]`, the structured prompt is composed over the
    family's skeleton and palette before anything else (§PW166), and a text prompt is
    refused, because it has nowhere to carry them.

    With `entity`, the description is the world's (§PW198): its look opens the prompt,
    the call's own words add detail, its traits close it, its style family is the one
    in force, and the record names the entity and a hash of what it was drawn from.

    On a Scenario service the picture is drawn from the model `style.train` trained on
    the family's canon, from a text prompt; `model` is then the trained one (§PW450).
    """
    if model not in MODELS:
        raise PolyweaveError(
            "fetch.bad-choice",
            f"there is no model {model!r} this client knows the request shape of",
            f"pass one of {', '.join(MODELS)}",
            given=model,
            allowed=MODELS,
        )
    if not out:
        raise PolyweaveError(
            "fetch.missing-field",
            "a picture was asked for with nowhere to write it",
            "pass out, a path under the project",
        )
    from . import scenario

    if scenario.serves(load(root), service):
        # A Scenario service draws from the model the family's canon trained (§PW450).
        return scenario.bought(report, out=out, prompt=prompt, family=family,
                               aspect_ratio=aspect_ratio, seed=seed, service=service,
                               root=root)
    drawn_from = None
    if entity is not None:
        drawn_from, family, prompt, json_prompt = from_world(
            entity, world, root, family, prompt, json_prompt, structured=model == "4.0"
        )
    config = load(root)
    held_to = style.in_force(config, family)
    referenced: list[dict] = []
    if held_to is not None and held_to[1].get("references"):
        # The canon's pictures go with the words (§PW180). Only 3.0 takes a reference,
        # and only beside text, so the skeleton and palette are written into the words
        # and a call that would drop the pictures is refused rather than sent.
        if model != "3.0":
            raise PolyweaveError(
                "style.references-need-3",
                f"the {held_to[0]} style sends {len(held_to[1]['references'])} canon "
                f"picture(s) as references, and {model} takes none",
                "ask model 3.0, or empty references to draw from the words alone",
                call=door("picture.buy", out=out, model="3.0", family=held_to[0],
                          prompt=prompt or Blank("the picture, in words")),
            )
        if json_prompt is not None:
            raise PolyweaveError(
                "style.references-take-text",
                f"the {held_to[0]} style's references go with a text prompt, and this "
                f"call gave a structured one",
                "pass prompt as text; the family's skeleton and palette are written "
                "into it",
            )
        _one_prompt(prompt, json_prompt, model)
        referenced = style.references(*held_to)
        prompt = style.worded(prompt, held_to[1])
    elif held_to is not None:
        _one_prompt(prompt, json_prompt, model)
        if json_prompt is None:
            raise PolyweaveError(
                "style.needs-structure",
                f"the {held_to[0]} style is carried by a structured prompt, and this "
                f"call gave text",
                "pass json_prompt on 4.0; its style block starts from the family's "
                "skeleton and its palette is the family's",
            )
        json_prompt = style.compose(json_prompt, held_to[1])
    else:
        _one_prompt(prompt, json_prompt, model)
    name = config.service(service, model=model)
    about = config.services()[name]
    base, key = _reached(name, about)
    price = _price(name, about.get("prices") or {}, model, rendering_speed)

    _, prompt_field, _ = MODELS[model]
    sent = prompt if json_prompt is None else json.dumps(json_prompt, sort_keys=True)
    payload: dict = {prompt_field if json_prompt is None else "json_prompt": sent}
    for field, value in (
        ("aspect_ratio", aspect_ratio),
        ("rendering_speed", rendering_speed),
        ("seed", seed),
    ):
        if value is not None:
            payload[field] = value
    learned = schema.read(root, name).get("field") or {}
    if seed is not None and not (learned.get("seed") or {}).get("proved"):
        # A field the service drops is dropped in silence, and a seed that was dropped
        # records a picture as repeatable when it is not. So it is learned, not assumed.
        raise PolyweaveError(
            "fetch.seed-unproved",
            f"nothing has proved that {name} reads a seed on {model}",
            "learn the service's schema, which proves each field it reads, or ask "
            "without a seed and keep the one the answer reports",
        )
    # Checked where a schema has been learned. The fields above are this client's own,
    # so where nothing is learned there is no caller's typo for a check to catch.
    if learned:
        schema.validate(payload, root=root, service=name)

    order = S.Order(
        service=name, base=base, key=key, price=price, root=config.root,
        asked={
            "path": ideogram.generation(model, transparent),
            "payload": payload,
            # Each reference as its own repeated field, which is how the service reads
            # a list.
            "files": [
                ("style_reference_images", (one["picture"], one["bytes"], "image/png"))
                for one in referenced
            ] or None,
            "unit": config.budget(service=name)["unit"],
        },
        kept={
            "out": out,
            "prompt": sent,
            "bought": "image",
            "engine": {"name": name, "model": model},
            "details": {
                "model": model,
                "transparent": bool(transparent),
                "rendering_speed": rendering_speed,
                "aspect_ratio": aspect_ratio,
                "json_prompt": json_prompt,
                "family": held_to[0] if held_to else None,
                # The canon pictures sent as style references, by digest, so a second
                # call sends the same ones (§PW180).
                **({"references": [{"picture": one["picture"], "sha256": one["sha256"]}
                                   for one in referenced]} if referenced else {}),
                "entity": drawn_from,
            },
            **({"inputs": [provenance.source("world", drawn_from["world"], root=root)]}
               if drawn_from else {}),
        },
    )
    return S.buy(ideogram.SERVICE, order, report)


@operation("picture.collect")
def collect(
    task_id: Annotated[str, Param("the purchase's task id, as the refusal named it")],
    *,
    root: Annotated[str, Param("the project whose ledger this is")] = ".",
) -> dict:
    """Take delivery of a picture that was paid for and never arrived (§PW179).

    Its charge is on the owed list, counted against the ceiling since the download
    failed. This reads the link again; once the picture lands it is ledgered like any
    other and the charge leaves the owed list. A link that has expired stays owed, and
    the charge stays counted, because the money went either way.
    """
    held = {e["task_id"]: e for e in purchase.owed(root)}
    if task_id not in held:
        raise PolyweaveError(
            "fetch.no-task",
            f"nothing is owed for task {task_id!r}",
            "name a task id purchase.held lists under owed",
            given=task_id,
            allowed=sorted(held),
        )
    owed_for = held[task_id]
    return S.delivered(owed_for["link"], owed_for["capture"], root)


@operation("picture.describe", spends=True)
def describe_picture(
    picture: Annotated[str, Param("an approved picture, under the project")],
    out: Annotated[str, Param("where the description goes; beside it if unset")] = None,
    *,
    service: Annotated[str, purchase.SERVICE] = None,
    root: Annotated[str, Param("the project whose ledger this is")] = ".",
) -> dict:
    """Turn an approved picture into the structured prompt 4.0 draws it from (§PW165).

    The service's describe call returns the picture as a `json_prompt`: a description,
    a background, its elements with their bounding boxes, and a style. It is written as
    a file beside the picture, `<name>.prompt.json`, with a record naming the picture
    it came from, so the next variation starts from the approved picture's own terms
    rather than a paraphrase. It is priced by the `describe` row of `prices`, and
    ledgered like anything else bought.
    """
    config = load(root)
    here = config.root
    name = config.service(service, model="describe")
    about = config.services()[name]
    base, key = _reached(name, about)
    source = here / picture
    if not source.is_file():
        raise PolyweaveError(
            "fetch.no-reference",
            f"there is no picture at {source} to describe",
            "name a picture under the project, as a path relative to its root",
        )
    price = _price(name, about.get("prices") or {}, "describe", None)
    order = S.Order(
        service=name, base=base, key=key, price=price, root=here,
        asked={
            "path": "ideogram-v4/describe",
            "payload": {"include_bbox": "true"},
            "files": {"image_file": (source.name, sent_bytes(source), _mime(source))},
            "describe": True,
            "digest": provenance.sha256_of(source)[0],
        },
        kept={
            "out": out or str(source.with_suffix(".prompt.json").relative_to(here)),
            "prompt": None,
            "reference": picture,
            "bought": "description",
            "engine": {"name": name, "model": "4.0"},
        },
    )
    return S.buy(ideogram.SERVICE, order)


@operation("picture.gate")
def gate(
    candidates: Annotated[list, Param("the pictures bought for one asset, by path")],
    outline: Annotated[str, Param("the declared silhouette they must match")],
    *,
    family: Annotated[
        str, Param("the asset family whose canon they are held to")
    ] = None,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Settle the silhouette on the pictures, before a mesh is bought from one (§PW168).

    Each candidate must be a drawing (real alpha, a clear border), fill enough of the
    frame and touch no edge of it, match the declared outline by IoU against
    `[tolerance] silhouette_iou`, and, where the project declares a style, not drift
    from its family's canon. A picture costs cents and a mesh thirty credits, so this
    is where the outline is refused.

    **A failure is a record, not a re-roll**: each candidate's failures are written
    beside it as `<name>.gate.json`, with the prompt it was bought with, so the next
    prompt is corrected from them. **No taste enters the choice**: of those that pass,
    the highest IoU is `chosen`, and where none passes nothing is.
    """
    from polyweave.kernel.image import load as load_image
    from polyweave.layers.geometry import shape
    from polyweave.layers.reference import reference

    config = load(root)
    here = config.root
    coverage = config.tolerances().subject_coverage
    floor = config.tolerances().alpha_floor
    styled = style.in_force(config, family) is not None
    framed_outline = _framed(here / outline, config)
    looked = []
    for candidate in candidates:
        path = here / candidate
        image = load_image(path)
        failed: list[str] = []
        if not reference.is_drawing(image):
            failed.append("not a drawing: no real alpha, or a border that is not clear")
        mask = image.subject(floor)
        filled = round(float(mask.mean()), 4)
        if filled < coverage:
            failed.append(f"fills {filled} of the frame, under {coverage}")
        edges = reference._touching(mask)
        if edges:
            failed.append(f"runs off the {', '.join(edges)} of the frame")
        # Shapes compared framed alike (§PW194): a service draws its subject where it
        # likes in the frame, and a render fills its own, so raw IoU measured placement.
        held = shape.check(
            str(_framed(path, config)), against=str(framed_outline), root=here
        )
        if not held["holds"]:
            failed.append(
                f"{held['why']}; the centroid is {held['centroid_offset']}px out and "
                f"the box differs by {held['bbox_delta']}px"
            )
        drifted = style.drift(candidate, family, root=here) if styled else None
        if drifted and drifted["passed"] is False:
            failed.extend(
                f"{key} drifted: {drifted['measures'][key].get('which_way', 'off')}"
                for key in drifted["drifted"]
            )
        lettering = letters(candidate, root=here)
        failed.extend(
            f"lettering: asked for {one['asked']!r}, read {one['read']!r}"
            for one in lettering["texts"]
            if one["passed"] is False
        )
        unchecked = [
            f"lettering {one['asked']!r}: no OCR engine to read it"
            for one in lettering["texts"]
            if one["passed"] is None
        ]
        if drifted and not drifted["judged"]:
            unchecked.append(f"style: {drifted['floor']}")
        found = {
            "picture": candidate,
            "passed": not failed,
            "silhouette_iou": held["silhouette_iou"],
            "failed": failed,
            "style_judged": bool(drifted and drifted["judged"]),
            # Declared lettering with no engine to read it is named, never passed.
            "lettering_unchecked": [
                one["asked"] for one in lettering["texts"] if one["passed"] is None
            ],
            # The numbers behind a refusal, so a person decides with the same facts the
            # agent used (§PW175): each drifted measure's value, floor and direction.
            "drift": {
                key: {
                    k: drifted["measures"][key].get(k)
                    for k in ("value", "canon", "floor", "which_way")
                }
                for key in (drifted or {}).get("drifted", ())
            },
            "unchecked": unchecked,
            "bought": _bought(path, here),
        }
        _written_against(path, found, here)
        looked.append(found)
    passing = [one for one in looked if one["passed"]]
    chosen = max(passing, key=lambda one: one["silhouette_iou"]) if passing else None
    answer = {
        "chosen": chosen["picture"] if chosen else None,
        "why": "the highest silhouette IoU of those that passed"
        if chosen
        else "none passed; each one's failures are written beside it",
        "candidates": looked,
        "not_checked": list(style.NOT_CHECKED[:1]),
    }
    answer["id"] = _logged(answer, outline=outline, family=family, config=config)
    return answer


#: Every gate's answer, one line each, so the page can show the refused beside the kept
#: (§PW175): a filter nobody can see into is a filter nobody audits.
GATES = "gates.jsonl"


def _logged(answer: dict, *, outline: str, family, config) -> str:
    import uuid
    from datetime import UTC, datetime

    line = {
        "id": uuid.uuid4().hex[:12],
        "at": datetime.now(tz=UTC).isoformat(timespec="seconds"),
        "outline": outline,
        "family": family,
        **answer,
    }
    path = config.path("paths.work") / GATES
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as appended:
        appended.write(json.dumps(line, sort_keys=True) + "\n")
    return line["id"]


def _bought(path, here) -> dict | None:
    """What a candidate cost and from which service, off the ledger."""
    entry = purchase.find(provenance.sha256_of(path)[0], root=here)
    if not entry:
        return None
    return {"credits": entry.get("credits"), "service": entry.get("service")}


def gates(root=".") -> list[dict]:
    """Every gate this project ran, oldest first."""
    from polyweave.kernel.files import read_text_retrying

    text = read_text_retrying(load(root).path("paths.work") / GATES) or ""
    return [json.loads(line) for line in text.splitlines() if line.strip()]


#: A project's `[capture] locale` as the reader's language, so a game in Portuguese is
#: read in Portuguese and its accents are letters rather than noise. Anything not here
#: is passed as `languages`.
LANGUAGES = {
    "en": "eng",
    "pt": "por",
    "es": "spa",
    "fr": "fra",
    "de": "deu",
    "it": "ita",
}


@operation("picture.letters")
def letters(
    picture: Annotated[str, Param("the picture, under the project")],
    texts: Annotated[
        list, Param("the lettering it must carry; its record's text elements if unset")
    ] = None,
    *,
    languages: Annotated[
        str, Param("the reader's languages, as tesseract names them")
    ] = (None),
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Read the lettering back off a picture and hold it to what was asked (§PW169).

    The text a picture must carry is the text elements of the structured prompt it was
    bought with, or `texts`. The comparison folds case and whitespace and **never folds
    accents**, because a dropped accent is the defect. Where no OCR engine is installed
    the picture is reported unchecked, by name, and never passed.
    """
    import difflib
    import shutil

    config = load(root)
    path = config.root / picture
    asked = list(texts) if texts is not None else _declared_text(path, config.root)
    if not asked:
        return {
            "picture": picture,
            "checked": False,
            "passed": None,
            "texts": [],
            "why": "no lettering was declared for this picture",
        }
    engine = shutil.which(str(config.path("paths.tesseract")))
    if not engine:
        return {
            "picture": picture,
            "checked": False,
            "passed": None,
            "texts": [{"asked": one, "read": None, "passed": None} for one in asked],
            "why": f"no OCR engine at {config.path('paths.tesseract')}: the lettering "
            f"is unchecked, which is not a pass",
        }
    locale = str(config.get("capture.locale") or "").split("_")[0].lower()
    language = languages or LANGUAGES.get(locale, "eng")
    read = _read_letters(engine, path, language)
    lines = [_folded(line) for line in read.splitlines() if line.strip()]
    whole = _folded(read)
    found = []
    for one in asked:
        wanted = _folded(one)
        near = difflib.get_close_matches(wanted, lines, n=1, cutoff=0.0)
        found.append(
            {
                "asked": one,
                "read": wanted if wanted in whole else (near[0] if near else ""),
                "passed": wanted in whole,
            }
        )
    return {
        "picture": picture,
        "checked": True,
        "passed": all(one["passed"] for one in found),
        "texts": found,
        "languages": language,
        "why": "",
    }


def _declared_text(path, here) -> list[str]:
    """The text elements of the structured prompt a picture was bought with."""
    try:
        record = provenance.read(path, root=here)
    except PolyweaveError:
        return []
    prompt = (record.get("details") or {}).get("json_prompt") or {}
    elements = (prompt.get("compositional_deconstruction") or {}).get("elements") or []
    return [e["text"] for e in elements if e.get("type") == "text" and e.get("text")]


def _folded(text: str) -> str:
    """Case and whitespace folded, accents kept: they are the letters at risk."""
    return " ".join(str(text).casefold().split())


#: How long the OCR engine may take over one picture.
OCR_TIMEOUT = 120


def _read_letters(engine: str, path, language: str) -> str:
    """What the OCR engine reads off the picture."""
    import subprocess

    done = subprocess.run(  # noqa: S603 - the engine is the project's own binary
        [engine, str(path), "stdout", "-l", language],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=OCR_TIMEOUT,
        check=False,
    )
    if done.returncode != 0:
        raise PolyweaveError(
            "fetch.ocr-failed",
            f"the OCR engine could not read {path}",
            f"check that the {language} language data is installed for it",
            detail=(done.stderr or "")[:400],
        )
    return done.stdout


#: The square both silhouettes are framed into before the gate compares them, and the
#: room left round the subject in it.
FRAMED, FRAMED_MARGIN = 256, 8


def _framed(path, config):
    """A picture's subject trimmed to its alpha and fitted, aspect kept, in one square.

    Where the subject sits and how much of the frame it fills are the service's choice
    and the renderer's, not the shape's, and compared raw they swamped it: Starship's
    Motes filled a twentieth of a 1024 frame against an outline filling a sixth of 256,
    and scored 0.46 for the right shape (§PW194). Coverage and edges are still checked
    on the picture as it is, because those are what the mesh service is sent.
    """
    import hashlib

    from PIL import Image as PILImage

    from polyweave.kernel.image import load as load_image

    image = load_image(path)
    mask = image.subject(config.tolerances().alpha_floor)
    target = (
        config.path("paths.work")
        / "gate"
        / (hashlib.sha256(image.rgba.tobytes()).hexdigest()[:16] + ".png")
    )
    if target.is_file():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    rows, columns = mask.nonzero()
    if not len(rows):
        PILImage.fromarray(image.rgba).save(target)
        return target
    box = (
        int(columns.min()),
        int(rows.min()),
        int(columns.max()) + 1,
        int(rows.max()) + 1,
    )
    subject = PILImage.fromarray(image.rgba).crop(box)
    room = FRAMED - 2 * FRAMED_MARGIN
    scale = room / max(subject.width, subject.height)
    size = (max(1, round(subject.width * scale)), max(1, round(subject.height * scale)))
    fitted = subject.resize(size, PILImage.Resampling.LANCZOS)
    # A silhouette is inside or outside. Soft edges resampled at two different scales
    # blur two copies of one shape apart, so alpha is cut at half once the size is set.
    alpha = np.asarray(fitted.getchannel("A")) >= 128
    fitted.putalpha(PILImage.fromarray((alpha * 255).astype(np.uint8)))
    square = PILImage.new("RGBA", (FRAMED, FRAMED), (0, 0, 0, 0))
    square.paste(fitted, ((FRAMED - size[0]) // 2, (FRAMED - size[1]) // 2))
    square.save(target)
    return target


def _written_against(path, found: dict, here) -> None:
    """The gate's answer beside the picture, with the prompt that bought it."""
    digest, _ = provenance.sha256_of(path)
    bought = purchase.find(digest, root=here) or {}
    record = {**found, "prompt": bought.get("prompt"), "sha256": digest}
    beside = path.with_suffix(".gate.json")
    write_atomic(beside, json.dumps(record, indent=2, sort_keys=True) + "\n")


def _one_prompt(prompt: str | None, json_prompt: dict | None, model: str) -> None:
    """Exactly one of the two, and the structured one only where the model reads it."""
    if (prompt is None) == (json_prompt is None):
        raise PolyweaveError(
            "fetch.missing-field",
            "a picture takes a prompt or a json_prompt, and this call gave "
            + ("neither" if prompt is None else "both"),
            "pass json_prompt on 4.0, which is drawn as written, or a text prompt",
        )
    if json_prompt is not None and model != "4.0":
        raise PolyweaveError(
            "fetch.unknown-field",
            f"{model} takes no json_prompt; only 4.0 draws from a structured prompt",
            "pass a text prompt for 3.0, or ask 4.0",
            given="json_prompt",
            allowed=("prompt",),
        )


