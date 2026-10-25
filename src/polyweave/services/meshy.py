"""Meshy, which sells meshes from words or pictures (§PW183, §PW516)."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from polyweave.kernel.errors import PolyweaveError

from . import client
from . import service as S

#: The three routes, and where each is asked after.
ROUTES = {"text": "/openapi/v2/text-to-3d", "image": "/openapi/v1/image-to-3d",
          "views": "/openapi/v1/multi-image-to-3d"}

#: The most pictures one task takes beside the front: three other views.
MOST_VIEWS = 3


def _data_uri(source: Path) -> str:
    encoded = base64.b64encode(client.sent_bytes(source)).decode("ascii")
    return f"data:{client.mime(source)};base64,{encoded}"


def submit(order: S.Order) -> str:
    asked = order.asked
    route = asked["route"]
    request = {
        "ai_model": asked["model"],
        "topology": "triangle",
        "target_polycount": int(asked["polycount"]),
        "should_remesh": True,
    }
    if route == "text":
        request.update(mode="preview", prompt=asked["prompt"])
    elif route == "views":
        # The front first, which Meshy takes as the primary view.
        request.update(image_urls=[_data_uri(one) for one in asked["pictures"]])
    else:
        request.update(image_url=_data_uri(asked["pictures"][0]))
    if route != "text":
        # A toy that is what it is by its colours is bought textured (§PW627).
        textured = bool(asked.get("texture"))
        request["should_texture"] = textured
        if textured and asked.get("texture_prompt"):
            request["texture_prompt"] = str(asked["texture_prompt"])
    return S.call("POST", order.base + ROUTES[route], order.key, request).get("result")


def poll(order: S.Order, task: str, report) -> dict:
    route = order.base + ROUTES[order.asked["route"]]

    def ask() -> S.Asked:
        found = S.call("GET", f"{route}/{task}", order.key)
        state = str(found.get("status"))
        return S.Asked(
            state="done" if state == "SUCCEEDED"
            else "failed" if state in ("FAILED", "CANCELED") else state,
            found=found,
            said=state.lower() if state in ("FAILED", "CANCELED") else state,
            progress=float(found.get("progress") or 0) / 100.0,
            reason=(found.get("task_error") or {}).get("message") or "no reason given",
        )

    return S.waited(task, ask, report)


def deliver(order: S.Order, task: str, finished: dict) -> S.Delivery:
    link = (finished.get("model_urls") or {}).get("glb")
    if not link:
        raise PolyweaveError(
            "fetch.nothing-arrived",
            f"task {task} finished with no .glb to take delivery of",
            "look at the task on the service; nothing was ledgered",
            detail=json.dumps(finished)[:400],
        )
    return S.Delivery(task=task, link=link)


def balance(base: str, key: str) -> float:
    """The account's credits now; read either side of a task, it is what it cost."""
    return float(S.call("GET", base + "/openapi/v1/balance", key).get("balance", 0.0))


SERVICE = S.Service(
    name="meshy", media=("mesh",), hosts=("meshy",),
    submit=submit, poll=poll, deliver=deliver, balance=balance,
)
