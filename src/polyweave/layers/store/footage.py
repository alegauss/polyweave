"""A clip bought from a Scenario video model, measured as the video it is (§PW692).

`picture.buy` reaches Scenario's public models through the same route a video model
answers on, and opens what comes back as a picture, so a video model's MP4 could not
come through it: a project wanting a generated opening shot called Scenario's API from
a script of its own, outside the ledger, the ceiling and the record. `video.buy` is the
verb whose delivery is a video. The request is built from what the model declares it
takes, read for free; the price is the project's row for the model, checked against a
dry run where the ceiling counts Scenario's own units; the clip is captured, recorded
and ledgered through `services.service.buy` like any purchase, and then measured by
`video.measured`: its length, size, rate and whether it carries sound.
"""

from __future__ import annotations

import base64
from typing import Annotated

from polyweave.kernel import provenance
from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.picture import scenario
from polyweave.services import client, purchase
from polyweave.services import scenario as adapter
from polyweave.services import service as S

from . import video

#: The inputs a video model may declare its starting still under, in the order looked.
STILLS = ("image", "startImage", "firstFrame", "firstFrameImage")

#: The files a clip may be written to.
SUFFIXES = (".mp4", ".mov", ".webm")


@operation("video.buy", kind="fetch", injects=("report",), spends=True)
def buy(
    report=None,
    out: Annotated[str, Param("where the clip is written, under the project")] = None,
    prompt: Annotated[str, Param("what happens in it, in words")] = None,
    *,
    model: Annotated[str, Param("a Scenario video model's id")] = None,
    image: Annotated[
        str, Param("a still under the project it starts from, if the model takes one")
    ] = None,
    duration: Annotated[
        float, Param("seconds, as the model declares them", lo=0.0)
    ] = None,
    aspect_ratio: Annotated[str, Param("as 16x9")] = None,
    seed: Annotated[int, Param("for a clip that can be asked for again")] = None,
    service: Annotated[str, purchase.SERVICE] = None,
    root: Annotated[str, Param("the project whose ledger this is")] = ".",
) -> dict:
    """Buy one generated clip from a Scenario video model against the ceiling (§PW692).

    The fields go as the model declares them: the prompt, the starting still inline,
    the duration within its bounds or among its allowed values, the shape as it spells
    one. A field the model does not declare is refused before anything is spent, as is
    a machine with no ffprobe to measure the clip. The price is the project's row for
    the model, and where the ceiling counts CU a dry run's quote above it is
    `picture.quoted-over-price`.

    Returns the ledger entry with `video`: the clip's length, width, height, rate and
    whether it has sound, also kept in its record's measurements. The still is the
    record's `image` input. The clip is a new artefact a person judges.
    """
    if not out or not prompt or not model:
        raise PolyweaveError(
            "fetch.missing-field",
            "a clip was asked for without where it goes, what happens in it, or the "
            "model",
            "pass out (a .mp4 under the project), prompt and model, a Scenario video "
            "model's id",
        )
    if not out.lower().endswith(SUFFIXES):
        raise PolyweaveError(
            "fetch.bad-choice",
            f"{out} is not a video file's name",
            f"end out in one of {', '.join(SUFFIXES)}",
            given=out,
            allowed=SUFFIXES,
        )
    config = load(root)
    if not scenario.serves(config, service):
        scenarios = sorted(one for one in config.services()
                           if scenario.serves(config, one))
        raise PolyweaveError(
            "fetch.unknown-service",
            "video.buy buys from Scenario, and the service named is not one",
            f"name one of {', '.join(scenarios)}" if scenarios else
            'declare [service.scenario] with base = "https://api.cloud.scenario.com"',
            given=service,
            allowed=scenarios,
        )
    still = None
    if image is not None:
        still = config.root / image
        if not still.is_file():
            raise PolyweaveError(
                "fetch.missing-field",
                f"there is no still at {image}",
                "pass a picture under the project, or no image",
                given=image,
            )
    # Measured after it is bought, so a machine that cannot measure is refused first.
    video._ffmpeg("ffprobe")
    chosen = config.service(service)
    about = config.services()[chosen]
    base, key = client.reached(chosen, about)
    price = client.price(chosen, about.get("prices") or {}, model, None, bought="clip")
    takes = {one["name"]: one for one in adapter.declared(base, key, model)}
    if "prompt" not in takes:
        raise PolyweaveError(
            "fetch.bad-choice",
            f"{model} takes no prompt, so it makes no clip from words",
            "name a video model whose capabilities include txt2video or img2video",
            given=model,
        )
    payload: dict = {"prompt": prompt, **scenario._shaped(model, takes, aspect_ratio)}
    if still is not None:
        field = next((one for one in STILLS if one in takes), None)
        if field is None:
            raise PolyweaveError(
                "fetch.unknown-field",
                f"{model} declares no still to start from",
                "ask without image, or name a model that takes one",
                given="image",
                allowed=sorted(takes),
            )
        payload[field] = f"data:{client.mime(still)};base64," + base64.b64encode(
            still.read_bytes()).decode()
    if duration is not None:
        payload["duration"] = _lasting(model, takes, duration)
    if seed is not None:
        if "seed" not in takes:
            raise PolyweaveError(
                "fetch.unknown-field",
                f"{model} declares no seed",
                "ask without a seed",
                given="seed",
                allowed=sorted(takes),
            )
        payload["seed"] = seed
    scenario._within_quote(config, chosen, base, key, model, payload, price)
    order = S.Order(
        service=chosen, base=base, key=key, price=price, root=config.root,
        asked={"call": "draw", "model": model, "payload": payload,
               "wait": adapter.VIDEO_TIMEOUT},
        kept={
            "out": out,
            "prompt": prompt,
            "bought": "video",
            "engine": {"name": chosen, "model": model},
            "details": {
                "model": model,
                "public": True,
                "seed": seed,
                "aspect_ratio": aspect_ratio,
                **{k: v for k, v in payload.items()
                   if k != "prompt" and k not in STILLS},
            },
            **({"inputs": [provenance.source("image", still, config.root)]}
               if still is not None else {}),
        },
    )
    entry = S.buy(adapter.SERVICE, order, report)
    try:
        measured = video.measured(config.root / out)
    except PolyweaveError as unread:
        # Bought and recorded already, so the entry stands and says what was not read.
        return {**entry, "findings": [{"code": unread.code, "message": unread.message}]}
    record = provenance.read(str(config.root / out), root=config.root)
    record["measurements"] = {**(record.get("measurements") or {}), **measured}
    provenance.write(record, config.root)
    return {**entry, "video": measured}


def _lasting(model: str, takes: dict, asked: float) -> float | int | str:
    """The duration in the spelling the model declares, refused where it takes none."""
    field = takes.get("duration")
    if field is None:
        raise PolyweaveError(
            "fetch.unknown-field",
            f"{model} declares no duration, so it decides the length itself",
            "ask without duration",
            given="duration",
            allowed=sorted(takes),
        )
    allowed = field.get("allowedValues") or []
    if allowed:
        for one in allowed:
            try:
                if float(str(one).rstrip("s")) == float(asked):
                    return one
            except ValueError:
                continue
        raise PolyweaveError(
            "fetch.bad-choice",
            f"{model} makes no clip {asked:g}s long",
            f"pass a duration among {', '.join(str(one) for one in allowed)}",
            given=asked,
            allowed=allowed,
        )
    low, high = field.get("min"), field.get("max")
    if (low is not None and asked < low) or (high is not None and asked > high):
        raise PolyweaveError(
            "fetch.bad-choice",
            f"{model} makes clips {low} to {high}s long, and {asked:g} was asked",
            f"pass a duration from {low} to {high}",
            given=asked,
        )
    if field.get("type") == "string":
        return f"{asked:g}"
    return int(asked) if float(asked).is_integer() else asked
