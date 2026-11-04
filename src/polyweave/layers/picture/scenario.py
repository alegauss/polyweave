"""A picture bought from a model trained on the project's own canon (§PW450).

Scenario trains a model on a team's art, which is what a canon of approved pictures
already is: the training set chosen by a person's verdicts. `style.train` sends one
family's canon pictures and trains a model on them; `picture.buy` naming a Scenario
service draws from the family's trained model. Both are purchases like any other:
priced from the project's `prices`, allowed against the ceiling, ledgered and recorded,
and never started on an agent's own judgement. The pictures it returns are held to the
canon and the gate like any service's; being trained on the style earns no pass.

The trained model is kept beside the canon as `<canon>/scenario.model.json`, naming the
members that trained it, so a picture drawn after a member joined says the model is
`outdated`, and the picture's record has the model file as an input.

Scenario's client is `services/scenario.py`, and both are bought through
`services.service.buy` (§PW516).
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Annotated

from polyweave.kernel import provenance
from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.doors import Blank, door
from polyweave.kernel.errors import PolyweaveError
from polyweave.services import purchase
from polyweave.services import scenario as adapter
from polyweave.services import service as S
from polyweave.services.client import mime as client_mime
from polyweave.services.scenario import HOSTS

from . import picture, style

#: The file beside a canon that names the model trained on it.
TRAINED = "scenario.model.json"

#: The fewest pictures Scenario trains on.
FEWEST = 5

#: The model kinds this client trains: a LoRA over a text-to-image model.
TYPES = ("flux.2-dev-lora", "flux.1-lora")

def serves(config, service: str | None) -> bool:
    """Whether the service a call means is Scenario."""
    try:
        name = config.service(service)
    except PolyweaveError:
        return False
    return any(host in str(config.services()[name].get("base", "")) for host in HOSTS)


@operation("style.train", kind="fetch", injects=("report",), spends=True)
def train(
    report=None,
    family: Annotated[str, Param("the family whose canon trains the model")] = None,
    *,
    kind: Annotated[str, Param("the kind of model trained", choices=TYPES)] = TYPES[0],
    service: Annotated[str, purchase.SERVICE] = None,
    root: Annotated[str, Param("the project whose ledger this is")] = ".",
) -> dict:
    """Train a Scenario model on one family's canon, against the ceiling (§PW450).

    The canon's pictures are sent as training images, the model is trained, and its id
    is kept beside the canon with the members that trained it. The price is the row
    `<kind>:train` of the service's `prices`. The call waits for training to end.
    """
    config = load(root)
    name, declared = config.style(family)
    if not serves(config, service):
        scenarios = sorted(one for one in config.services() if serves(config, one))
        raise PolyweaveError(
            "fetch.unknown-service",
            "style.train trains on Scenario, and the service named is not one",
            f"name one of {', '.join(scenarios)}" if scenarios else
            'declare [service.scenario] with base = "https://api.cloud.scenario.com"',
            given=service,
            allowed=scenarios,
        )
    held = [e for e in style.admitted(declared) if not style.is_mesh(e["picture"])]
    if len(held) < FEWEST:
        raise PolyweaveError(
            "style.too-few-to-train",
            f"the {name} canon holds {len(held)} picture(s), and Scenario trains on "
            f"at least {FEWEST}",
            "admit more pictures to the canon by verdict first",
        )
    chosen = config.service(service)
    about = config.services()[chosen]
    base, key = picture._reached(chosen, about)
    price = picture._price(chosen, about.get("prices") or {}, kind, "train")
    canon = Path(declared["canon"])
    order = S.Order(
        service=chosen, base=base, key=key, price=price, root=config.root,
        asked={
            "call": "train",
            "name": f"polyweave {name}",
            "type": kind,
            "pictures": [(e["picture"], canon / e["picture"]) for e in held],
            "record": {
                "service": chosen,
                "type": kind,
                "family": name,
                "members": [{"picture": e["picture"], "sha256": e["sha256"]}
                            for e in held],
            },
        },
        kept={
            "out": provenance.relative(canon / TRAINED, config.root),
            "bought": "model",
            "engine": {"name": chosen, "model": kind},
            "inputs": [provenance.source("canon", canon / e["picture"], config.root)
                       for e in held],
        },
    )
    # Training was started and is charged whether or not it ends well (§PW179): the
    # charge is owed from the moment it is sent.
    entry = S.buy(adapter.SERVICE, order, report)
    model = entry["task_id"].split(":", 1)[1]
    return {**entry, "model": model, "members": len(held)}


def trained_model(declared: dict) -> dict | None:
    """The model a family's canon trained, as kept beside it, or None."""
    if not declared.get("canon"):
        return None
    where = Path(declared["canon"]) / TRAINED
    return json.loads(where.read_text(encoding="utf-8")) if where.is_file() else None


