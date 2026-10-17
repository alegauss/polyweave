"""A paid provider is an adapter, and one `buy` spends through it (§PW516).

Each provider is a module under `services/` holding one `SERVICE`: what it sells, the
hosts its base is on, and the three halves of an asynchronous purchase, `submit`, `poll`
and `fetch`, with the balance read either side where the provider publishes one. What
the domain asks for is an `Order` in its own words (a route, a prompt, the pictures, a
model); the adapter turns it into the provider's request.

`buy` is the order of doors every purchase goes through, written once: the ceiling is
asked, the balance read, the task submitted and polled, the balance read again, and the
bytes captured into the record and the ledger. A domain names what it wants and never
calls `purchase.allow` itself, so a provider added here cannot be bought from without
the bound.
"""

from __future__ import annotations

import importlib
import json
import pkgutil
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from polyweave.kernel.errors import PolyweaveError

from . import client, purchase

#: How often a task is asked after, and for how long, before the call gives up on it.
POLL_EVERY = 5.0
POLL_TIMEOUT = 900

TIMEOUT = 120


@dataclass(frozen=True)
class Order:
    """One purchase, in the domain's words, and how its record is kept."""

    #: The project's `[service.<name>]` it is bought from and charged to.
    service: str
    base: str
    key: str
    #: The quote from the project's `prices` row, which decides whether it may be spent.
    price: float
    #: What is asked, which the adapter reads: `route`, `prompt`, `pictures`, `model`,
    #: `polycount`.
    asked: dict
    root: Path
    #: What `purchase.capture` keeps beside the bytes: `out`, `prompt`, `reference`,
    #: `bought`, `engine`, `details`, `inputs`.
    kept: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Service:
    """One provider, as a module under `services/` declares it in `SERVICE`."""

    name: str
    #: What it sells, as `purchase.BOUGHT` names it.
    media: tuple[str, ...]
    #: A project's base on one of these hosts is spoken to by this adapter.
    hosts: tuple[str, ...]
    #: (order) -> the provider's task id.
    submit: Callable[[Order], str]
    #: (order, task, report) -> the finished task, as the provider answers it.
    poll: Callable[[Order, str, Any], dict]
    #: (order, finished) -> the bytes delivered.
    fetch: Callable[[Order, dict], bytes]
    #: (base, key) -> the account's balance now; none where the provider publishes none,
    #: and the cost recorded is then the quote, marked as not measured.
    balance: Callable[[str, str], float] | None = None
    #: What the record adds for every purchase from it, such as Rodin's quad mesh.
    details: dict = field(default_factory=dict)


def providers() -> dict[str, Service]:
    """Every adapter under `services/`, by name; a new provider is a new module."""
    import polyweave.services as package

    found = {}
    for one in pkgutil.iter_modules(package.__path__):
        declared = getattr(
            importlib.import_module(f"{package.__name__}.{one.name}"), "SERVICE", None)
        if isinstance(declared, Service):
            found[declared.name] = declared
    return found


def provider(base: str, media: str, default: str) -> Service:
    """The adapter a project's base is spoken to by, or `default` where no host says."""
    every = providers()
    for one in every.values():
        if media in one.media and any(host in base for host in one.hosts):
            return one
    return every[default]


def buy(adapter: Service, order: Order, report=None) -> dict:
    """Spend on one order through its adapter, against the ceiling; the ledger entry.

    The only path a purchase takes from a quote to a ledger entry: nothing is sent
    before the ceiling allows the quote, and nothing is ledgered before the bytes are
    on disk and recorded.
    """
    purchase.allow(order.price, root=order.root, service=order.service)
    before = adapter.balance(order.base, order.key) if adapter.balance else None
    task = adapter.submit(order)
    if not task:
        raise PolyweaveError(
            "fetch.service-error",
            "the service accepted the request and returned no task id",
            "read the service's answer; nothing was ledgered",
        )
    finished = adapter.poll(order, task, report)
    if report is not None:
        report.stage("downloading", progress=0.9, note="taking delivery of it")
    body = adapter.fetch(order, finished)
    after = adapter.balance(order.base, order.key) if adapter.balance else None
    kept = dict(order.kept)
    if adapter.details:
        kept["details"] = {**(kept.get("details") or {}), **adapter.details}
    return purchase.capture(
        body,
        task_id=f"{order.service}:{task}",
        credits=order.price,
        balance_before=before,
        balance_after=after,
        service=order.service,
        root=order.root,
        **kept,
    )


@dataclass(frozen=True)
class Asked:
    """One answer to asking after a task, in the words `waited` reads."""

    #: `done`, `failed`, or anything else for still working.
    state: str
    #: The provider's own answer: returned when done, quoted when it failed.
    found: Any
    #: The provider's word for the state, as a person reads it.
    said: str
    progress: float = 0.0
    reason: str = "no reason given"


def waited(task: str, ask: Callable[[], Asked], report) -> Any:
    """Ask after one task until it is done, fails or runs out of time."""
    started = time.monotonic()
    while True:
        one = ask()
        if one.state == "done":
            return one.found
        if one.state == "failed":
            raise PolyweaveError(
                "fetch.service-error",
                f"task {task} {one.said}: {one.reason}",
                "reword the request or ask again; nothing was ledgered, and the "
                "balance readings will show whether the service charged",
                detail=json.dumps(one.found)[:400],
            )
        if time.monotonic() - started > POLL_TIMEOUT:
            raise PolyweaveError(
                "fetch.service-error",
                f"task {task} was still {one.said} after {POLL_TIMEOUT}s",
                f"ask after it later by its id, {task}; nothing was ledgered",
            )
        if report is not None:
            report.stage("building", progress=min(0.8, one.progress),
                         note=f"task {task} is {one.said}")
        time.sleep(POLL_EVERY)


def call(method: str, url: str, key: str, payload: dict | None = None) -> dict:
    """One JSON call with the bearer key, a refusal turned into a code."""
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Authorization": f"Bearer {key}"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    answer = _sent(url, method=method, data=body, headers=headers)
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


def form(url: str, key: str, fields: dict, files: list) -> dict:
    """One multipart POST with the bearer key: `files` as [(field, path)], a refusal
    turned into a code as `call` turns one."""
    import uuid

    boundary = uuid.uuid4().hex
    parts = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
        f"{value}\r\n".encode() for name, value in fields.items()
    ]
    for name, path in files:
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
            f'filename="{path.name}"\r\nContent-Type: {client.mime(path)}\r\n\r\n'
            .encode() + client.sent_bytes(path) + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    answer = _sent(url, method="POST", data=b"".join(parts), headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": f"multipart/form-data; boundary={boundary}"})
    if answer.status >= 400:
        raise PolyweaveError(
            "fetch.service-error", f"the service answered {answer.status} to {url}",
            "read the detail; a 401 is a key the service does not accept",
            detail=answer.body[:400].decode("utf-8", "replace"),
        )
    return json.loads(answer.body or b"{}")


def download(link: str) -> bytes:
    """The bytes a finished task links to."""
    return client.download(link)


def _sent(url: str, **how) -> client.Answer:
    try:
        return client.send(url, timeout=TIMEOUT, **how)
    except client.Unreached as exc:
        raise PolyweaveError(
            "fetch.service-error",
            f"the service could not be reached at {url}",
            "check the base under [service] and the network",
            detail=exc.reason,
        ) from exc
