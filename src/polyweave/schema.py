"""What the service accepts, learned once and kept.

The evidence is §PW19. A request the server refuses never enqueues a task, so a
rejection is free information: send an empty payload to learn the required fields, then
one field at a time with a value no enumeration could hold, to make the server print
that field's permitted set. That is how Cottony's client was written.

**The trap that makes it honest is that an unknown field is dropped in silence.** A
field passing validation proves nothing at all — only an *invalid value* proves a field
is read. So every probe carries a deliberately made-up field as its control, and a field
is marked `proved` only where an invalid value came back rejected.

None of that knowledge was kept anywhere. Here it is a file in the project, and the
client validates against it **before sending**, so a typo in a field name is a local
refusal rather than a silent no-op, and re-learning after a service change is one call.
"""

from __future__ import annotations

import tomllib
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from .config import load
from .describe import Param, operation
from .errors import PolyweaveError
from .files import read_text_retrying, write_atomic

#: The made-up field every probe carries. If the server never complains about it, it
#: drops unknown fields in silence — which is the fact that makes a passing field
#: worthless as evidence, and the reason this is in every request the probe sends.
CONTROL = "polyweave_control_field"

#: A value no enumeration could hold, for making a server print what it does accept.
IMPOSSIBLE = "__polyweave_impossible__"


def where(root: str | Path = ".") -> Path:
    """Where the learned schema lives. TOML, because a person reads and corrects it."""
    config = load(root)
    return config.path("service.schema")


@operation("schema.read")
def read(root: Annotated[str, Param("the project whose schema this is")] = ".") -> dict:
    """The schema this project has learned, or nothing if it never has."""
    path = where(root)
    text = read_text_retrying(path)
    if text is None:
        return {}
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise PolyweaveError(
            "fetch.schema-malformed",
            f"{path} is not readable as TOML",
            "fix the syntax the detail points at, or learn the schema again",
            detail=str(exc),
        ) from exc


def write(schema: dict, root: str | Path = ".") -> Path:
    """Write the schema where the client will read it before every send."""
    path = where(root)
    write_atomic(path, _as_toml(schema))
    return path


@operation("schema.validate")
def validate(
    payload: Annotated[dict, Param("the request about to be sent")],
    *,
    root: Annotated[str, Param("the project whose schema this is")] = ".",
    schema: Annotated[dict, Param("a schema to use instead of the learned one")] = None,
) -> dict:
    """Refuse a payload here, before sending, against what the service takes.

    A local refusal beats a silent no-op: a field the service drops is a setting the
    caller believes is in effect and is not.
    """
    known = schema if schema is not None else read(root)
    fields = known.get("field") or {}
    if not fields:
        raise PolyweaveError(
            "fetch.no-schema",
            "nothing is known about what this service accepts",
            f"learn it once and keep it in {where(root)}; until then a payload cannot "
            f"be checked before it is sent",
        )

    unknown = sorted(set(payload) - set(fields))
    if unknown:
        raise PolyweaveError(
            "fetch.unknown-field",
            f"the service has no {', '.join(unknown)}",
            f"it takes {', '.join(sorted(fields))}; a field it does not know is "
            f"dropped in silence, so this is refused here instead",
        )
    missing = sorted(
        name for name, f in fields.items() if f.get("required") and name not in payload
    )
    if missing:
        raise PolyweaveError(
            "fetch.missing-field",
            f"the service requires {', '.join(missing)}",
            f"pass {', '.join(f'{m}=…' for m in missing)}",
        )
    for name, value in payload.items():
        choices = fields[name].get("choices")
        if choices and fields[name].get("proved") and value not in choices:
            raise PolyweaveError(
                "fetch.bad-choice",
                f"{name} is not {value!r} on this service",
                f"pass one of {', '.join(str(c) for c in choices)}",
            )
    return dict(payload)


# -- learning it ---------------------------------------------------------------------


