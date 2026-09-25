"""An operation says what it takes, and the saying is the signature.

`docs/specs/tool-surface.md` §4: `describe(operation)` returns the parameter set — name,
type, range, default, one sentence — **read from the implementation**, so the
documentation and the code cannot drift apart.

The evidence is §PW3: Cottony's render rig takes fourteen parameters whose only
description is a comment above each field in a thousand-line module. A comment can go
stale silently. A parameter that carries its own sentence in its own annotation cannot,
because deleting the parameter deletes the sentence with it:

    @operation("render.bake", produces="render", injects=("report",))
    def bake(
        report,
        model: Annotated[str, Param("which model to render")],
        size: Annotated[int, Param("square edge", lo=16, hi=4096, unit="px")] = 512,
    ) -> str:
        '''Render one model on the project's rig.'''

Registration is refused where a parameter carries no sentence, which is what keeps the
description complete rather than merely present.
"""

from __future__ import annotations

import contextlib
import importlib
import inspect
import typing
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Annotated, Any, get_args, get_origin

from .errors import PolyweaveError


@dataclass(frozen=True)
class Param:
    """What a caller needs to know about one parameter, next to the parameter."""

    about: str
    lo: float | None = None
    hi: float | None = None
    choices: tuple[Any, ...] | None = None
    unit: str | None = None

    def as_dict(self) -> dict:
        out: dict[str, Any] = {"about": self.about}
        if self.lo is not None or self.hi is not None:
            out["range"] = [self.lo, self.hi]
        if self.choices is not None:
            out["choices"] = list(self.choices)
        if self.unit:
            out["unit"] = self.unit
        return out


@dataclass(frozen=True)
class Operation:
    name: str
    fn: Callable
    summary: str
    produces: str | None
    kind: str | None
    injects: tuple[str, ...]
    parameters: tuple[dict, ...]

    def as_dict(self) -> dict:
        return {
            "operation": self.name,
            "summary": self.summary,
            "produces": self.produces,
            "kind": self.kind,
            "asynchronous": self.kind is not None,
            "parameters": [dict(p) for p in self.parameters],
        }

    @property
    def target(self) -> str:
        """How a job would name this operation's function: `module:function`."""
        return f"{self.fn.__module__}:{self.fn.__qualname__}"


_REGISTRY: dict[str, Operation] = {}

#: The plugin's own modules that register operations, imported on demand so the registry
#: is complete before anything is looked up in it (§PW39). Only this package's own
#: modules are ever imported here: a project's target may need an environment the caller
#: does not have, which is exactly why a job spawns rather than importing.
MODULES: tuple[str, ...] = (
    "polyweave.render",
    "polyweave.accept",
    "polyweave.search",
    "polyweave.calibrate",
    "polyweave.verdict",
    "polyweave.loop",
    "polyweave.port",
    "polyweave.trace",
    "polyweave.provenance",
    "polyweave.units",
    "polyweave.measure",
    "polyweave.cli",
    "polyweave.geometry.review",
    "polyweave.purchase",
    "polyweave.schema",
    "polyweave.engine",
    "polyweave.capture",
    "polyweave.offscreen",
    "polyweave.godot",
    "polyweave.shape",
    "polyweave.reference",
    "polyweave.normalise",
    "polyweave.compose",
    "polyweave.texture",
    "polyweave.clip",
    "polyweave.skeleton",
    "polyweave.sprites",
)


def _type_name(annotation: Any) -> str:
    if get_origin(annotation) is Annotated:
        annotation = get_args(annotation)[0]
    if annotation is inspect.Parameter.empty:
        return "any"
    return getattr(annotation, "__name__", str(annotation).replace("typing.", ""))


def _param_marker(annotation: Any) -> Param | None:
    if get_origin(annotation) is not Annotated:
        return None
    for extra in get_args(annotation)[1:]:
        if isinstance(extra, Param):
            return extra
    return None