def bought(report, *, out: str, prompt: str | None, family: str | None,
           aspect_ratio: str | None, seed: int | None, service: str | None,
           root, model: str | None = None) -> dict:
    """`picture.buy` on a Scenario service: a picture from the family's model, or
    from the public model `model` names (§PW688)."""
    if model and model not in picture.MODELS:
        return _public(report, out=out, prompt=prompt, model=model,
                      aspect_ratio=aspect_ratio, seed=seed, service=service, root=root)
    config = load(root)
    name, declared = config.style(family)
    trained = trained_model(declared)
    if trained is None:
        raise PolyweaveError(
            "style.untrained",
            f"the {name} canon has trained no model to draw from",
            "train one on the canon first",
            call=door("style.train", family=name, service=service or Blank("scenario")),
        )
    if not prompt:
        raise PolyweaveError(
            "fetch.missing-field",
            "a picture from a trained model was asked for with no prompt",
            "pass prompt, what it shows in words; the style is the model's",
        )
    chosen = config.service(service)
    about = config.services()[chosen]
    base, key = picture._reached(chosen, about)
    price = picture._price(chosen, about.get("prices") or {}, trained["type"], None)
    joined = {m["sha256"] for m in trained["members"]}
    outdated = [e["picture"] for e in style.admitted(declared)
                if not style.is_mesh(e["picture"]) and e["sha256"] not in joined]
    payload: dict = {"prompt": prompt}
    if aspect_ratio:
        payload["aspectRatio"] = aspect_ratio
    if seed is not None:
        payload["seed"] = seed
    canon = Path(declared["canon"])
    order = S.Order(
        service=chosen, base=base, key=key, price=price, root=config.root,
        asked={"call": "draw", "model": trained["model"], "payload": payload},
        kept={
            "out": out,
            "prompt": prompt,
            "bought": "image",
            "engine": {"name": chosen, "model": trained["model"]},
            "details": {
                "model": trained["model"],
                "type": trained["type"],
                "family": name,
                "members": trained["members"],
                # Members a person admitted after the model was trained: it has not
                # seen them, so it draws the family as it was.
                "outdated": outdated,
                "seed": seed,
                "aspect_ratio": aspect_ratio,
            },
            "inputs": [provenance.source("model", canon / TRAINED, config.root)],
        },
    )
    entry = S.buy(adapter.SERVICE, order, report)
    return {**entry, "outdated": outdated} if outdated else entry


#: The longer side a shape given as width and height is drawn at, where the model
#: declares no default of its own.
LONGER = 1024


