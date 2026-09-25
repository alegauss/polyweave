"""Buying a picture, which is the cheap step in front of the dear one (§PW163).

The plugin prefers a drawing to a photograph (§PW21), and until now every drawing came
from a person, because the agent cannot draw. Ideogram generates one, and its
transparent endpoint delivers a PNG with a real alpha channel, which is the form
`reference.pick` reads as a drawing. A picture costs cents where the mesh it steers
costs thirty credits.

**This is the first service the plugin speaks to itself.** Until now a consumer's own
client fetched and the plugin captured. The client here is small, and it goes through
the same doors a mesh does, in the same order:

    1. the payload is checked against the learned schema, where one is learned (§PW19)
    2. `purchase.allow` is asked, against this service's own ceiling (§PW18, §PW162)
    3. the request is sent, and a refusal is a code rather than a traceback
    4. the picture is captured before anything else happens (§PW17), because the
       service's links expire and that order is the only one that cannot leave a
       receipt without an asset

The call is synchronous: the service answers with the picture's link. Its asynchronous
variants, with their poll, are not here yet.
"""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
import uuid
from typing import Annotated

from . import provenance, purchase, schema, style
from .config import load
from .describe import Param, operation
from .errors import PolyweaveError
from .files import write_atomic

#: The models this client knows the request shape of. They spell the prompt field
#: differently, which is the reason the choice is a parameter and not a guess.
MODELS = {"4.0": ("ideogram-v4", "text_prompt"), "3.0": ("ideogram-v3", "prompt")}

#: What the service allows in flight on an account by default. More than this and it
#: answers 429, so the client never holds more open than this in one process.
INFLIGHT = 10
_inflight = threading.BoundedSemaphore(INFLIGHT)

#: How long one request may take before it is called failed. A picture takes seconds.
TIMEOUT = 120