def operation(
    name: str,
    *,
    produces: str | None = None,
    kind: str | None = None,
    injects: Sequence[str] = (),
) -> Callable:
    """Register `fn` as an operation a caller can discover and describe.

    `produces` is what §2 asserts about its output; `kind` is the job kind where the
    work is asynchronous. `injects` names the parameters the harness supplies, which a
    caller never passes and never needs described.
    """

    def register(fn: Callable) -> Callable:
        if name in _REGISTRY:
            raise PolyweaveError(
                "op.duplicate",
                f"{name!r} is already registered, by {_REGISTRY[name].fn.__module__}",
                "give this one another name, or delete the operation it shadows",
            )
        summary = (inspect.getdoc(fn) or "").strip().split("\n\n")[0].replace("\n", " ")
        if not summary:
            raise PolyweaveError(
                "op.undocumented",
                f"{name!r} has no docstring, so `describe` has nothing to return",
                "write one sentence saying what the operation does",
            )
        _REGISTRY[name] = Operation(
            name=name,
            fn=fn,
            summary=summary,
            produces=produces,
            kind=kind,
            injects=tuple(injects),
            parameters=tuple(_parameters(name, fn, tuple(injects))),
        )
        return fn

    return register


def _parameters(name: str, fn: Callable, injects: tuple[str, ...]) -> list[dict]:
    signature = inspect.signature(fn)
    try:
        hints = typing.get_type_hints(fn, include_extras=True)
    except Exception:  # noqa: BLE001 - an unresolvable hint is still describable
        hints = {}
    out: list[dict] = []
    for pname, parameter in signature.parameters.items():
        if pname in injects:
            continue
        if parameter.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            raise PolyweaveError(
                "op.open-signature",
                f"{name!r} takes *{pname}, so its parameter set is not a set",
                "name every parameter, or the surface cannot describe itself",
            )
        annotation = hints.get(pname, parameter.annotation)
        marker = _param_marker(annotation)
        if marker is None:
            raise PolyweaveError(
                "op.unannotated",
                f"{name!r} does not say what {pname!r} is for",
                "annotate it as Annotated[<type>, Param('…')], or name it in "
                "`injects` if the harness supplies it",
            )
        required = parameter.default is inspect.Parameter.empty
        out.append(
            {
                "name": pname,
                "type": _type_name(annotation),
                "required": required,
                "default": None if required else parameter.default,
                **marker.as_dict(),
            }
        )
    return out


def load() -> None:
    """Import this package's own operation modules, so the registry is complete.

    Registration happens as a side effect of an import, so anything asking "is this a
    registered operation?" is really asking "has its module been imported yet?" — and a
    parent that never imports the module gets "no" for an operation that plainly exists.
    Importing them here is safe in the way importing a project's target is not: these
    are the plugin's own modules, and `polyweave.render` deliberately keeps `bpy` behind
    a lazy import so that loading it costs nothing and needs no Blender.
    """
    for module in MODULES:
        with contextlib.suppress(ImportError):  # pragma: no cover - always present
            importlib.import_module(module)


def for_target(target: str) -> str | None:
    """The operation a job's `module:function` target is, or None if it is not one.

    None is the ordinary answer, not a failure: a project's own generator named as a
    file path is a legitimate target and has no registration (§PW39). What it means is
    that the worker's own signature check is the only contract that target has.
    """
    load()
    for registered in _REGISTRY.values():
        if registered.target == target:
            return registered.name
    return None


def operations() -> list[str]:
    """Every operation name, sorted."""
    load()
    return sorted(_REGISTRY)


def describe(name: str | None = None) -> dict | list[dict]:
    """One operation's parameter set, or every operation's.

    The registry is loaded first (§PW124): registration is an import's side effect, so
    a fresh process asking `capabilities()` used to list whatever happened to have been
    imported, which could be nothing.
    """
    load()
    if name is None:
        return [_REGISTRY[n].as_dict() for n in operations()]
    try:
        return _REGISTRY[name].as_dict()
    except KeyError:
        raise PolyweaveError(
            "op.unknown",
            f"there is no operation named {name!r}",
            f"describe() with no argument lists them; there "
            f"{'is 1' if len(_REGISTRY) == 1 else f'are {len(_REGISTRY)}'}",
            given=name,
            allowed=_REGISTRY,
        ) from None


