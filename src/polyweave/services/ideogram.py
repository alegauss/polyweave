"""Ideogram, which sells pictures and their structured descriptions (§PW163, §PW516).

Every call is a form POST with the `Api-Key` header. A generation on 4.0 is
asynchronous: the answer is a generation id at once, asked after until it is drawn. 3.0
has no asynchronous route, and its picture is in the first answer, as is every remix,
edit, reframe and description. The service bills per picture returned, and says what it
charged where the ceiling counts dollars.

What the domain asks is `path` (after `/v1/`), `payload` and `files`, and, for a
description, `describe` and the picture's `digest`; `prefix` begins the task id of an
answer that carries no generation id, and `unit` is the ceiling's.
"""

from __future__ import annotations

import json
import threading
import time
import uuid

from polyweave.kernel.errors import PolyweaveError

from . import client
from . import service as S

#: The models this client knows the request shape of: their path, how they spell the
#: prompt field, and whether they have an asynchronous route. 3.0's `async/generate`
#: answers 404, its synchronous `generate` and `generate-transparent` the picture in the
#: body (§PW437, probed 2026-10-13 with an empty request, which draws nothing).
MODELS = {
    "4.0": ("ideogram-v4", "text_prompt", True),
    "3.0": ("ideogram-v3", "prompt", False),
}

#: What the service allows in flight on an account by default. More than this and it
#: answers 429, so the client never holds more open than this in one process.
INFLIGHT = 10
_inflight = threading.BoundedSemaphore(INFLIGHT)

#: How long one request may take before it is called failed. A picture takes seconds.
TIMEOUT = 120

#: How long a generation may stay pending before the call gives up on it, and how
#: often it is asked. A poll that is never answered ends here rather than holding a
#: slot of the account's ten for ever.
POLL_TIMEOUT = 300
POLL_EVERY = 2.0


def generation(model: str, transparent: bool) -> str:
    """The path a generation on `model` is sent to (§PW178).

    The asynchronous route where the model has one: the answer is a generation id at
    once, and the connection is not held while the picture is drawn. 3.0 has none, and
    sent there every 3.0 picture failed with a 404 (§PW437).
    """
    path, _, asynchronous = MODELS[model]
    route = "async/generate" if asynchronous else "generate"
    return f"{path}/{route}" + ("-transparent" if transparent else "")


def submit(order: S.Order) -> dict:
    asked = order.asked
    return answered(f"{order.base.rstrip('/')}/v1/{asked['path']}", order.key,
                    asked["payload"], asked.get("files"))


def poll(order: S.Order, answer: dict, report) -> dict:
    if answer.get("generation_id") and not answer.get("data"):
        return polled(order.base, order.key, answer["generation_id"], report)
    return answer


def deliver(order: S.Order, sent: dict, answer: dict) -> S.Delivery:
    asked = order.asked
    if asked.get("describe"):
        described = answer.get("json_prompt")
        if not isinstance(described, dict):
            raise PolyweaveError(
                "fetch.nothing-arrived",
                "the service answered with no structured description",
                "ask again; nothing was ledgered",
                detail=json.dumps(answer)[:400],
            )
        return S.Delivery(
            task=f"describe:{asked['digest'][:16]}",
            body=(json.dumps(described, indent=2, sort_keys=True) + "\n").encode(),
        )
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
    return S.Delivery(
        # The generation id where there is one; an answer without one is identified by
        # what it does carry, when it was made and the seed it was made with.
        task=answer.get("generation_id")
        or f"{asked.get('prefix', '')}{answer.get('created')}:{drawn.get('seed')}",
        link=link,
        # The service bills per picture returned, so an answer carrying more than was
        # asked for is charged as many prices, although only the first is kept.
        outputs=max(1, len(answer.get("data") or ())),
        reported=reported(answer, asked.get("unit")),
        details={
            "resolution": drawn.get("resolution"),
            # What it reports, which is the seed a second call asks for.
            "seed": drawn.get("seed"),
            # What the service says it drew from. On a text prompt to 4.0 this is not
            # what was sent, and it is the only account of the picture that is true.
            "returned_prompt": drawn.get("prompt"),
        },
    )


