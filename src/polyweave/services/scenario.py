"""Scenario, which trains a model on a canon and draws from it (§PW450, §PW516).

The routes are Scenario's v1 API, authenticated with `Basic key:secret`: the key
variable holds both, joined by a colon. What the domain asks is `call`, `train` or
`draw`. A training sends `pictures` as (name, path) under a model `name` of a `type`,
and delivers the `record` kept beside the canon with the model's id and status. A
drawing sends `payload` to the trained `model` and delivers the first asset it made.
"""

from __future__ import annotations

import base64
import json
import time
from typing import Any

from polyweave.kernel.errors import PolyweaveError

from . import client
from . import service as S

#: The hosts that are Scenario, so a service there is bought from this way.
HOSTS = ("scenario.com",)

#: How long training may take before the call stops waiting, and how often it asks.
TRAIN_TIMEOUT = 3 * 3600
JOB_TIMEOUT = 300
POLL_EVERY = 5.0


def call(method: str, url: str, key: str, body: dict | None = None) -> tuple[int, Any]:
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
            timeout=S.TIMEOUT,
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


def submit(order: S.Order) -> str:
    asked, base, key = order.asked, order.base, order.key
    if asked["call"] == "train":
        status, made = call("POST", _url(base, "models"), key,
                            {"name": asked["name"], "type": asked["type"]})
        model = _ok(status, made, "creating the model")["model"]["id"]
        for name, path in asked["pictures"]:
            data = f"data:{client.mime(path)};base64," + (
                base64.b64encode(path.read_bytes()).decode())
            status, said = call("POST", _url(base, f"models/{model}/training-images"),
                                key, {"name": name, "data": data})
            _ok(status, said, f"taking {name}")
        status, said = call("PUT", _url(base, f"models/{model}/train"), key,
                            {"parameters": {}})
        _ok(status, said, "starting training")
        return model
    status, said = call("POST", _url(base, f"generate/custom/{asked['model']}"), key,
                        asked["payload"])
    job = (_ok(status, said, "drawing from the model").get("job") or {}).get("jobId")
    if not job:
        raise PolyweaveError(
            "fetch.nothing-arrived",
            "Scenario answered with no job to ask after",
            "read the detail; nothing was ledgered",
            detail=json.dumps(said)[:400],
        )
    return job


def poll(order: S.Order, handle: str, report) -> dict:
    if order.asked["call"] == "train":
        return _trained(order.base, order.key, handle, report)
    assets = _job(order.base, order.key, handle, report)
    status, said = call("GET", _url(order.base, f"assets/{assets[0]}"), order.key)
    asset = _ok(status, said, f"reading asset {assets[0]}").get("asset") or {}
    if not asset.get("url"):
        raise PolyweaveError(
            "fetch.nothing-arrived",
            f"asset {assets[0]} came back with no link to take delivery of",
            "read the detail; nothing was ledgered",
            detail=json.dumps(said)[:400],
        )
    return {"assets": assets, "link": asset["url"]}


def deliver(order: S.Order, handle: str, finished: dict) -> S.Delivery:
    if order.asked["call"] == "train":
        record = {**order.asked["record"], "model": handle,
                  "status": finished.get("status")}
        return S.Delivery(
            task=handle,
            body=(json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            details=record,
        )
    return S.Delivery(task=handle, link=finished["link"],
                      outputs=len(finished["assets"]))


def _trained(base: str, key: str, model: str, report) -> dict:
    """Ask after a model until it is trained, failed or out of time."""
    started = time.monotonic()
    while True:
        status, said = call("GET", _url(base, f"models/{model}"), key)
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


def _job(base: str, key: str, job: str, report) -> list[str]:
    """Ask after a generation job until it succeeds, and say the assets it made."""
    started = time.monotonic()
    while True:
        status, said = call("GET", _url(base, f"jobs/{job}"), key)
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


SERVICE = S.Service(
    name="scenario", media=("image", "model"), hosts=HOSTS,
    submit=submit, poll=poll, deliver=deliver,
)
