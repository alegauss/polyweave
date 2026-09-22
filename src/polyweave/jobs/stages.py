"""The stage vocabulary, closed on purpose.

`docs/specs/tool-surface.md` §1: a caller branches on a word rather than parsing a
message, which only holds if the words are few and fixed. A stage outside its kind's
vocabulary is refused where it is set, so a typo never reaches a caller as a state.
"""

from __future__ import annotations

from ..errors import PolyweaveError

QUEUED = "queued"
BUILDING = "building"
RENDERING = "rendering"
DOWNLOADING = "downloading"
DONE = "done"
FAILED = "failed"
CANCELLED = "cancelled"

#: Reached by every kind, and the three a `status` may be.
TERMINAL = (DONE, FAILED, CANCELLED)

#: The four operations §1 names as asynchronous, each with the stages it may report.
#: `queued` is where a job sits between its record being written and its worker booting.
KINDS: dict[str, tuple[str, ...]] = {
    "bake": (QUEUED, BUILDING, RENDERING),
    "capture": (QUEUED, BUILDING, RENDERING),
    "fetch": (QUEUED, BUILDING, DOWNLOADING),
    "search": (QUEUED, RENDERING),
}


def stages_for(kind: str) -> tuple[str, ...]:
    """The stages `kind` may report, terminal ones included."""
    try:
        running = KINDS[kind]
    except KeyError:
        raise PolyweaveError(
            "job.unknown-kind",
            f"there is no operation kind {kind!r}",
            f"pass kind as one of {', '.join(sorted(KINDS))}",
        ) from None
    return running + TERMINAL


def check_stage(kind: str, stage: str) -> str:
    """Return `stage`, or refuse it against `kind`'s vocabulary."""
    allowed = stages_for(kind)
    if stage not in allowed:
        raise PolyweaveError(
            "job.unknown-stage",
            f"a {kind} job has no stage {stage!r}",
            f"report one of {', '.join(allowed)}",
        )
    return stage


def is_terminal(stage: str | None) -> bool:
    return stage in TERMINAL
