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
from pathlib import Path
from typing import Annotated

from polyweave.kernel import provenance
from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.picture import picture
from polyweave.services import client, purchase
from polyweave.services.client import download as _download

#: The two routes, and where each is asked after.
ROUTES = {"text": "/openapi/v2/text-to-3d", "image": "/openapi/v1/image-to-3d",
          "views": "/openapi/v1/multi-image-to-3d"}

#: The most pictures one Meshy task takes: the front and three other views.
MOST_VIEWS = 3

#: Tripo's (§PW445), on its v3 API, whose base is `https://openapi.tripo3d.com/v3`: a
#: picture is sent up first for a token, a task is asked after at /tasks/<id>, and the
#: balance is the account's. A service whose base is on tripo3d is spoken to this way.
TRIPO_ROUTES = {"text": "/generation/text-to-model",
                "image": "/generation/image-to-model"}
TRIPO_HOST = "tripo3d"

#: Rodin's (§PW446), Hyper3D's v2 API: a task is sent as a form, its jobs asked after by
#: the subscription key it answers, and its files listed by the task's uuid. A service
#: whose base is on hyper3d or deemos is spoken to this way. Rodin publishes no balance,
#: so its cost is the project's quoted price, recorded as not measured.
RODIN_HOSTS = ("hyper3d", "deemos")
RODIN_ROUTES = {"make": "/api/v2/rodin", "status": "/api/v2/status",
                "download": "/api/v2/download"}

#: How often a task is asked after, and for how long, before the call gives up on it.
POLL_EVERY = 5.0
POLL_TIMEOUT = 900

TIMEOUT = 120


