"""Work that takes longer than a moment, held by a handle instead of a wait.

    store = JobStore(root=".")
    handle = store.start("tools/art/bake.py:render", kind="bake", args={"size": 512})
    store.poll(handle["job"])            # -> stage, progress, elapsed_s
    store.result(handle["job"], wait=True)
    store.cancel(handle["job"])

`docs/specs/tool-surface.md` §1 is the contract, and `runner.py` is where it is kept.
"""

from ..errors import PolyweaveError
from .report import Report
from .runner import HEARTBEAT_S, MAX_PARALLEL, RETAIN_S, STALE_AFTER_S, JobStore
from .stages import KINDS, TERMINAL, is_terminal, stages_for

__all__ = [
    "HEARTBEAT_S",
    "KINDS",
    "MAX_PARALLEL",
    "RETAIN_S",
    "STALE_AFTER_S",
    "JobStore",
    "PolyweaveError",
    "Report",
    "TERMINAL",
    "is_terminal",
    "stages_for",
]