def validate(name: str, args: dict) -> dict:
    """Refuse a call against what the operation declared, and fill in the defaults.

    A range that nothing enforces is a comment, and a comment is what §PW3 is about.
    """
    load()  # a fresh process called an operation unknown before it was imported
    try:
        registered = _REGISTRY[name]
    except KeyError:
        raise PolyweaveError(
            "op.unknown",
            f"there is no operation named {name!r}",
            "describe() with no argument lists them",
            given=name,
            allowed=_REGISTRY,
        ) from None

    declared = {p["name"]: p for p in registered.parameters}
    unknown = sorted(set(args) - set(declared))
    if unknown:
        raise PolyweaveError(
            "op.unknown-argument",
            f"{name} takes no {', '.join(unknown)}",
            f"it takes {', '.join(declared) or 'no arguments'}",
            given=unknown[0],
            allowed=declared,
        )
    missing = sorted(n for n, p in declared.items() if p["required"] and n not in args)
    if missing:
        raise PolyweaveError(
            "op.missing-argument",
            f"{name} needs {', '.join(missing)}",
            f"pass {', '.join(f'{n}=…' for n in missing)}",
        )

    resolved = {n: p["default"] for n, p in declared.items() if not p["required"]}
    for key, value in args.items():
        _check_value(name, declared[key], value)
        resolved[key] = value
    return resolved


#: The smallest correct value of each type, for a refusal to show.
_EXAMPLES = {
    "str": '"text"',
    "int": "3",
    "float": "0.5",
    "bool": "true",
    "list": '["a"]',
    "dict": '{"a": 1}',
}

#: What a value of each declared type may be. A type not here (`Any`) takes anything.
_ACCEPTS: dict[str, tuple[type, ...]] = {
    "str": (str,),
    "int": (int,),
    "float": (int, float),
    "bool": (bool,),
    "list": (list, tuple),
    "dict": (dict,),
}


def _check_value(name: str, declared: dict, value: Any) -> None:
    what = declared["name"]
    kinds = _ACCEPTS.get(declared["type"])
    # §PW130: only a ranged value used to be type-checked, so `preview: "yes"` passed
    # and read as true, and `given: "size=2"` reached a function expecting a table.
    # None stays allowed: it is how a caller leaves an optional value to its default.
    wrong = (
        kinds is not None
        and value is not None
        and (
            not isinstance(value, kinds)
            or (isinstance(value, bool) and bool not in kinds)
        )
    )
    if wrong:
        raise PolyweaveError(
            "op.bad-type",
            f"{what} is a {declared['type']} on {name}, and a "
            f"{type(value).__name__} was passed",
            f"pass a {declared['type']}",
            example=_EXAMPLES.get(declared["type"]),
            at=what,
        )
    choices = declared.get("choices")
    if choices is not None and value not in choices:
        raise PolyweaveError(
            "op.bad-choice",
            f"{what} is not {value!r} on {name}",
            f"pass one of {', '.join(repr(c) for c in choices)}",
        )
    span = declared.get("range")
    if span is None:
        return
    lo, hi = span
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise PolyweaveError(
            "op.bad-type",
            f"{what} is a {declared['type']} on {name}, and a "
            f"{type(value).__name__} was passed",
            f"pass a {declared['type']}",
        )
    if (lo is not None and value < lo) or (hi is not None and value > hi):
        span_text = (
            f"{lo} to {hi}"
            if lo is not None and hi is not None
            else (f"at least {lo}" if hi is None else f"at most {hi}")
        )
        raise PolyweaveError(
            "op.out-of-range",
            f"{what} is {span_text} on {name}, and {value!r} was passed",
            f"pass a value {span_text}",
        )
