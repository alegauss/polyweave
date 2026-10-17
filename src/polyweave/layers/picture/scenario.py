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

The routes are Scenario's v1 API, authenticated with `Basic key:secret`: the key
variable holds both, joined by a colon.
"""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Annotated, Any

from polyweave.kernel import provenance
from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.doors import Blank, door
from polyweave.kernel.errors import PolyweaveError
from polyweave.services import client, purchase

from . import picture, style

#: The hosts that are Scenario, so a service there is bought from this way.
HOSTS = ("scenario.com",)

#: The file beside a canon that names the model trained on it.
TRAINED = "scenario.model.json"

#: The fewest pictures Scenario trains on.
FEWEST = 5

#: The model kinds this client trains: a LoRA over a text-to-image model.
TYPES = ("flux.2-dev-lora", "flux.1-lora")

#: How long training may take before the call stops waiting, and how often it asks.
TRAIN_TIMEOUT = 3 * 3600
JOB_TIMEOUT = 300
POLL_EVERY = 5.0


def serves(config, service: str | None) -> bool:
    """Whether the service a call means is Scenario."""
    try:
        name = config.service(service)
    except PolyweaveError:
        return False
    return any(host in str(config.services()[name].get("base", "")) for host in HOSTS)


def _call(method: str, url: str, key: str, body: dict | None = None) -> tuple[int, Any]:
    """One JSON request with the key and secret, answered as status and JSON."""
    try:
        answer = client.send(
            url,
            method=method,
            data=None if body is None else json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": "Basic " + base64.b64encode(key.encode()).decode(),
                "Content-Type": "application/json",
            },
            timeout=picture.TIMEOUT,
        )
    except client.Unreached as exc:
        raise PolyweaveError(
            "fetch.service-error",
            f"the service could not be reached at {url}",
            "check the base under [service] and the network; nothing was spent",
            detail=exc.reason,
        ) from exc
    status, raw = answer.status, answer.body
    try:
        return status, json.loads(raw or b"{}")
    except json.JSONDecodeError:
        return status, {"raw": raw[:400].decode("utf-8", "replace")}


def _ok(status: int, answer: Any, doing: str) -> Any:
    if 200 <= status < 300:
        return answer
    raise PolyweaveError(
        "fetch.service-error",
        f"Scenario answered {status} {doing}",
        "read the detail; a 401 is a key:secret the service does not accept",
        detail=json.dumps(answer)[:400],
    )


def _url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}/v1/{path}"


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
    purchase.allow(price, root=root, service=chosen)

    canon = Path(declared["canon"])
    status, made = _call("POST", _url(base, "models"), key,
                         {"name": f"polyweave {name}", "type": kind})
    model = _ok(status, made, "creating the model")["model"]["id"]
    for entry in held:
        content = (canon / entry["picture"]).read_bytes()
        data = f"data:{picture._mime(canon / entry['picture'])};base64," + (
            base64.b64encode(content).decode())
        status, said = _call("POST", _url(base, f"models/{model}/training-images"), key,
                             {"name": entry["picture"], "data": data})
        _ok(status, said, f"taking {entry['picture']}")
    status, said = _call("PUT", _url(base, f"models/{model}/train"), key,
                         {"parameters": {}})
    _ok(status, said, "starting training")
    task = f"{chosen}:{model}"
    try:
        trained = _trained(base, key, model, report)
    except PolyweaveError as failed:
        # Training was started and is charged whether or not it ends well (§PW179).
        purchase.owe({"task_id": task, "service": chosen, "credits": price,
                      "expected_credits": price, "measured": False, "outputs": 1,
                      "artefact": provenance.relative(canon / TRAINED, config.root)},
                     root=root)
        raise failed
    kept = {
        "service": chosen,
        "model": model,
        "type": kind,
        "family": name,
        "members": [{"picture": e["picture"], "sha256": e["sha256"]} for e in held],
        "status": trained.get("status"),
    }
    entry = purchase.capture(
        (json.dumps(kept, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        out=provenance.relative(canon / TRAINED, config.root),
        task_id=task, credits=price, bought="model", service=chosen,
        engine={"name": chosen, "model": kind}, details=kept,
        inputs=[provenance.source("canon", canon / e["picture"], config.root)
                for e in held],
        root=root,
    )
    return {**entry, "model": model, "members": len(held)}


def _trained(base: str, key: str, model: str, report) -> dict:
    """Ask after a model until it is trained, failed or out of time."""
    started = time.monotonic()
    while True:
        status, said = _call("GET", _url(base, f"models/{model}"), key)
        found = _ok(status, said, f"asking after model {model}").get("model") or {}
        state = found.get("status")
        if state == "trained":
            return found
        if state == "failed":
            raise PolyweaveError(
                "fetch.service-error",
                f"training model {model} failed",
                "read the detail; the charge is counted against the ceiling as owed",
                detail=json.dumps(found)[:400],
            )
        waited = time.monotonic() - started
        if waited > TRAIN_TIMEOUT:
            raise PolyweaveError(
                "fetch.service-error",
                f"model {model} was still {state} after {TRAIN_TIMEOUT // 3600} hours",
                "ask after it on Scenario; the charge is counted as owed",
            )
        if report is not None:
            stage = (found.get("trainingProgress") or {}).get("stage") or state
            report.stage("building", progress=min(0.8, waited / TRAIN_TIMEOUT),
                         note=f"model {model} is {stage}")
        time.sleep(POLL_EVERY)


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
    purchase.allow(price, root=root, service=chosen)
    joined = {m["sha256"] for m in trained["members"]}
    outdated = [e["picture"] for e in style.admitted(declared)
                if not style.is_mesh(e["picture"]) and e["sha256"] not in joined]
    payload: dict = {"prompt": prompt}
    if aspect_ratio:
        payload["aspectRatio"] = aspect_ratio
    if seed is not None:
        payload["seed"] = seed
    status, said = _call("POST", _url(base, f"generate/custom/{trained['model']}"), key,
                         payload)
    job = (_ok(status, said, "drawing from the model").get("job") or {}).get("jobId")
    if not job:
        raise PolyweaveError(
            "fetch.nothing-arrived",
            "Scenario answered with no job to ask after",
            "read the detail; nothing was ledgered",
            detail=json.dumps(said)[:400],
        )
    assets = _job(base, key, job, report)
    status, said = _call("GET", _url(base, f"assets/{assets[0]}"), key)
    asset = _ok(status, said, f"reading asset {assets[0]}").get("asset") or {}
    link = asset.get("url")
    if not link:
        raise PolyweaveError(
            "fetch.nothing-arrived",
            f"asset {assets[0]} came back with no link to take delivery of",
            "read the detail; nothing was ledgered",
            detail=json.dumps(said)[:400],
        )
    canon = Path(declared["canon"])
    kept = {
        "out": out,
        "task_id": f"{chosen}:{job}",
        "credits": round(price * len(assets), 4),
        "reported": None,
        "outputs": len(assets),
        "prompt": prompt,
        "bought": "image",
        "engine": {"name": chosen, "model": trained["model"]},
        "service": chosen,
        "details": {
            "model": trained["model"],
            "type": trained["type"],
            "family": name,
            "members": trained["members"],
            # Members a person admitted after the model was trained: it has not seen
            # them, so it draws the family as it was.
            "outdated": outdated,
            "seed": seed,
            "aspect_ratio": aspect_ratio,
        },
        "inputs": [provenance.source("model", canon / TRAINED, config.root)],
    }
    entry = picture._delivered(link, kept, root)
    return {**entry, "outdated": outdated} if outdated else entry


def _job(base: str, key: str, job: str, report) -> list[str]:
    """Ask after a generation job until it succeeds, and say the assets it made."""
    started = time.monotonic()
    while True:
        status, said = _call("GET", _url(base, f"jobs/{job}"), key)
        found = _ok(status, said, f"asking after job {job}").get("job") or {}
        state = found.get("status")
        if state == "success":
            assets = (found.get("metadata") or {}).get("assetIds") or []
            if assets:
                return assets
            raise PolyweaveError(
                "fetch.nothing-arrived",
                f"job {job} succeeded with no asset",
                "read the detail; nothing was ledgered",
                detail=json.dumps(found)[:400],
            )
        if state in ("failed", "canceled"):
            raise PolyweaveError(
                "fetch.service-error",
                f"job {job} {state}",
                "reword the prompt or ask again; nothing was ledgered",
                detail=json.dumps(found)[:400],
            )
        if time.monotonic() - started > JOB_TIMEOUT:
            raise PolyweaveError(
                "fetch.service-error",
                f"job {job} was still {state} after {JOB_TIMEOUT}s",
                f"ask after it later by its id, {job}; nothing was ledgered",
            )
        if report is not None:
            report.stage("building", note=f"job {job} is {state}")
        time.sleep(POLL_EVERY)
