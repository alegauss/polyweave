"""What every paid service is reached through: the request, the key, the price and
the bytes that come back (§PW516).

Each service still reads its own refusals into its own codes, because what a 402 or a
422 means is the service's; what is shared is the transport, so the timeout, the agent
string and an unreachable host are one thing however many services there are.
`send` answers every status, refusals included, and raises `Unreached` only where
nothing answered.
"""

from __future__ import annotations

import json  # noqa: F401 - read by the moved helpers
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np

from polyweave import __version__
from polyweave.kernel.errors import PolyweaveError

AGENT = f"polyweave/{__version__} (+https://github.com/alegauss/polyweave)"

#: How long one request may take before it is given up, in seconds.
TIMEOUT = 120


class Answer(NamedTuple):
    status: int
    body: bytes
    headers: Any


class Unreached(Exception):
    """Nothing answered: the host, the network or the name was wrong."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def send(url: str, *, method: str = "GET", data: bytes | None = None,
         headers: dict | None = None, timeout: float = TIMEOUT) -> Answer:
    """One request, answered whatever its status, with the agent string set."""
    request = urllib.request.Request(  # noqa: S310 - the base is the project's own
        url, data=data, headers={**(headers or {}), "User-Agent": AGENT}, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as answer:  # noqa: S310
            return Answer(answer.status, answer.read(), getattr(answer, "headers", {}))
    except urllib.error.HTTPError as refused:
        return Answer(refused.code, refused.read(), getattr(refused, "headers", {}))
    except urllib.error.URLError as exc:
        raise Unreached(str(getattr(exc, "reason", exc))) from exc


def sent_bytes(path) -> bytes:
    """A picture as it is sent to a service: the colour under full transparency cleared.

    A generator's transparent PNG keeps whatever colour it drew under alpha zero, and a
    service that ignores alpha (3.0's inpaint, remix and reframe) shows it. Starship's
    edited Mote came back ringed in green noise that had been invisible, and every pixel
    of it counted as changed (§PW195). Clearing it to black leaves the picture as a
    viewer saw it, on the dark ground a service that drops alpha would give it anyway.
    """
    import io

    from PIL import Image as PILImage

    raw = Path(path).read_bytes()
    try:
        with PILImage.open(io.BytesIO(raw)) as opened:
            if "A" not in opened.getbands():
                return raw
            rgba = np.asarray(opened.convert("RGBA")).copy()
    except OSError:
        return raw  # not a picture this can read; the service will say so
    clear = rgba[..., 3] == 0
    if not clear.any():
        return raw
    rgba[clear, :3] = 0
    out = io.BytesIO()
    PILImage.fromarray(rgba).save(out, format="PNG")
    return out.getvalue()


def mime(path) -> str:
    return {".png": "image/png", ".webp": "image/webp"}.get(
        path.suffix.lower(), "image/jpeg"
    )


def price(
    name: str, prices: dict, model: str, speed: str | None, count: int | None = None,
    *, bought: str = "picture",
) -> float:
    """What one call costs, from the declared table, or a refusal (§PW164)."""
    return priced(name, prices, model, speed, count, bought=bought)["price"]


def priced(
    name: str, prices: dict, model: str, speed: str | None, count: int | None = None,
    *, bought: str = "picture",
) -> dict:
    """What one call costs and how it was reached, or a refusal (§PW164, §PW320).

    A row is `<model>:<speed>`, or `<model>` for the speed the service defaults to. A
    call with no row is refused rather than priced at zero: under-counting is the
    direction that lets a session pass a ceiling a person set. A row by the unit,
    `{ per = "character", rate }`, is the rate times `count`, the characters the call
    sends, and one with no count is refused for the same reason.

    The refusal names what the call buys, `bought`, and where the call counts the
    words it sends, the row by the character beside the row by the call (§PW669): an
    unpriced sound model had been refused as a picture, priced per picture.
    """
    row = f"{model}:{speed}" if speed else model
    if row in prices and isinstance(prices[row], dict):
        per, rate = prices[row]["per"], float(prices[row]["rate"])
        if count is None:
            raise PolyweaveError(
                "fetch.uncounted",
                f"[service.{name}] prices {row!r} by the {per}, and this call states "
                f"no count of them",
                "pass the text the call would send, so its length can be priced",
                given=row,
            )
        return {"price": round(rate * int(count), 6), "per": per, "rate": rate,
                "count": int(count)}
    if row in prices:
        return {"price": float(prices[row]), "per": "call"}
    by_words = (
        f', or {row!r} = {{ per = "character", rate = <price of one character> }} '
        f"where the service bills by the words sent" if count is not None else ""
    )
    raise PolyweaveError(
        "fetch.unpriced",
        f"[service.{name}] prices has no row {row!r}, so what the {bought} costs is "
        f"not known",
        f"add {row!r} = <price of one {bought}> to [service.{name}] prices{by_words}, "
        f"in the unit of its ceiling",
        given=row,
        allowed=sorted(prices),
    )


#: What a service's 402 says when the plan, and not the balance, refuses the task.
_PLAN_WORDS = ("plan", "nomorependingtasks", "subscription")


def unpaid(status: int, said: str) -> PolyweaveError | None:
    """A 402 as the refusal it is, or None for any other status (§PW670).

    The plan where the service's words name it: Meshy answered 402 with 300 credits
    left, its free plan refusing the task, and a top-up would not help (§PW627).
    Otherwise the account is out of credit, `fetch.no-credit`, its own code so a batch
    stops at once: Dumont's 68 photos met a 402 on the 15th, and the remedy read as a
    401 or a 400's.
    """
    if status != 402:
        return None
    if any(word in said.lower() for word in _PLAN_WORDS):
        return PolyweaveError(
            "fetch.plan-lacks",
            "the service refuses this task on the account's plan, whatever its balance",
            "move the account to a plan that takes the task, at the service; a refused "
            "task is not charged",
            detail=said,
        )
    return PolyweaveError(
        "fetch.no-credit",
        "the service's account has no credit left for this call (it answered 402)",
        "top the account up at the service, then run again; nothing was charged for "
        "this call, and purchase.remaining says what the project's own ceiling, a "
        "different limit, still allows",
        detail=said,
    )


def reached(name: str, about: dict) -> tuple[str, str]:
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


def download(link: str) -> bytes:
    """The picture's bytes, fetched at once: the link the service gives expires."""
    try:
        fetched = urllib.request.Request(link, headers={"User-Agent": AGENT})  # noqa: S310
        with urllib.request.urlopen(fetched, timeout=TIMEOUT) as answer:  # noqa: S310
            return answer.read()
    except urllib.error.URLError as exc:
        raise PolyweaveError(
            "fetch.nothing-arrived",
            "the picture was made and paid for, and its link could not be read",
            "read the link again at once, before it expires; nothing was ledgered, "
            "so the spend is not yet counted against the ceiling",
            detail=f"{link}: {getattr(exc, 'reason', exc)}",
        ) from exc
