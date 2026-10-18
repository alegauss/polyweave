"""A paid provider is an adapter, and one `buy` spends through it (§PW516).

Each provider is a module under `services/` holding one `SERVICE`: what it sells, the
hosts its base is on, and the halves of a purchase: `submit` sends what was asked and
answers a handle, `poll` asks after it until it is finished where the provider works
asynchronously, and `deliver` says what arrived, a link or the bytes, under which task
id, and what the provider reported of it. What the domain asks for is an `Order` in its
own words (a route, a prompt, the pictures, a model); the adapter turns it into the
provider's request.

`buy` is the order of doors every purchase goes through, written once:

    1. the ceiling is asked for the quote, and nothing is sent where it refuses
    2. the charge is owed before the request goes, so a purchase the provider took and
       never delivered is still counted against the ceiling (§PW179); a request the
       provider refused takes its charge back off at once
    3. the balance is read, the request submitted and asked after, the balance read
    4. the bytes are taken delivery of, recorded and ledgered, and the charge settled

A link that cannot be read leaves the charge owed under the task's own id with the
link, for `picture.collect` to take delivery of later. A domain names what it wants and
never calls `purchase.allow` itself, so a provider added here cannot be bought from
without the bound.
"""

from __future__ import annotations

import importlib
import json
import pkgutil
import time
import uuid
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
    #: The quote from the project's `prices` row, which decides whether it may be spent;
    #: per output, where the provider bills per output.
    price: float
    #: What is asked, in the words the adapter reads.
    asked: dict
    root: Path
    #: What `purchase.capture` keeps beside the bytes: `out`, `prompt`, `reference`,
    #: `bought`, `engine`, `details`, `inputs`.
    kept: dict = field(default_factory=dict)
    #: The quote as `client.priced` reached it, where it was counted by the unit, so a
    #: refusal says what the count came to (§PW320).
    priced: dict | None = None
    #: (bytes, details) -> (bytes, details): what the domain does to delivered bytes
    #: before they are kept, such as a transcode to the cue's format.
    shaped: Callable[[bytes, dict], tuple[bytes, dict]] | None = None


@dataclass(frozen=True)
class Part:
    """One of several files a single purchase delivers, which share its charge."""

    task: str
    body: bytes
    out: str
    details: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Delivery:
    """What a finished purchase delivers, and what the provider said about it."""

    #: The provider's id for what was bought; the ledger's is `<service>:<task>`.
    task: str
    #: Where to take delivery from, or the bytes where the answer carried them.
    link: str | None = None
    body: bytes | None = None
    #: How many outputs the provider billed, which the quote is multiplied by.
    outputs: int = 1
    #: What the provider says it charged, where it says, in the ceiling's unit.
    reported: float | None = None
    #: What the provider reported about what it made, kept on the record.
    details: dict = field(default_factory=dict)
    #: What the record's engine adds, such as the plan tier that licenses it (§PW448).
    engine: dict = field(default_factory=dict)
    #: Several files from one call, each kept and ledgered with its share of the
    #: charge, in place of `link` or `body`.
    parts: tuple[Part, ...] = ()


@dataclass(frozen=True)
class Service:
    """One provider, as a module under `services/` declares it in `SERVICE`."""

    name: str
    #: What it sells, as `purchase.BOUGHT` names it.
    media: tuple[str, ...]
    #: A project's base on one of these hosts is spoken to by this adapter.
    hosts: tuple[str, ...]
    #: (order) -> a handle on what was sent: a task id, or a synchronous answer.
    submit: Callable[[Order], Any]
    #: (order, handle, finished) -> what arrived.
    deliver: Callable[[Order, Any, Any], Delivery]
    #: (order, handle, report) -> the finished answer; none where `submit` answers it.
    poll: Callable[[Order, Any, Any], Any] | None = None
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


