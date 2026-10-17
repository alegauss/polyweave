"""Tripo, on its v3 API (§PW445, §PW516).

The base is `https://openapi.tripo3d.com/v3`: a picture is sent up first for a token,
once the spend is allowed, a task is asked after at /tasks/<id>, and the balance is the
account's.
"""

from __future__ import annotations

import json
from pathlib import Path

from polyweave.kernel.errors import PolyweaveError

from . import service as S

ROUTES = {"text": "/generation/text-to-model", "image": "/generation/image-to-model"}


def upload(base: str, key: str, source: Path) -> str:
    """The token Tripo names a picture by once it holds it, sent up as a form."""
    said = S.form(base + "/files", key, {}, [("file", source)])
    token = (said.get("data") or {}).get("file_token")
    if not token:
        raise PolyweaveError(
            "fetch.service-error",
            "the service took the picture and named no token for it",
            "read the detail; nothing was spent or ledgered",
            detail=json.dumps(said)[:400],
        )
    return token


def submit(order: S.Order) -> str:
    asked = order.asked
    request: dict = {"model_version": asked["model"], "texture": False,
                     "face_limit": int(asked["polycount"])}
    if asked["route"] == "text":
        request["prompt"] = asked["prompt"]
    else:
        source = asked["pictures"][0]
        request["file"] = {"type": source.suffix.lower().lstrip(".") or "png",
                           "file_token": upload(order.base, order.key, source)}
    made = S.call("POST", order.base + ROUTES[asked["route"]], order.key, request)
    return (made.get("data") or {}).get("task_id")


def poll(order: S.Order, task: str, report) -> dict:
    def ask() -> S.Asked:
        found = S.call("GET", f"{order.base}/tasks/{task}", order.key).get("data") or {}
        state = str(found.get("status", "")).lower()
        return S.Asked(
            state="done" if state == "success"
            else "failed" if state in ("failed", "cancelled", "banned", "expired")
            else state,
            found=found,
            said=state,
            progress=float(found.get("progress") or 0) / 100.0,
            reason=found.get("error_message") or "no reason given",
        )

    return S.waited(task, ask, report)


def fetch(order: S.Order, finished: dict) -> bytes:
    link = (finished.get("output") or {}).get("model_url")
    if not link:
        raise PolyweaveError(
            "fetch.nothing-arrived",
            "the task finished with no .glb to take delivery of",
            "look at the task on the service; nothing was ledgered",
            detail=json.dumps(finished)[:400],
        )
    return S.download(link)


def balance(base: str, key: str) -> float:
    """Tripo's credits now, a decimal (§PW445)."""
    said = S.call("GET", base + "/account/balance", key).get("data") or {}
    return float(said.get("balance", 0.0))


SERVICE = S.Service(
    name="tripo", media=("mesh",), hosts=("tripo3d",),
    submit=submit, poll=poll, fetch=fetch, balance=balance,
)
