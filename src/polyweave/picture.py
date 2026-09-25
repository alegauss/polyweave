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

from . import purchase, schema
from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

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
    prompt: Annotated[str, Param("what the picture shows")],
    out: Annotated[str, Param("where it is written, under the project")],
    *,
    transparent: Annotated[bool, Param("a PNG with alpha, read as a drawing")] = True,
    model: Annotated[str, Param("the model", choices=tuple(MODELS))] = "4.0",
    aspect_ratio: Annotated[str, Param("as the service spells it")] = None,
    rendering_speed: Annotated[str, Param("as the service spells it")] = None,
    seed: Annotated[int, Param("for a picture that can be asked for again")] = None,
    service: Annotated[str, purchase.SERVICE] = None,
    root: Annotated[str, Param("the project whose ledger this is")] = ".",
) -> dict:
    """Buy one picture against the service's ceiling and keep it before anything else.

    Returns the ledger entry, with where the picture landed. Nothing is spent where the
    ceiling would not allow it, where the key is not set, where no price is declared for
    the model and speed, or where the payload names a field the learned schema does not
    carry. The price is the project's `prices` table, never the caller's figure, and the
    entry says it was quoted rather than measured (§PW164).
    """
    if model not in MODELS:
        raise PolyweaveError(
            "fetch.bad-choice",
            f"there is no model {model!r} this client knows the request shape of",
            f"pass one of {', '.join(MODELS)}",
            given=model,
            allowed=MODELS,
        )
    config = load(root)
    name = config.service(service)
    about = config.services()[name]
    base, key = _reached(name, about)
    price = _price(name, about.get("prices") or {}, model, rendering_speed)

    path, prompt_field = MODELS[model]
    payload: dict = {prompt_field: prompt}
    for field, value in (
        ("aspect_ratio", aspect_ratio),
        ("rendering_speed", rendering_speed),
        ("seed", seed),
    ):
        if value is not None:
            payload[field] = value
    # Checked where a schema has been learned. The fields above are this client's own,
    # so where nothing is learned there is no caller's typo for a check to catch.
    if schema.read(root, name).get("field"):
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
        prompt=prompt,
        bought="image",
        engine={"name": name, "model": model},
        service=name,
        details={
            "model": model,
            "transparent": bool(transparent),
            "rendering_speed": rendering_speed,
            "resolution": drawn.get("resolution"),
            "seed": drawn.get("seed"),
        },
        root=root,
    )
    return entry


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


def _answered(endpoint: str, key: str, payload: dict) -> dict:
    """Send one request and read its answer, turning a refusal into a code."""
    status, body = _send(endpoint, key, payload)
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


def _send(endpoint: str, key: str, payload: dict) -> tuple[int, bytes]:
    """POST the payload as a form, holding no more calls open than the account may."""
    boundary = uuid.uuid4().hex
    parts = []
    for field, value in payload.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"\r\n\r\n'
            f"{value}\r\n"
        )
    parts.append(f"--{boundary}--\r\n")
    request = urllib.request.Request(  # noqa: S310 - the base is the project's own
        endpoint,
        data="".join(parts).encode("utf-8"),
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