@operation("mesh.buy", kind="fetch", injects=("report",), spends=True)
def buy(
    report=None,
    out: Annotated[str, Param("where the .glb is written, under the project")] = None,
    prompt: Annotated[str, Param("what to model, in words")] = None,
    *,
    picture_path: Annotated[
        str, Param("a picture picture.gate passed, to model from instead of words")
    ] = None,
    views: Annotated[
        list, Param("other views of the same thing, each gated too: a side, a top")
    ] = (),
    model: Annotated[
        str, Param("the service's model: meshy-6-lite, or Tripo's v2.5-20250123")
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
    name = config.service(service, model=model)
    about = config.services()[name]
    base, key = _reached(name, about)
    price = client.price(name, about.get("prices") or {}, model, None)

    route = "text" if prompt is not None else "views" if views else "image"
    tripo = TRIPO_HOST in base
    rodin = any(host in base for host in RODIN_HOSTS)
    if rodin:
        return _rodin(report, out=out, prompt=prompt, picture_path=picture_path,
                      views=views, model=model, polycount=polycount, name=name,
                      base=base, key=key, price=price, here=here, drawn_from=drawn_from)
    source = None
    if views and (picture_path is None or tripo or len(views) > MOST_VIEWS):
        raise PolyweaveError(
            "fetch.bad-choice",
            "other views are sent with a front picture, to Meshy, three at most"
            if not tripo else "Tripo is sent one picture here, and views were given",
            "pass picture_path as the front and at most three views beside it"
            if not tripo else "buy from the Meshy service, or leave views out",
            given="views",
        )
    seen = []
    if route != "text":
        source = here / picture_path
        _gated(source, here)
        for one in views:
            _gated(here / one, here)
            seen.append(here / one)
    if tripo:
        request: dict = {"model_version": model, "texture": False,
                         "face_limit": int(polycount)}
        if route == "text":
            request["prompt"] = prompt
    else:
        request = {
            "ai_model": model,
            "topology": "triangle",
            "target_polycount": int(polycount),
            "should_remesh": True,
        }
        if route == "text":
            request.update(mode="preview", prompt=prompt)
        elif route == "views":
            # The front first, which Meshy takes as the primary view.
            request.update(image_urls=[_data_uri(one) for one in (source, *seen)],
                           should_texture=False)
        else:
            request.update(image_url=_data_uri(source), should_texture=False)

    purchase.allow(price, root=here, service=name)
    if tripo:
        before = _tripo_balance(base, key)
        if source is not None:
            # Tripo takes no picture inline: it is sent up first, once the spend is
            # allowed, and named by the token it answers.
            request["file"] = {"type": source.suffix.lower().lstrip(".") or "png",
                               "file_token": _uploaded(base, key, source)}
        made = _json("POST", base + TRIPO_ROUTES[route], key, request)
        task = (made.get("data") or {}).get("task_id")
    else:
        before = _balance(base, key)
        task = _json("POST", base + ROUTES[route], key, request).get("result")
    if not task:
        raise PolyweaveError(
            "fetch.service-error",
            "the service accepted the request and returned no task id",
            "read the service's answer; nothing was ledgered",
        )
    if tripo:
        finished = _tripo_polled(base, key, task, report)
        link = (finished.get("output") or {}).get("model_url")
    else:
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
    body = _download(link)
    after = _tripo_balance(base, key) if tripo else _balance(base, key)
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
            **({"views": list(views)} if views else {}),
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
    from polyweave.kernel import provenance

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
    from polyweave.loop import verdict

    for answer in verdict.answers(root=str(here))["answers"]:
        if not str(answer.get("sitting", "")).startswith("gate:"):
            continue
        if answer.get("family") != source.stem:
            continue
        if any(m.get("person_accepted") for m in answer.get("members") or ()):
            return True
    return False


def _data_uri(source: Path) -> str:
    encoded = base64.b64encode(client.sent_bytes(source)).decode("ascii")
    return f"data:{client.mime(source)};base64,{encoded}"


def _reached(name: str, about: dict) -> tuple[str, str]:
    return client.reached(name, about)


def _json(method: str, url: str, key: str, payload: dict | None = None) -> dict:
    """One JSON call with the bearer key, a refusal turned into a code."""
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Authorization": f"Bearer {key}"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    try:
        answer = client.send(url, method=method, data=body, headers=headers,
                             timeout=TIMEOUT)
    except client.Unreached as exc:
        raise PolyweaveError(
            "fetch.service-error",
            f"the service could not be reached at {url}",
            "check the base under [service] and the network",
            detail=exc.reason,
        ) from exc
    if answer.status < 400:
        return json.loads(answer.body or b"{}")
    said = answer.body[:400].decode("utf-8", "replace")
    if answer.status == 402:
        raise PolyweaveError(
            "fetch.over-budget",
            "the service says the account has too few credits for this task",
            "top the account up; the project's own ceiling was not the limit",
            detail=said,
        )
    if answer.status == 429:
        raise PolyweaveError(
            "fetch.rate-limited",
            "the service has more tasks from this account in flight than it allows",
            "wait for the tasks already out to finish, then ask again",
            detail=said,
        )
    raise PolyweaveError(
        "fetch.service-error",
        f"the service answered {answer.status} to {method} {url}",
        "read the detail; a 401 is a key the service does not accept, and a 400 a "
        "request it does not",
        detail=said,
    )


def _balance(base: str, key: str) -> float:
    """The account's credits now; read either side of a task, it is what it cost."""
    return float(_json("GET", base + "/openapi/v1/balance", key).get("balance", 0.0))


def _rodin(report, *, out, prompt, picture_path, views, model, polycount, name, base,
           key, price, here, drawn_from) -> dict:
    """One Rodin task (§PW446): gated pictures or words sent as a form for a quad mesh,
    its jobs asked after until done, and its .glb taken delivery of."""
    pictures = [] if picture_path is None else [here / picture_path,
                                                *(here / one for one in views)]
    for one in pictures:
        _gated(one, here)
    fields = {"tier": model, "mesh_mode": "Quad", "quality_override": int(polycount),
              "geometry_file_format": "glb", "material": "Shaded"}
    if prompt is not None:
        fields["prompt"] = prompt
    purchase.allow(price, root=here, service=name)
    made = _form(base + RODIN_ROUTES["make"], key, fields,
                 [("images", one) for one in pictures])
    task = made.get("uuid")
    subscription = (made.get("jobs") or {}).get("subscription_key")
    if not task or not subscription:
        raise PolyweaveError(
            "fetch.service-error",
            "the service accepted the request and returned no task or subscription key",
            "read the detail; nothing was ledgered",
            detail=json.dumps(made)[:400],
        )
    started = time.monotonic()
    while True:
        jobs = _json("POST", base + RODIN_ROUTES["status"], key,
                     {"subscription_key": subscription}).get("jobs") or []
        states = [str(job.get("status")) for job in jobs]
        if "Failed" in states:
            raise PolyweaveError(
                "fetch.service-error", f"task {task} failed",
                "reword the request or ask again; nothing was ledgered",
                detail=json.dumps(jobs)[:400])
        if states and all(state == "Done" for state in states):
            break
        if time.monotonic() - started > POLL_TIMEOUT:
            raise PolyweaveError(
                "fetch.service-error",
                f"task {task} was still {states} after {POLL_TIMEOUT}s",
                f"ask after it later by its id, {task}; nothing was ledgered")
        if report is not None:
            done = sum(1 for state in states if state == "Done")
            share = done / max(1, len(states))
            report.stage("building", progress=min(0.8, 0.2 + 0.6 * share),
                         note=f"task {task}: {', '.join(states) or 'queued'}")
        time.sleep(POLL_EVERY)
    files = _json("POST", base + RODIN_ROUTES["download"], key,
                  {"task_uuid": task}).get("list") or []
    link = next((one.get("url") for one in files
                 if str(one.get("name", "")).lower().endswith(".glb")), None)
    if not link:
        raise PolyweaveError(
            "fetch.nothing-arrived",
            f"task {task} finished with no .glb to take delivery of",
            "look at the task on the service; nothing was ledgered",
            detail=json.dumps(files)[:400])
    if report is not None:
        report.stage("downloading", progress=0.9, note="taking delivery of the mesh")
    return purchase.capture(
        _download(link),
        out=out,
        task_id=f"{name}:{task}",
        credits=price,
        prompt=prompt,
        reference=picture_path,
        bought="mesh",
        engine={"name": name, "model": model},
        service=name,
        details={
            "route": "text" if prompt is not None else "views" if views else "image",
            **({"views": list(views)} if views else {}), "model": model,
            "polycount": int(polycount), "mesh_mode": "Quad", "entity": drawn_from,
        },
        inputs=[provenance.source("world", drawn_from["world"], root=here)]
        if drawn_from else None,
        root=here,
    )


def _form(url: str, key: str, fields: dict, files: list) -> dict:
    """One multipart POST with the bearer key: `files` as [(field, path)], a refusal
    turned into a code as `_json` turns one."""
    import uuid

    boundary = uuid.uuid4().hex
    parts = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"\r\n\r\n'
        f"{value}\r\n".encode() for field, value in fields.items()
    ]
    for field, path in files:
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; '
            f'filename="{path.name}"\r\nContent-Type: {client.mime(path)}\r\n\r\n'
            .encode() + client.sent_bytes(path) + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    try:
        answer = client.send(
            url, method="POST", data=b"".join(parts), timeout=TIMEOUT,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
    except client.Unreached as exc:
        raise PolyweaveError(
            "fetch.service-error", f"the service could not be reached at {url}",
            "check the base under [service] and the network", detail=exc.reason,
        ) from exc
    if answer.status >= 400:
        raise PolyweaveError(
            "fetch.service-error", f"the service answered {answer.status} to {url}",
            "read the detail; a 401 is a key the service does not accept",
            detail=answer.body[:400].decode("utf-8", "replace"),
        )
    return json.loads(answer.body or b"{}")


def _tripo_balance(base: str, key: str) -> float:
    """Tripo's credits now, a decimal (§PW445)."""
    said = _json("GET", base + "/account/balance", key).get("data") or {}
    return float(said.get("balance", 0.0))


def _uploaded(base: str, key: str, source: Path) -> str:
    """The token Tripo names a picture by once it holds it, sent up as a form."""
    import uuid

    boundary = uuid.uuid4().hex
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="{source.name}"\r\nContent-Type: {client.mime(source)}\r\n\r\n'
    ).encode() + client.sent_bytes(source) + f"\r\n--{boundary}--\r\n".encode()
    try:
        answer = client.send(
            base + "/files", method="POST", data=body, timeout=TIMEOUT,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
    except client.Unreached as exc:
        raise PolyweaveError(
            "fetch.service-error",
            f"the service could not be reached at {base}",
            "check the base under [service] and the network",
            detail=exc.reason,
        ) from exc
    if answer.status >= 400:
        raise PolyweaveError(
            "fetch.service-error",
            f"the service answered {answer.status} to the picture sent up",
            "read the detail; nothing was spent or ledgered",
            detail=answer.body[:400].decode("utf-8", "replace"),
        )
    said = json.loads(answer.body or b"{}")
    token = (said.get("data") or {}).get("file_token")
    if not token:
        raise PolyweaveError(
            "fetch.service-error",
            "the service took the picture and named no token for it",
            "read the detail; nothing was spent or ledgered",
            detail=json.dumps(said)[:400],
        )
    return token


def _tripo_polled(base: str, key: str, task: str, report) -> dict:
    """Ask after one Tripo task until it succeeds, fails or runs out of time."""
    started = time.monotonic()
    while True:
        found = _json("GET", f"{base}/tasks/{task}", key).get("data") or {}
        state = str(found.get("status", "")).lower()
        if state == "success":
            return found
        if state in ("failed", "cancelled", "banned", "expired"):
            raise PolyweaveError(
                "fetch.service-error",
                f"task {task} {state}: "
                f"{found.get('error_message') or 'no reason given'}",
                "reword the request or ask again; nothing was ledgered, and the "
                "balance readings will show whether the service charged",
                detail=json.dumps(found)[:400],
            )
        if time.monotonic() - started > POLL_TIMEOUT:
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