def learn(
    send: Callable[[dict], dict],
    candidates: Sequence[str],
    *,
    base: dict | None = None,
    root: str | Path = ".",
    control: str = CONTROL,
    balance: Callable[[], float] | None = None,
) -> dict:
    """Probe the service for its shape, spending nothing, and keep what comes back.

    `send` takes a payload and returns `{"ok", "message", "fields", "choices"}` — the
    caller's adapter, because only it knows how this service words a refusal.

    `balance` is read either side of the run and the difference reported, which is the
    only proof that the probing really was free.
    """
    spent_before = float(balance()) if balance else None
    probes = 0

    # An empty payload: whatever the server names is what it requires.
    empty = send({control: IMPOSSIBLE})
    probes += 1
    required = list(empty.get("fields") or [])
    drops_unknown = bool(empty.get("ok")) or control not in (empty.get("message") or "")

    names = sorted(set(candidates) | set(required))
    fields = {
        n: {"required": n in required, "proved": False, "choices": []} for n in names
    }

    # A server will not look past a required field that is missing, so the probe
    # **bootstraps a valid payload as it learns**: fill in what is known, leave the rest
    # impossible, go round again.
    #
    # Every payload must be one the server is certain to refuse, because only a refusal
    # is free. The first pass is guaranteed a refusal by having no valid value for
    # anything; after that, a field already proved to be enumerated is held at an
    # impossible value as the **anchor**, and without one the probing stops rather than
    # risk a request the server might accept and charge for.
    unknown = set(names)
    anchor: str | None = None
    while unknown:
        payload = {**_valid(fields, base), control: IMPOSSIBLE}
        for name in unknown:
            payload[name] = IMPOSSIBLE
        if anchor:
            payload[anchor] = IMPOSSIBLE
        answer = send(payload)
        probes += 1
        if answer.get("ok"):  # pragma: no cover - the anchor exists to prevent this
            break

        learned = set()
        for name in answer.get("fields") or []:
            choices = list((answer.get("choices") or {}).get(name) or [])
            if name in fields and choices and not fields[name]["proved"]:
                # An invalid value came back refused **with the permitted set**, which
                # is the only thing that proves the field is read at all.
                fields[name].update(proved=True, choices=choices)
                learned.add(name)
        unknown -= learned
        anchor = anchor or next(iter(sorted(learned)), None)
        if not learned or not anchor:
            break

    spent_after = float(balance()) if balance else None
    schema = {
        "learned_at": datetime.now(tz=UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "drops_unknown": drops_unknown,
        "control": control,
        "probes": probes,
        "credits": None
        if spent_before is None
        else round(spent_before - spent_after, 4),
        "field": fields,
    }
    write(schema, root)
    return schema


def _valid(fields: dict, base: dict | None) -> dict:
    """The best payload the probe can build from what it has learned so far."""
    payload = dict(base or {})
    for name, field in fields.items():
        if field["choices"]:
            payload.setdefault(name, field["choices"][0])
    return payload


@operation("schema.proved")
def proved(
    schema: Annotated[dict, Param("a schema, as schema.read returns it")],
) -> list[str]:
    """The fields an invalid value was actually refused for, and nothing else."""
    return sorted(n for n, f in (schema.get("field") or {}).items() if f.get("proved"))


def _as_toml(schema: dict) -> str:
    lines = [
        "# Learned from the service by probing, not written by hand — though fixing",
        "# it by hand is fine, and `learn` again is how it is refreshed.",
        "#",
        "# `proved` means an invalid value for that field came back refused. A field",
        "# that merely passed proves nothing: an unknown field is dropped in silence.",
        "",
    ]
    for key in ("learned_at", "control"):
        if schema.get(key) is not None:
            lines.append(f'{key} = "{schema[key]}"')
    for key in ("drops_unknown",):
        if schema.get(key) is not None:
            lines.append(f"{key} = {str(bool(schema[key])).lower()}")
    for key in ("probes", "credits"):
        if schema.get(key) is not None:
            lines.append(f"{key} = {schema[key]}")
    for name, field in sorted((schema.get("field") or {}).items()):
        lines.append("")
        lines.append(f"[field.{name}]")
        lines.append(f"required = {str(bool(field.get('required'))).lower()}")
        lines.append(f"proved = {str(bool(field.get('proved'))).lower()}")
        choices = field.get("choices") or []
        rendered = ", ".join(f'"{c}"' for c in choices)
        lines.append(f"choices = [{rendered}]")
    return "\n".join(lines) + "\n"


def as_dict(schema: Any) -> dict:  # pragma: no cover - a convenience for callers
    return dict(schema)
