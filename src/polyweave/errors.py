"""The shape a failure arrives in, and the read that explains one.

`docs/specs/tool-surface.md` §3: a failure carries a stable code, a sentence saying what
is wrong, and the call that closes it. A traceback says where the code gave up, which is
rarely where the caller should act, so it goes in `detail` and never in `message`.

The measure to hold this to is whether a failure can be answered **without opening any
implementation file**. That is why a code must be declared in `codes.py` before it can
be raised: an undeclared code is one `explain` cannot answer, so it is refused where it
is constructed rather than discovered by whoever receives it.
"""

from __future__ import annotations

import contextlib
import difflib
import re
import traceback
from collections.abc import Iterable, Iterator
from typing import Any

from . import codes as _codes
from . import doors as _doors

# `area.kebab-case`, the namespaces §3 fixes. A code is part of the published contract,
# so it is checked where it is constructed rather than where it is read.
_AREAS = tuple(_codes.AREAS)
_CODE = re.compile(rf"^({'|'.join(_AREAS)})\.[a-z0-9]+(-[a-z0-9]+)*$")


class PolyweaveError(Exception):
    """An error that names the door that closes it.

    `message` never carries a traceback; `detail` may.
    """

    def __init__(
        self,
        code: str,
        message: str,
        remedy: str,
        detail: str | None = None,
        *,
        call: dict | None = None,
        given: str | None = None,
        allowed: Iterable[str] | None = None,
        example: str | None = None,
        at: str | None = None,
    ) -> None:
        if not _CODE.match(code):
            raise ValueError(
                f"{code!r} is not a code: expected <area>.<kebab-case>, "
                f"where area is one of {', '.join(_AREAS)}"
            )
        if not _codes.known(code):
            raise ValueError(
                f"{code!r} is not declared in polyweave/codes.py, so `explain` could "
                f"not answer it; declare what it means and what produces it there first"
            )
        if not remedy:
            raise ValueError(
                f"{code} carries no remedy, and an error without one is a traceback "
                f"with better manners"
            )
        super().__init__(message)
        self.code = code
        self.message = message
        self.remedy = remedy
        self.detail = detail
        #: The call the remedy names, as data, where it names one (§PW127).
        self.call = call
        #: Where the refusal is about a name (§PW128): the names that would have
        #: worked, the nearest of them, a correct fragment, and where in the input.
        self.allowed = sorted({str(one) for one in allowed}) if allowed else []
        self.did_you_mean = near(given, self.allowed) if given is not None else None
        self.example = example
        self.at = at

    def as_dict(self) -> dict:
        """The wire form, every optional field present only when it has something."""
        out = {"code": self.code, "message": self.message, "remedy": self.remedy}
        if self.detail:
            out["detail"] = self.detail
        if self.call:
            out["call"] = _doors.as_data(self.call)
        for name in ("allowed", "did_you_mean", "example", "at"):
            value = getattr(self, name)
            if value:
                out[name] = value
        return out

    @classmethod
    def from_dict(cls, payload: dict) -> PolyweaveError:
        call = payload.get("call")
        back = cls(
            payload["code"],
            payload["message"],
            payload["remedy"],
            payload.get("detail"),
            call={"operation": call["operation"], "arguments": call["arguments"]}
            if call
            else None,
            allowed=payload.get("allowed"),
            example=payload.get("example"),
            at=payload.get("at"),
        )
        back.did_you_mean = payload.get("did_you_mean")
        return back

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"PolyweaveError({self.code!r}, {self.message!r})"


def _plain(name: str) -> str:
    """A name with case and separators taken out, which is how a typo differs."""
    return re.sub(r"[\s_\-.]+", "", str(name).lower())


def near(given: Any, allowed: Iterable[str]) -> str | None:
    """The one allowed name `given` most likely meant, or None when nothing is close.

    Shio's rule, taken whole: case- and separator-insensitive, deterministic on ties,
    and silent when nothing is close, because a wrong guess costs more than none.
    """
    choices = sorted({str(one) for one in allowed})
    if given is None or not choices or str(given) in choices:
        return None
    wanted = _plain(given)
    by_plain: dict[str, str] = {}
    for one in choices:
        by_plain.setdefault(_plain(one), one)
    if wanted in by_plain and by_plain[wanted] != str(given):
        return by_plain[wanted]
    found = difflib.get_close_matches(wanted, list(by_plain), n=1, cutoff=0.75)
    return by_plain[found[0]] if found else None


def explain(code: str) -> dict:
    """What a code means, what produces it, and the general shape of the fix.

    The read a caller makes when planning for a failure. The `remedy` on a raised error
    is the same answer with the arguments filled in, which is the one to act on.
    """
    try:
        declared = _codes.CODES[code]
    except KeyError:
        near = difflib.get_close_matches(code, _codes.CODES, n=3, cutoff=0.6)
        area = _codes.area_of(code)
        raise PolyweaveError(
            "spec.unknown-code",
            f"{code!r} is not a code this plugin publishes",
            f"did you mean {', '.join(near)}?"
            if near
            else f"codes() lists them; {area!r} covers "
            f"{_codes.AREAS.get(area, 'nothing here')}",
        ) from None
    return {
        "code": code,
        "area": _codes.area_of(code),
        "about": _codes.AREAS[_codes.area_of(code)],
        "means": declared.means,
        "when": declared.when,
        "doors": list(declared.doors),
        "calls": [_doors.as_data(one) for one in declared.calls],
    }


def codes(area: str | None = None) -> list[str]:
    """Every code this plugin publishes, or every code in one area."""
    if area is None:
        return sorted(_codes.CODES)
    if area not in _codes.AREAS:
        raise PolyweaveError(
            "spec.unknown-area",
            f"{area!r} is not an area",
            f"name one of {', '.join(sorted(_codes.AREAS))}",
        )
    return _codes.in_area(area)


@contextlib.contextmanager
def guard(code: str, *, remedy: str, message: str | None = None) -> Iterator[None]:
    """Turn whatever is raised inside into a typed failure, keeping the traceback.

    The boundary an operation puts around work it did not write. A failure that is
    already typed passes through untouched, because it already names its own door.
    """
    try:
        yield
    except PolyweaveError:
        raise
    except Exception as exc:
        raise PolyweaveError(
            code,
            message or f"{type(exc).__name__}: {exc}",
            remedy,
            detail=traceback.format_exc(),
        ) from exc