def _public(report, *, out: str, prompt: str | None, model: str,
           aspect_ratio: str | None, seed: int | None, service: str | None,
           root) -> dict:
    """A picture from one of Scenario's public models, which needs no training (§PW688).

    The payload is built from what the model declares it takes, read for free, so a
    field it would drop is refused here. The price is the project's row for the model;
    where the ceiling counts Scenario's own units, a dry run asks the exact charge
    first, and one above the row is refused rather than under-counted.
    """
    if not prompt:
        raise PolyweaveError(
            "fetch.missing-field",
            "a picture from a public model was asked for with no prompt",
            "pass prompt, what it shows in words",
        )
    config = load(root)
    chosen = config.service(service)
    about = config.services()[chosen]
    base, key = picture._reached(chosen, about)
    price = picture._price(chosen, about.get("prices") or {}, model, None)
    takes = {one["name"]: one for one in adapter.declared(base, key, model)}
    if "prompt" not in takes:
        raise PolyweaveError(
            "fetch.bad-choice",
            f"{model} takes no prompt, so it draws no picture from words",
            "name a model whose capabilities include txt2img",
            given=model,
        )
    payload: dict = {"prompt": prompt, **_shaped(model, takes, aspect_ratio)}
    if seed is not None:
        if "seed" not in takes:
            # A seed the model drops records a picture as repeatable when it is not.
            raise PolyweaveError(
                "fetch.unknown-field",
                f"{model} declares no seed",
                "ask without a seed",
                given="seed",
                allowed=sorted(takes),
            )
        payload["seed"] = seed
    _within_quote(config, chosen, base, key, model, payload, price)
    order = S.Order(
        service=chosen, base=base, key=key, price=price, root=config.root,
        asked={"call": "draw", "model": model, "payload": payload},
        kept={
            "out": out,
            "prompt": prompt,
            "bought": "image",
            "engine": {"name": chosen, "model": model},
            "details": {
                "model": model,
                "public": True,
                "seed": seed,
                "aspect_ratio": aspect_ratio,
                **{k: v for k, v in payload.items() if k != "prompt"},
            },
        },
    )
    return S.buy(adapter.SERVICE, order, report)


def _within_quote(config, chosen: str, base: str, key: str, model: str, payload: dict,
                  price: float) -> None:
    """Refuse a call Scenario quotes above the project's row, before it is sent.

    Only where the ceiling counts Scenario's own units, the ones a dry run answers in;
    the dry run bills nothing (§PW688).
    """
    unit = str(config.budget(service=chosen).get("unit") or "")
    if unit.upper() != "CU":
        return
    charge = adapter.quoted(base, key, model, payload)
    if charge is not None and charge > price:
        raise PolyweaveError(
            "picture.quoted-over-price",
            f"Scenario quotes {charge:g} CU for this call, and [service.{chosen}] "
            f"prices {model!r} at {price:g}",
            f"raise the {model!r} row to at least {charge:g}, so the ceiling "
            "counts what is spent; nothing was spent",
            given=charge,
        )


#: The upscaler a call names none of: Scenario's own, which takes the factor asked.
UPSCALER = "model_upscale-v3"


@operation("picture.upscale", kind="fetch", injects=("report",), spends=True)
def upscale(
    report=None,
    source: Annotated[str, Param("the picture to enlarge, under the project")] = None,
    out: Annotated[str, Param("where the larger picture goes")] = None,
    *,
    factor: Annotated[int, Param("how many times larger each side becomes")] = 2,
    model: Annotated[str, Param("a Scenario upscaler's id")] = UPSCALER,
    service: Annotated[str, purchase.SERVICE] = None,
    root: Annotated[str, Param("the project whose ledger this is")] = ".",
) -> dict:
    """Buy a larger copy of a picture from a Scenario upscaler (§PW689).

    The picture goes inline, the factor in the spelling the model declares, and the
    price is the project's row for the model, checked against a dry run where the
    ceiling counts CU. The larger picture is recorded as made from the smaller one; it
    is a new picture a person judges, and being upscaled earns it no pass. The answer
    says the size it came back at, which a model with a fixed factor decides itself.
    """
    from PIL import Image as PILImage

    config = load(root)
    if not source or not out:
        raise PolyweaveError(
            "fetch.missing-field",
            "an upscale was asked for without the picture or where it goes",
            "pass source and out, both under the project",
        )
    path = config.root / source
    if not path.is_file():
        raise PolyweaveError(
            "fetch.missing-field",
            f"there is no picture at {source}",
            "pass a picture under the project",
            given=source,
        )
    if not serves(config, service):
        scenarios = sorted(one for one in config.services() if serves(config, one))
        raise PolyweaveError(
            "fetch.unknown-service",
            "picture.upscale buys from Scenario, and the service named is not one",
            f"name one of {', '.join(scenarios)}" if scenarios else
            'declare [service.scenario] with base = "https://api.cloud.scenario.com"',
            given=service,
            allowed=scenarios,
        )
    chosen = config.service(service)
    about = config.services()[chosen]
    base, key = picture._reached(chosen, about)
    price = picture._price(chosen, about.get("prices") or {}, model, None)
    takes = {one["name"]: one for one in adapter.declared(base, key, model)}
    if "image" not in takes:
        raise PolyweaveError(
            "fetch.bad-choice",
            f"{model} takes no image, so it enlarges nothing",
            "name an upscaler, such as model_upscale-v3",
            given=model,
        )
    data = f"data:{client_mime(path)};base64," + base64.b64encode(
        path.read_bytes()).decode()
    payload = {"image": data, **_factored(model, takes, factor)}
    _within_quote(config, chosen, base, key, model, payload, price)
    with PILImage.open(path) as held:
        width, height = held.size
    order = S.Order(
        service=chosen, base=base, key=key, price=price, root=config.root,
        asked={"call": "draw", "model": model, "payload": payload},
        kept={
            "out": out,
            "prompt": None,
            "bought": "image",
            "engine": {"name": chosen, "model": model},
            "details": {"model": model, "public": True, "upscaled": {
                "from": source, "size": [width, height],
                **({"factor": factor} if len(payload) > 1 else {})}},
            "inputs": [provenance.source("source", path, config.root)],
        },
    )
    entry = S.buy(adapter.SERVICE, order, report)
    with PILImage.open(config.root / out) as drawn:
        entry["size"] = list(drawn.size)
    return entry


