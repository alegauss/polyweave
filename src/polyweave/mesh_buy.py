"""Buying a mesh, from words or from a picture that was settled first (§PW183).

Until now a consumer wrote its own Meshy client and polyweave took delivery: Starship's
`meshy.py` carried a bearer header, a poll, a balance read either side and its own error
handling, and every fix to them was made in a second repository. This is that client
once, going through the same doors a picture does:

    1. the price is the project's `prices` row for the model, never the caller's figure
    2. `purchase.allow` is asked against the service's own ceiling
    3. the balance is read, the task is sent and polled, the balance is read again
    4. the mesh is captured before anything else, because the service deletes it later

**A mesh bought from a picture needs the picture to have passed the gate.** The point
of drawing first is that the outline is settled for cents before thirty credits go on a
mesh (§PW168). A picture `picture.gate` never passed is refused here, so the rule is a
property of the call and not a habit.

The cost recorded is the difference between the two balance readings, which is a
measurement; the price row only decides whether the call may be made.
"""

from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Annotated

from . import picture, provenance, purchase
from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

#: The two routes, and where each is asked after.
ROUTES = {"text": "/openapi/v2/text-to-3d", "image": "/openapi/v1/image-to-3d"}

#: How often a task is asked after, and for how long, before the call gives up on it.
POLL_EVERY = 5.0
POLL_TIMEOUT = 900

TIMEOUT = 120


@operation("mesh.buy", kind="fetch", injects=("report",))
def buy(
    report=None,
    out: Annotated[str, Param("where the .glb is written, under the project")] = None,
    prompt: Annotated[str, Param("what to model, in words")] = None,
    *,
    picture_path: Annotated[
        str, Param("a picture picture.gate passed, to model from instead of words")
    ] = None,
    model: Annotated[
        str, Param("the service's model, e.g. meshy-6-lite")
    ] = "meshy-6-lite",
    polycount: Annotated[int, Param("the triangles to aim at", lo=100)] = 8000,
    entity: Annotated[str, picture.ENTITY] = None,
    world: Annotated[str, picture.WORLD] = None,
    service: Annotated[str, purchase.SERVICE] = None,
    root: Annotated[str, Param("the project whose ledger this is")] = ".",
) -> dict:
    """Buy one untextured mesh, from a prompt or a gated picture, against the ceiling.

    Returns the ledger entry. The cost recorded is what two balance readings either side
    of the task say it was; the `prices` row for `model` only decides whether it may be
    spent. A picture is refused unless the gate passed it, so a mesh bought from a
    picture had its silhouette settled on the picture first.

    With `entity` and no picture, the prompt is the world's description of it, with the
    call's own words as detail (§PW198); either way the record names the entity.
    """
    if not out:
        raise PolyweaveError(
            "fetch.missing-field",
            "a mesh was asked for with nowhere to write it",
            "pass out, a .glb path under the project",
        )
    drawn_from = None
    if entity is not None:
        drawn_from, _, composed, _ = picture.from_world(
            entity, world, root, None, prompt, None, structured=False
        )
        if picture_path is None:
            prompt = composed
    if (prompt is None) == (picture_path is None):
        raise PolyweaveError(
            "fetch.missing-field",
            "a mesh is bought from a prompt or a picture, and this call gave "
            + ("neither" if prompt is None else "both"),
            "pass prompt, or picture_path for a picture picture.gate passed",
        )
    config = load(root)
    here = config.root
    name = config.service(service)
    about = config.services()[name]
    base, key = _reached(name, about)
    price = picture._price(name, about.get("prices") or {}, model, None)

    route = "text" if prompt is not None else "image"
    request: dict = {
        "ai_model": model,
        "topology": "triangle",
        "target_polycount": int(polycount),
        "should_remesh": True,
    }
    source = None
    if route == "text":
        request.update(mode="preview", prompt=prompt)
    else:
        source = here / picture_path
        _gated(source, here)
        encoded = base64.b64encode(picture.sent_bytes(source)).decode("ascii")
        request.update(
            image_url=f"data:{picture._mime(source)};base64,{encoded}",
            should_texture=False,
        )

    purchase.allow(price, root=here, service=name)
    before = _balance(base, key)
    task = _json("POST", base + ROUTES[route], key, request).get("result")
    if not task:
        raise PolyweaveError(
            "fetch.service-error",
            "the service accepted the request and returned no task id",
            "read the service's answer; nothing was ledgered",
        )
    finished = _polled(base + ROUTES[route], key, task, report)
    link = (finished.get("model_urls") or {}).get("glb")
    if not link:
        raise PolyweaveError(
            "fetch.nothing-arrived",
            f"task {task} finished with no .glb to take delivery of",
            "look at the task on the service; nothing was ledgered",
            detail=json.dumps(finished)[:400],
        )
    if report is not None:
        report.stage("downloading", progress=0.9, note="taking delivery of the mesh")
    body = picture._download(link)
    after = _balance(base, key)
    return purchase.capture(
        body,
        out=out,
        task_id=f"{name}:{task}",
        credits=price,
        balance_before=before,
        balance_after=after,
        prompt=prompt,
        reference=picture_path,
        bought="mesh",
        engine={"name": name, "model": model},
        service=name,
        details={
            "route": route,
            "model": model,
            "polycount": int(polycount),
            "entity": drawn_from,
        },
        inputs=[provenance.source("world", drawn_from["world"], root=here)]
        if drawn_from
        else None,
        root=here,
    )


