"""ElevenLabs, which sells sound effects, spoken lines and designed voices (§PW190,
§PW314, §PW321, §PW516).

Every call is one JSON request with the `xi-api-key` header, answered at once: a sound
or a line with the audio, a voice design with its previews. A price by the character
is measured where the subscription answers its `character_count` either side of the
call (§PW320), and the account's tier is read for the record, since a free tier's
licence is what a sold game cannot use (§PW435).

What the domain asks is `call` (`audio` or `design`), the `route` after the base and
the `payload`; `rate` where the price is by the character; and, for a design, the
`folder` and `named` its previews land as.
"""

from __future__ import annotations

import base64
import hashlib
import json

from polyweave.kernel.errors import PolyweaveError

from . import client
from . import service as S

#: The routes: a sound effect, a line in a voice, a voice designed and one saved.
ROUTE = "/v1/sound-generation"
SPEAK = "/v1/text-to-speech/{voice}"
DESIGN = "/v1/text-to-voice/design"
SAVE = "/v1/text-to-voice"

#: Where the service says how many characters the account has used (§PW320).
USAGE = "/v1/user/subscription"
FORMAT = "mp3_44100_128"

TIMEOUT = 120


def submit(order: S.Order) -> dict:
    asked, base, key = order.asked, order.base, order.key
    tier_now = tier(base, key)
    before = used(base, key) if asked.get("rate") is not None else None
    if asked["call"] == "design":
        answer = {"answer": asked_json(f"{base}{DESIGN}", key, asked["payload"])}
    else:
        body, said = post(f"{base}{asked['route']}", key, asked["payload"])
        answer = {"body": body, "request_id": said}
    after = used(base, key) if before is not None else None
    spent = (
        round((after - before) * asked["rate"], 6)
        if before is not None and after is not None and after >= before
        else None
    )
    return {**answer, "tier": tier_now, "spent": spent}


def deliver(order: S.Order, sent: dict, finished: dict) -> S.Delivery:
    engine = {"tier": sent["tier"]} if sent["tier"] else {}
    if order.asked["call"] == "design":
        previews = [one for one in (sent["answer"].get("previews") or ())
                    if one.get("audio_base_64")]
        if not previews:
            raise PolyweaveError(
                "fetch.nothing-arrived",
                "the service answered with no preview of the voice",
                "reword the description; nothing was ledgered",
            )
        folder, named = order.asked["folder"], order.asked["named"]
        return S.Delivery(
            task="design",
            reported=sent["spent"],
            engine=engine,
            parts=tuple(
                S.Part(
                    task=str(one.get("generated_voice_id") or index),
                    body=base64.b64decode(one["audio_base_64"]),
                    out=f"{folder}/{named}_{index}.mp3",
                    details={"voice_preview": one.get("generated_voice_id")},
                )
                for index, one in enumerate(previews, start=1)
            ),
        )
    body = sent["body"]
    if not body:
        raise PolyweaveError(
            "fetch.nothing-arrived",
            "the service answered with no audio",
            "ask again; nothing was ledgered",
        )
    return S.Delivery(
        task=sent["request_id"] or hashlib.sha256(body).hexdigest()[:16],
        body=body, reported=sent["spent"], engine=engine,
    )


def plan_lacks(said: str) -> PolyweaveError:
    """A 403: the account's plan lacks the feature, in the service's own words (§PW410).

    ElevenLabs answers voice design on a free plan with a 403 whose message says so,
    and the refusal used to be a service error whose remedy named only 401 and 422.
    """
    from polyweave.kernel.errors import detail_line

    why = detail_line(said)
    return PolyweaveError(
        "fetch.plan-lacks",
        "the account's plan does not include this"
        + (f": {why}" if why else " (the service answered 403)"),
        "move the account to a plan that has it, or ask for what the plan has; "
        "nothing was ledgered, and a refused call is not charged",
        detail=said,
    )


def asked_json(url: str, key: str, payload: dict) -> dict:
    """One JSON request with the service's key header, answered with JSON."""
    try:
        answer = client.send(
            url, method="POST", data=json.dumps(payload).encode("utf-8"),
            headers={"xi-api-key": key, "Content-Type": "application/json",
                     "Accept": "application/json"},
            timeout=TIMEOUT,
        )
    except client.Unreached as exc:
        raise PolyweaveError(
            "fetch.service-error",
            f"the service could not be reached at {url}",
            "check the base under [service] and the network",
            detail=exc.reason,
        ) from exc
    if answer.status >= 400:
        said = answer.body[:400].decode("utf-8", "replace")
        if answer.status == 403:
            raise plan_lacks(said)
        raise PolyweaveError(
            "fetch.service-error",
            f"the service answered {answer.status}",
            "read the detail; a 401 is a key the service does not accept, or an "
            "account out of credits, and a 422 words it would not use",
            detail=said,
        )
    said = json.loads(answer.body or b"{}")
    return said if isinstance(said, dict) else {}


def post(url: str, key: str, payload: dict) -> tuple[bytes, str]:
    """One request with the service's key header, answered with audio and its id."""
    try:
        answer = client.send(
            url, method="POST", data=json.dumps(payload).encode("utf-8"),
            headers={"xi-api-key": key, "Content-Type": "application/json",
                     "Accept": "audio/mpeg"},
            timeout=TIMEOUT,
        )
    except client.Unreached as exc:
        raise PolyweaveError(
            "fetch.service-error",
            f"the service could not be reached at {url}",
            "check the base under [service] and the network",
            detail=exc.reason,
        ) from exc
    if answer.status < 400:
        return answer.body, answer.headers.get("request-id", "")
    said = answer.body[:400].decode("utf-8", "replace")
    if answer.status == 422:
        raise PolyweaveError(
            "fetch.prompt-refused",
            "the service would not make a sound from those words",
            "reword the prompt; nothing was ledgered",
            detail=said,
        )
    if answer.status == 429:
        raise PolyweaveError(
            "fetch.rate-limited",
            "the service has more requests from this account than it allows",
            "wait, then ask again",
            detail=said,
        )
    if answer.status == 403:
        raise plan_lacks(said)
    raise PolyweaveError(
        "fetch.service-error",
        f"the service answered {answer.status}",
        "read the detail; a 401 is a key the service does not accept, or an "
        "account out of credits, and a 400 a request it does not",
        detail=said,
    )


def subscription(base: str, key: str) -> dict | None:
    """What the account's subscription says, or None where the service will not say."""
    try:
        answer = client.send(f"{base}{USAGE}", timeout=TIMEOUT,
                             headers={"xi-api-key": key, "Accept": "application/json"})
        said = json.loads(answer.body) if answer.status < 400 else None
    except (client.Unreached, OSError, ValueError):
        return None
    return said if isinstance(said, dict) else None


def used(base: str, key: str) -> int | None:
    """The characters the account has used, or None where the service will not say.

    Read before and after a call priced by the character, so its spend is measured; a
    reading that fails leaves the quoted price standing, never a guess (§PW320).
    """
    count = (subscription(base, key) or {}).get("character_count")
    return count if isinstance(count, int) and not isinstance(count, bool) else None


def tier(base: str, key: str) -> str | None:
    """The account's tier, kept in each take's record so a free one's licence is never
    forgotten (§PW435); None where the service will not say, never a guess."""
    said = (subscription(base, key) or {}).get("tier")
    return said.lower() if isinstance(said, str) and said.strip() else None


SERVICE = S.Service(
    name="elevenlabs", media=("sound",), hosts=("elevenlabs",),
    submit=submit, deliver=deliver,
)
