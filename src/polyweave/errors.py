"""The shape a failure arrives in.

`docs/specs/tool-surface.md` §3: a failure carries a stable code, a sentence saying what
is wrong, and the call that closes it. This module is the carrier and the code grammar
only — the registry of codes for the rest of the surface, and the remedies that fill in
their own arguments, belong to PW4.
"""

from __future__ import annotations

import re

# `area.kebab-case`, the namespaces §3 fixes. A code is part of the published contract,
# so it is checked where it is constructed rather than where it is read.
_AREAS = ("render", "mesh", "fetch", "post", "config", "job", "geom", "spec", "op")
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
    ) -> None:
        if not _CODE.match(code):
            raise ValueError(
                f"{code!r} is not a code: expected <area>.<kebab-case>, "
                f"where area is one of {', '.join(_AREAS)}"
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

    def as_dict(self) -> dict:
        """The wire form, with `detail` present only when there is one."""
        out = {"code": self.code, "message": self.message, "remedy": self.remedy}
        if self.detail:
            out["detail"] = self.detail
        return out

    @classmethod
    def from_dict(cls, payload: dict) -> PolyweaveError:
        return cls(
            payload["code"],
            payload["message"],
            payload["remedy"],
            payload.get("detail"),
        )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"PolyweaveError({self.code!r}, {self.message!r})"