def polled(base: str, key: str, generation: str, report) -> dict:
    """Ask after one generation until it is done, failed or out of time."""
    started = time.monotonic()
    while True:
        status, body = get(f"{base.rstrip('/')}/v1/generations/{generation}", key)
        if status != 200:
            raise PolyweaveError(
                "fetch.service-error",
                f"asking after generation {generation} was answered {status}",
                "read the detail; nothing was ledgered",
                detail=body[:400].decode("utf-8", "replace"),
            )
        answer = json.loads(body)
        state = answer.get("status")
        if state == "completed":
            return {
                **answer,
                "generation_id": answer.get("generation_id") or generation,
            }
        if state == "failed":
            raise PolyweaveError(
                "fetch.service-error",
                f"generation {generation} failed: "
                f"{answer.get('failure_reason') or 'no reason given'}",
                "reword the prompt or ask again; nothing was ledgered",
                detail=json.dumps(answer)[:400],
            )
        waited = time.monotonic() - started
        if waited > POLL_TIMEOUT:
            raise PolyweaveError(
                "fetch.service-error",
                f"generation {generation} was still {state} after {POLL_TIMEOUT}s",
                f"ask after it later by its id, {generation}; nothing was ledgered",
            )
        if report is not None:
            report.stage(
                "building",
                progress=min(0.8, waited / POLL_TIMEOUT),
                note=f"generation {generation} is {state}",
            )
        time.sleep(POLL_EVERY)


def reported(answer: dict, unit: str | None) -> float | None:
    """What the service reports a generation cost, in the ceiling's unit, if it does."""
    micros = answer.get("usage_cost_usd_micros")
    if micros is None or str(unit).upper() != "USD":
        return None
    return round(float(micros) / 1_000_000, 6)


def get(url: str, key: str) -> tuple[int, bytes]:
    """GET one URL with the key, inside the account's allowance of calls in flight."""
    with _inflight:
        try:
            answer = client.send(url, headers={"Api-Key": key}, timeout=TIMEOUT)
        except client.Unreached as exc:
            raise PolyweaveError(
                "fetch.service-error",
                f"the service could not be reached at {url}",
                "check the base under [service] and the network",
                detail=exc.reason,
            ) from exc
    return answer.status, answer.body


def answered(
    endpoint: str, key: str, payload: dict, files: dict | list | None = None
) -> dict:
    """Send one request and read its answer, turning a refusal into a code."""
    status, body = send(endpoint, key, payload, files)
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


def send(
    endpoint: str, key: str, payload: dict, files: dict | list | None = None
) -> tuple[int, bytes]:
    """POST the payload as a form, holding no more calls open than the account may.

    `files` maps a field to `(filename, bytes, content type)`, for a picture sent up,
    or is a list of `(field, (filename, bytes, type))` where a field repeats (§PW180).
    """
    boundary = uuid.uuid4().hex
    parts: list[bytes] = []
    for field, value in payload.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"\r\n\r\n'
            f"{value}\r\n".encode()
        )
    sent_up = files.items() if isinstance(files, dict) else (files or ())
    for field, (filename, content, kind) in sent_up:
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; '
            f'filename="{filename}"\r\nContent-Type: {kind}\r\n\r\n'.encode()
            + content
            + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode())
    with _inflight:
        try:
            answer = client.send(
                endpoint,
                method="POST",
                data=b"".join(parts),
                headers={
                    "Api-Key": key,
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                },
                timeout=TIMEOUT,
            )
        except client.Unreached as exc:
            raise PolyweaveError(
                "fetch.service-error",
                f"the service could not be reached at {endpoint}",
                "check the base under [service] and the network; nothing was spent",
                detail=exc.reason,
            ) from exc
    return answer.status, answer.body


SERVICE = S.Service(
    name="ideogram", media=("image", "description"), hosts=("ideogram",),
    submit=submit, poll=poll, deliver=deliver,
)