def _gated(source: Path, here: Path) -> None:
    """Refuse a picture the gate never passed and no person promoted (§PW168, §PW208).

    The gate's bar is the project's, and a person who looks at a refused picture and
    says it is right after all is the door the refused lane exists for. So a picture
    passes here when the gate passed it, or when the gate saw exactly these bytes and a
    person's verdict on the review page promoted it.
    """
    from . import provenance

    if not source.is_file():
        raise PolyweaveError(
            "fetch.no-reference",
            f"there is no picture at {source} to model from",
            "name the picture picture.gate chose, as a path under the project",
        )
    said = source.with_suffix(".gate.json")
    verdict = json.loads(said.read_text(encoding="utf-8")) if said.is_file() else None
    digest = provenance.sha256_of(source)[0]
    seen = bool(verdict) and verdict.get("sha256") == digest
    if seen and (verdict.get("passed") or _promoted(source, here)):
        return
    raise PolyweaveError(
        "fetch.picture-ungated",
        f"{source.name} has not passed picture.gate"
        + ("" if verdict else ", or was never put through it")
        + (", or changed since it was" if verdict and not seen else ""),
        "run picture.gate on it against the declared outline and buy from the one it "
        "chooses, or have a person promote it from the review page's refused lane; a "
        "silhouette is settled on the picture before the mesh is paid for",
    )


def _promoted(source: Path, here: Path) -> bool:
    """Whether a person accepted this refused picture from a gate's lane on the page."""
    from . import verdict

    for answer in verdict.answers(root=str(here))["answers"]:
        if not str(answer.get("sitting", "")).startswith("gate:"):
            continue
        if answer.get("family") != source.stem:
            continue
        if any(m.get("person_accepted") for m in answer.get("members") or ()):
            return True
    return False


def _reached(name: str, about: dict) -> tuple[str, str]:
    return picture._reached(name, about)


def _json(method: str, url: str, key: str, payload: dict | None = None) -> dict:
    """One JSON call with the bearer key, a refusal turned into a code."""
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Authorization": f"Bearer {key}", "User-Agent": picture.AGENT}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:  # noqa: S310
            return json.loads(answer.read() or b"{}")
    except urllib.error.HTTPError as refused:
        said = refused.read()[:400].decode("utf-8", "replace")
        if refused.code == 402:
            raise PolyweaveError(
                "fetch.over-budget",
                "the service says the account has too few credits for this task",
                "top the account up; the project's own ceiling was not the limit",
                detail=said,
            ) from refused
        if refused.code == 429:
            raise PolyweaveError(
                "fetch.rate-limited",
                "the service has more tasks from this account in flight than it allows",
                "wait for the tasks already out to finish, then ask again",
                detail=said,
            ) from refused
        raise PolyweaveError(
            "fetch.service-error",
            f"the service answered {refused.code} to {method} {url}",
            "read the detail; a 401 is a key the service does not accept, and a 400 a "
            "request it does not",
            detail=said,
        ) from refused
    except urllib.error.URLError as exc:
        raise PolyweaveError(
            "fetch.service-error",
            f"the service could not be reached at {url}",
            "check the base under [service] and the network",
            detail=str(exc.reason),
        ) from exc


def _balance(base: str, key: str) -> float:
    """The account's credits now; read either side of a task, it is what it cost."""
    return float(_json("GET", base + "/openapi/v1/balance", key).get("balance", 0.0))


def _reason(found: dict) -> str:
    return (found.get("task_error") or {}).get("message") or "no reason given"


def _polled(route: str, key: str, task: str, report) -> dict:
    """Ask after one task until it succeeds, fails or runs out of time."""
    started = time.monotonic()
    while True:
        found = _json("GET", f"{route}/{task}", key)
        state = found.get("status")
        if state == "SUCCEEDED":
            return found
        if state in ("FAILED", "CANCELED"):
            raise PolyweaveError(
                "fetch.service-error",
                f"task {task} {state.lower()}: {_reason(found)}",
                "reword the request or ask again; nothing was ledgered, and the "
                "balance readings will show whether the service charged",
                detail=json.dumps(found)[:400],
            )
        waited = time.monotonic() - started
        if waited > POLL_TIMEOUT:
            raise PolyweaveError(
                "fetch.service-error",
                f"task {task} was still {state} after {POLL_TIMEOUT}s",
                f"ask after it later by its id, {task}; nothing was ledgered",
            )
        if report is not None:
            report.stage(
                "building",
                progress=min(0.8, float(found.get("progress") or 0) / 100.0),
                note=f"task {task} is {state}",
            )
        time.sleep(POLL_EVERY)