@operation("picture.buy")
def buy(
    out: Annotated[str, Param("where it is written, under the project")],
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
    """
    if model not in MODELS:
        raise PolyweaveError(
            "fetch.bad-choice",
            f"there is no model {model!r} this client knows the request shape of",
            f"pass one of {', '.join(MODELS)}",
            given=model,
            allowed=MODELS,
        )
    _one_prompt(prompt, json_prompt, model)
    config = load(root)
    held_to = style.in_force(config, family)
    if held_to is not None:
        if json_prompt is None:
            raise PolyweaveError(
                "style.needs-structure",
                f"the {held_to[0]} style is carried by a structured prompt, and this "
                f"call gave text",
                "pass json_prompt on 4.0; its style block starts from the family's "
                "skeleton and its palette is the family's",
            )
        json_prompt = style.compose(json_prompt, held_to[1])
    name = config.service(service)
    about = config.services()[name]
    base, key = _reached(name, about)
    price = _price(name, about.get("prices") or {}, model, rendering_speed)

    path, prompt_field = MODELS[model]
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

    purchase.allow(price, root=root, service=name)

    endpoint = f"{base.rstrip('/')}/v1/{path}/generate"
    if transparent:
        endpoint += "-transparent"
    answer = _answered(endpoint, key, payload)
    drawn = (answer.get("data") or [{}])[0]
    link = drawn.get("url")
    if not link:
        raise PolyweaveError(
            "fetch.prompt-refused"
            if drawn.get("is_image_safe") is False
            else "fetch.nothing-arrived",
            "the service answered with no picture to take delivery of",
            "reword the prompt; a picture the service calls unsafe comes back "
            "without a link, and nothing was ledgered",
            detail=json.dumps(answer)[:400],
        )

    body = _download(link)
    # The service bills per picture returned, so an answer carrying more than was asked
    # for is charged as many prices, although only the first is kept.
    returned = max(1, len(answer.get("data") or ()))
    entry = purchase.capture(
        body,
        out=out,
        # The synchronous answer carries no id of its own, so the id is what it does
        # carry: when it was made and the seed it was made with.
        task_id=f"{name}:{answer.get('created')}:{drawn.get('seed')}",
        credits=round(price * returned, 4),
        outputs=returned,
        prompt=sent,
        bought="image",
        engine={"name": name, "model": model},
        service=name,
        details={
            "model": model,
            "transparent": bool(transparent),
            "rendering_speed": rendering_speed,
            "aspect_ratio": aspect_ratio,
            "resolution": drawn.get("resolution"),
            # What it reports, which is the seed a second call asks for.
            "seed": drawn.get("seed"),
            "json_prompt": json_prompt,
            "family": held_to[0] if held_to else None,
            # What the service says it drew from. On a text prompt to 4.0 this is not
            # what was sent, and it is the only account of the picture that is true.
            "returned_prompt": drawn.get("prompt"),
        },
        root=root,
    )
    return entry


@operation("picture.describe")
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
    name = config.service(service)
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
    purchase.allow(price, root=here, service=name)

    answer = _answered(
        f"{base.rstrip('/')}/v1/ideogram-v4/describe",
        key,
        {"include_bbox": "true"},
        files={"image_file": (source.name, source.read_bytes(), _mime(source))},
    )
    described = answer.get("json_prompt")
    if not isinstance(described, dict):
        raise PolyweaveError(
            "fetch.nothing-arrived",
            "the service answered with no structured description",
            "ask again; nothing was ledgered",
            detail=json.dumps(answer)[:400],
        )
    target = out or str(source.with_suffix(".prompt.json").relative_to(here))
    return purchase.capture(
        (json.dumps(described, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        out=target,
        task_id=f"{name}:describe:{provenance.sha256_of(source)[0][:16]}",
        credits=price,
        prompt=None,
        reference=picture,
        bought="description",
        engine={"name": name, "model": "4.0"},
        service=name,
        root=here,
    )


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
    from . import reference, shape
    from .image import load as load_image

    config = load(root)
    here = config.root
    coverage = config.tolerances().subject_coverage
    floor = config.tolerances().alpha_floor
    styled = style.in_force(config, family) is not None
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
        held = shape.check(str(path), against=outline, root=here)
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
        found = {
            "picture": candidate,
            "passed": not failed,
            "silhouette_iou": held["silhouette_iou"],
            "failed": failed,
            "style_judged": bool(drifted and drifted["judged"]),
        }
        _written_against(path, found, here)
        looked.append(found)
    passing = [one for one in looked if one["passed"]]
    chosen = max(passing, key=lambda one: one["silhouette_iou"]) if passing else None
    return {
        "chosen": chosen["picture"] if chosen else None,
        "why": "the highest silhouette IoU of those that passed"
        if chosen
        else "none passed; each one's failures are written beside it",
        "candidates": looked,
        "not_checked": list(style.NOT_CHECKED[:1]),
    }


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


def _mime(path) -> str:
    return {".png": "image/png", ".webp": "image/webp"}.get(
        path.suffix.lower(), "image/jpeg"
    )


def _price(name: str, prices: dict, model: str, speed: str | None) -> float:
    """What one picture costs, from the declared table, or a refusal (§PW164).

    A row is `<model>:<speed>`, or `<model>` for the speed the service defaults to. A
    call with no row is refused rather than priced at zero: under-counting is the
    direction that lets a session pass a ceiling a person set.
    """
    row = f"{model}:{speed}" if speed else model
    if row in prices:
        return float(prices[row])
    raise PolyweaveError(
        "fetch.unpriced",
        f"[service.{name}] prices has no row {row!r}, so what the picture costs is "
        f"not known",
        f"add {row!r} = <price of one picture> to [service.{name}] prices, in the "
        f"unit of its ceiling",
        given=row,
        allowed=sorted(prices),
    )


def _reached(name: str, about: dict) -> tuple[str, str]:
    """Where the service is and the key it takes, refused before anything is sent."""
    if not about.get("base"):
        raise PolyweaveError(
            "fetch.service-unconfigured",
            f"[service.{name}] names no base, so there is nowhere to send the request",
            f'set base = "https://api.ideogram.ai" under [service.{name}]',
        )
    variable = about.get("key_env")
    key = os.environ.get(variable) if variable else None
    if not key:
        raise PolyweaveError(
            "fetch.service-unconfigured",
            f"the key for {name} is not set here"
            + (f": {variable} is empty" if variable else ", and no key_env names it"),
            f"export {variable or 'the variable'} in this environment, and name it as "
            f"key_env under [service.{name}]; the key itself never goes in the file",
        )
    return about["base"], key


def _answered(
    endpoint: str, key: str, payload: dict, files: dict | None = None
) -> dict:
    """Send one request and read its answer, turning a refusal into a code."""
    status, body = _send(endpoint, key, payload, files)
    if status == 200:
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise PolyweaveError(
                "fetch.service-error",
                "the service answered 200 with something that is not JSON",
                "try again; nothing was charged to the ledger",
                detail=body[:400].decode("utf-8", "replace"),
            ) from exc
    said = body[:400].decode("utf-8", "replace")
    if status == 422:
        raise PolyweaveError(
            "fetch.prompt-refused",
            "the service refused the prompt as failing its safety check",
            "reword the prompt; a refused request is not charged",
            detail=said,
        )
    if status == 429:
        raise PolyweaveError(
            "fetch.rate-limited",
            "the service has more requests from this account in flight than it allows",
            "wait for the calls already out to finish, then ask again",
            detail=said,
        )
    raise PolyweaveError(
        "fetch.service-error",
        f"the service answered {status}",
        "read the detail; a 401 is a key the service does not accept, and a 400 "
        "a payload it does not",
        detail=said,
    )


def _send(
    endpoint: str, key: str, payload: dict, files: dict | None = None
) -> tuple[int, bytes]:
    """POST the payload as a form, holding no more calls open than the account may.

    `files` maps a field to `(filename, bytes, content type)`, for a picture sent up.
    """
    boundary = uuid.uuid4().hex
    parts: list[bytes] = []
    for field, value in payload.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"\r\n\r\n'
            f"{value}\r\n".encode()
        )
    for field, (filename, content, kind) in (files or {}).items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; '
            f'filename="{filename}"\r\nContent-Type: {kind}\r\n\r\n'.encode()
            + content
            + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode())
    request = urllib.request.Request(  # noqa: S310 - the base is the project's own
        endpoint,
        data=b"".join(parts),
        method="POST",
        headers={
            "Api-Key": key,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    with _inflight:
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:  # noqa: S310
                return answer.status, answer.read()
        except urllib.error.HTTPError as refused:
            return refused.code, refused.read()
        except urllib.error.URLError as exc:
            raise PolyweaveError(
                "fetch.service-error",
                f"the service could not be reached at {endpoint}",
                "check the base under [service] and the network; nothing was spent",
                detail=str(exc.reason),
            ) from exc


def _download(link: str) -> bytes:
    """The picture's bytes, fetched at once: the link the service gives expires."""
    try:
        with urllib.request.urlopen(link, timeout=TIMEOUT) as answer:  # noqa: S310
            return answer.read()
    except urllib.error.URLError as exc:
        raise PolyweaveError(
            "fetch.nothing-arrived",
            "the picture was made and paid for, and its link could not be read",
            "read the link again at once, before it expires; nothing was ledgered, "
            "so the spend is not yet counted against the ceiling",
            detail=f"{link}: {getattr(exc, 'reason', exc)}",
        ) from exc