def buy(adapter: Service, order: Order, report=None) -> dict | list[dict]:
    """Spend on one order through its adapter, against the ceiling; the ledger entry.

    The only path a purchase takes from a quote to a ledger entry: nothing is sent
    before the ceiling allows the quote, the charge is owed from the moment it is
    sent, and nothing is ledgered before the bytes are on disk and recorded. A
    delivery in several parts answers an entry for each, in order.
    """
    root = order.root
    if order.priced is not None:
        purchase.allow_priced(order.priced, root=root, service=order.service)
    else:
        purchase.allow(order.price, root=root, service=order.service)
    pending = f"{order.service}:sent:{uuid.uuid4().hex[:12]}"
    purchase.owe({"task_id": pending, "service": order.service,
                  "credits": order.price, "expected_credits": order.price,
                  "measured": False, "outputs": 1,
                  "artefact": order.kept.get("out")}, root=root)
    try:
        before = adapter.balance(order.base, order.key) if adapter.balance else None
        handle = adapter.submit(order)
    except Exception:
        # Refused before the provider took it, so nothing was charged.
        purchase.settle(pending, root=root)
        raise
    if not handle:
        purchase.settle(pending, root=root)
        raise PolyweaveError(
            "fetch.service-error",
            "the service accepted the request and returned no task id",
            "read the service's answer; nothing was ledgered",
        )
    finished = adapter.poll(order, handle, report) if adapter.poll else handle
    got = adapter.deliver(order, handle, finished)
    after = adapter.balance(order.base, order.key) if adapter.balance else None
    details = {**(order.kept.get("details") or {}), **adapter.details, **got.details}
    kept = {
        **order.kept,
        **({"details": details} if details else {}),
        **({"engine": {**(order.kept.get("engine") or {}), **got.engine}}
           if got.engine else {}),
        "task_id": f"{order.service}:{got.task}",
        "credits": round(order.price * got.outputs, 6),
        "outputs": got.outputs,
        "reported": got.reported,
        "balance_before": before,
        "balance_after": after,
        "service": order.service,
    }
    if got.parts:
        # One call answered every part, so each carries its share of the charge: of
        # what the balance readings measured where there are two, else of what the
        # provider reported, and never the whole difference on every part.
        share = len(got.parts)
        measured = (before - after if before is not None and after is not None
                    else got.reported)
        entries = [
            purchase.capture(one.body, **{
                **kept,
                "out": one.out,
                "task_id": f"{order.service}:{one.task}",
                "credits": round(kept["credits"] / share, 6),
                "reported": None if measured is None else round(measured / share, 6),
                "balance_before": None,
                "balance_after": None,
                "details": {**details, **one.details},
            }, root=root)
            for one in got.parts
        ]
        purchase.settle(pending, root=root)
        return entries
    if got.body is not None:
        body = got.body
        if order.shaped is not None:
            body, shaped = order.shaped(body, kept.get("details") or {})
            kept["details"] = shaped
        entry = purchase.capture(body, **kept, root=root)
        purchase.settle(pending, root=root)
        return entry
    purchase.settle(pending, root=root)
    if report is not None:
        report.stage("downloading", progress=0.9, note="taking delivery of it")
    return delivered(got.link, kept, root)


def delivered(link: str, kept: dict, root) -> dict:
    """Take delivery and ledger it, or owe the charge where delivery fails (§PW179).

    The service has charged by now. A download that fails leaves no asset, so nothing
    may enter the ledger, and yet the ceiling must see the spend: the charge goes on the
    owed list, which `spent` counts, with the link, for `picture.collect` to retry.
    """
    try:
        body = download(link)
    except PolyweaveError as missed:
        purchase.owe({**_owed(kept), "link": link, "capture": kept}, root=root)
        raise PolyweaveError(
            "fetch.nothing-arrived",
            "it was made and charged, and its link could not be read; the charge is "
            "counted against the ceiling as owed",
            f"call picture.collect with task_id {kept['task_id']!r} while the link "
            "lasts; it lands it and moves the charge into the ledger",
            detail=missed.detail,
        ) from missed
    entry = purchase.capture(body, **kept, root=root)
    purchase.settle(kept["task_id"], root=root)
    return entry


def _owed(kept: dict) -> dict:
    reported = kept.get("reported")
    return {
        "task_id": kept["task_id"],
        "service": kept["service"],
        "credits": reported if reported is not None else kept["credits"],
        "expected_credits": kept["credits"],
        "measured": reported is not None,
        "outputs": kept.get("outputs", 1),
        "artefact": kept["out"],
    }


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
