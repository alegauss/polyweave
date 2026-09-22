"""What a target uses to say where it got to.

Its own module rather than part of `worker`, because `python -m polyweave.jobs.worker`
re-executes the module it is given: anything the package imports eagerly would be loaded
twice, and the interpreter says so in every worker log.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from ..errors import PolyweaveError
from . import record as rec
from .stages import check_stage, is_terminal


class Report:
    """The running job's half of the record.

    Every write replaces the whole record in one step, so a poll from another process
    reads one version or the other and never half of each. The worker is the only writer
    while a job runs, so nothing here has to merge.
    """

    def __init__(self, record_path: Path, state: dict) -> None:
        self._path = record_path
        self._state = state
        self._lock = threading.Lock()

    @property
    def job(self) -> str:
        return self._state["job"]

    @property
    def kind(self) -> str:
        return self._state["kind"]

    def stage(
        self,
        stage: str,
        *,
        progress: float | None = None,
        note: str | None = None,
    ) -> None:
        """Move to `stage`, which must be one this kind of job may report."""
        check_stage(self._state["kind"], stage)
        if is_terminal(stage):
            raise PolyweaveError(
                "job.stage-terminal",
                f"a target may not report {stage!r} itself",
                "return a value to finish, or raise to fail",
            )
        self._set(stage=stage, progress=progress, note=note)

    def progress(self, value: float, *, note: str | None = None) -> None:
        """Say how far along the current stage is, as a fraction of one."""
        if not 0.0 <= value <= 1.0:
            raise PolyweaveError(
                "job.bad-progress",
                f"progress is a fraction of one, so {value!r} is out of range",
                "pass a number between 0.0 and 1.0",
            )
        self._set(progress=value, note=note)

    def note(self, text: str) -> None:
        """A sentence a person reads, next to the stage a caller branches on."""
        self._set(note=text)

    def _set(self, **fields: Any) -> None:
        with self._lock:
            for key, value in fields.items():
                if value is not None or key == "note":
                    self._state[key] = value
            self._state["elapsed_s"] = round(time.time() - self._state["started_ts"], 3)
            rec.write_record(self._path, self._state)

    def finish(self, status: str, **fields: Any) -> None:
        """The last version of the record. The worker's call, never a target's."""
        with self._lock:
            now = time.time()
            self._state.update(fields)
            self._state["stage"] = status
            self._state["status"] = status
            self._state["ended_ts"] = now
            self._state["ended_at"] = rec.stamp(now)
            self._state["elapsed_s"] = round(now - self._state["started_ts"], 3)
            rec.write_record(self._path, self._state)
