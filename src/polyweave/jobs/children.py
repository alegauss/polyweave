"""Leaving a trail to what a worker spawned, so a sweep can end it afterwards.

§PW37. `cancel` never had this problem: it walks the tree from a living worker, which
both `taskkill /T` and a POSIX process group can do. `sweep` does have it, because by
the time a job is found abandoned the worker is already gone. On POSIX the process group
outlives its leader and an orphan is still reachable by group id; on Windows nothing
connects a dead parent to its children, and the render runs until somebody opens Task
Manager.

The answer is to stop needing the tree. A worker that spawns a renderer writes its pid
down before it waits on it, and a sweep ends those pids directly.

The registration is process-wide because a worker process **is** one job — the worker
runs a single target and exits. Outside a worker nothing is registered and `watch` is a
no-op, which is what makes it safe to call from `engine.run` and anywhere else that
spawns, whether or not a job is driving it.
"""

from __future__ import annotations

import contextlib
import threading
from pathlib import Path

from . import process
from . import record as rec

_lock = threading.Lock()
_where: Path | None = None


def watching(path: Path | None) -> None:
    """Say where spawned pids go, or pass None to stop recording them."""
    global _where
    with _lock:
        _where = None if path is None else Path(path)


def watched() -> Path | None:
    """Where they are going, which is None outside a worker."""
    return _where


def watch(pid: int | None) -> None:
    """Record one spawned process against the running job, if there is one.

    Never raises. A trail that could not be written is a renderer that may leak, and a
    leaked renderer is a much smaller failure than a render that refused to start
    because the bookkeeping around it failed.
    """
    where = _where
    if where is None or not pid or pid <= 0:
        return
    with contextlib.suppress(OSError):
        rec.add_kid(where, pid, process.started_at(pid))


def ended(path: Path) -> list[tuple[int, float | None]]:
    """What is left of the trail: every recorded child that is still running.

    A child that exited normally is simply absent from this, so nothing has to erase it
    and the file keeps its single writer. Ordering is the order they were spawned in.
    """
    return [(pid, since) for pid, since in rec.read_kids(path) if process.alive(pid)]
