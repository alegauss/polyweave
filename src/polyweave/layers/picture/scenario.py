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
           root) -> dict:
    """`picture.buy` on a Scenario service: a picture from the family's model."""
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


