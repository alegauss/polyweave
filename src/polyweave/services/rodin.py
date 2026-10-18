"""Rodin, Hyper3D's v2 API (§PW446, §PW516).

A task is sent as a form, its jobs asked after by the subscription key it answers, and
its files listed by the task's uuid. Rodin publishes no balance, so its cost is the
project's quoted price, recorded as not measured.
"""

from __future__ import annotations

import json

from polyweave.kernel.errors import PolyweaveError

from . import service as S

ROUTES = {"make": "/api/v2/rodin", "status": "/api/v2/status",
          "download": "/api/v2/download"}

#: The subscription key each task is asked after by, kept between submit and poll.
_SUBSCRIBED: dict[str, str] = {}


def submit(order: S.Order) -> str:
    asked = order.asked
    fields = {"tier": asked["model"], "mesh_mode": "Quad",
              "quality_override": int(asked["polycount"]),
              "geometry_file_format": "glb", "material": "Shaded"}
    if asked.get("prompt") is not None:
        fields["prompt"] = asked["prompt"]
    made = S.form(order.base + ROUTES["make"], order.key, fields,
                  [("images", one) for one in asked.get("pictures", ())])
    task = made.get("uuid")
    subscription = (made.get("jobs") or {}).get("subscription_key")
    if not task or not subscription:
        raise PolyweaveError(
            "fetch.service-error",
            "the service accepted the request and returned no task or subscription key",
            "read the detail; nothing was ledgered",
            detail=json.dumps(made)[:400],
        )
    _SUBSCRIBED[task] = subscription
    return task


def poll(order: S.Order, task: str, report) -> str:
    subscription = _SUBSCRIBED.pop(task)

    def ask() -> S.Asked:
        jobs = S.call("POST", order.base + ROUTES["status"], order.key,
                      {"subscription_key": subscription}).get("jobs") or []
        states = [str(job.get("status")) for job in jobs]
        done = sum(1 for state in states if state == "Done")
        return S.Asked(
            state="failed" if "Failed" in states
            else "done" if states and done == len(states) else "working",
            found=jobs if "Failed" in states else task,
            said="failed" if "Failed" in states else ", ".join(states) or "queued",
            progress=0.2 + 0.6 * done / max(1, len(states)),
            reason="a job failed",
        )

    return S.waited(task, ask, report)


def deliver(order: S.Order, task: str, finished: str) -> S.Delivery:
    files = S.call("POST", order.base + ROUTES["download"], order.key,
                   {"task_uuid": task}).get("list") or []
    link = next((one.get("url") for one in files
                 if str(one.get("name", "")).lower().endswith(".glb")), None)
    if not link:
        raise PolyweaveError(
            "fetch.nothing-arrived",
            f"task {task} finished with no .glb to take delivery of",
            "look at the task on the service; nothing was ledgered",
            detail=json.dumps(files)[:400])
    return S.Delivery(task=task, link=link)


SERVICE = S.Service(
    name="rodin", media=("mesh",), hosts=("hyper3d", "deemos"),
    submit=submit, poll=poll, deliver=deliver, details={"mesh_mode": "Quad"},
)