def _factored(model: str, takes: dict, factor: int) -> dict:
    """The factor in the spelling the model declares, or nothing for a fixed one."""
    field = takes.get("upscaleFactor")
    if field is None:
        return {}
    allowed = field.get("allowedValues") or []
    if field.get("type") == "string":
        spelled = f"{factor}x"
        if allowed and spelled not in allowed:
            raise PolyweaveError(
                "fetch.bad-choice",
                f"{model} enlarges by none of {factor}x",
                f"pass a factor among {', '.join(str(one) for one in allowed)}",
                given=factor,
                allowed=allowed,
            )
        return {"upscaleFactor": spelled}
    low, high = field.get("min"), field.get("max")
    if (low is not None and factor < low) or (high is not None and factor > high):
        raise PolyweaveError(
            "fetch.bad-choice",
            f"{model} enlarges by {low} to {high}, and {factor} was asked",
            f"pass a factor from {low} to {high}",
            given=factor,
        )
    return {"upscaleFactor": factor}


def _shaped(model: str, takes: dict, asked: str | None) -> dict:
    """The fields a ratio goes as, in the spelling the model declares (§PW688)."""
    if not asked:
        return {}
    wanted = picture._ratio(asked)
    if wanted is None:
        raise PolyweaveError(
            "fetch.bad-choice",
            f"aspect_ratio is {asked!r}",
            "give it as width by height, such as 16x9",
            given=asked,
        )
    if "aspectRatio" in takes:
        left, right = str(asked).replace("x", ":").replace(" ", "").split(":")
        spelled = f"{left}:{right}"
        allowed = takes["aspectRatio"].get("allowedValues") or []
        if allowed and spelled not in allowed:
            raise PolyweaveError(
                "fetch.bad-choice",
                f"{model} draws no {spelled}",
                f"pass one of {', '.join(str(one) for one in allowed)}",
                given=asked,
                allowed=allowed,
            )
        return {"aspectRatio": spelled}
    if "width" in takes and "height" in takes:
        top = min(int(takes["width"].get("max") or LONGER),
                  int(takes["height"].get("max") or LONGER), LONGER)
        width, height = (top, top / wanted) if wanted >= 1 else (top * wanted, top)
        low = max(int(takes["width"].get("min") or 0),
                  int(takes["height"].get("min") or 0))
        sides = [max(low, int(round(side / 16)) * 16) for side in (width, height)]
        return {"width": sides[0], "height": sides[1]}
    raise PolyweaveError(
        "fetch.unknown-field",
        f"{model} declares no shape, so aspect_ratio has nowhere to go",
        "ask without aspect_ratio",
        given="aspect_ratio",
        allowed=sorted(takes),
    )


