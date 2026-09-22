"""Start, poll, result, cancel — the four calls §1 of the tool surface fixes.

The point of the shape is that a turn is not spent waiting. `start` returns a handle in
the time it takes to write a file and fork; everything after it is a read of that file.
Four handles is four parallel samples, which is what makes the search in Block C
affordable at all.
"""

from __future__ import annotations

import contextlib
import os
import sys
import time
from pathlib import Path
from typing import Any

from ..errors import PolyweaveError
from . import process
from . import record as rec
from .stages import is_terminal, stages_for

#: How often a worker proves it is still the process the pid names.
HEARTBEAT_S = 2.0

#: How long a silent worker is given before a poll calls it gone. Generous against a
#: loaded machine, and only ever reached when the pid itself still answers — a worker
#: that exited is found the moment it is asked about.
STALE_AFTER_S = 30.0

#: How long a finished job's record is kept before `sweep` collects it.
RETAIN_S = 24 * 60 * 60

#: Matches `[render] max_parallel` in the project config, until PW5 resolves it.
MAX_PARALLEL = 4

#: The directory `polyweave` is importable from, so the worker can import it whether the
#: plugin was installed or is being run out of a checkout.
_PACKAGE_ROOT = Path(__file__).resolve().parents[2]


class JobStore:
    """The jobs of one project tree.

    Nothing is written outside `root`: `work` is the only location this chooses for
    itself, and it belongs in `.gitignore`.
    """

    def __init__(
        self,
        root: str | Path = ".",
        work: str | Path | None = None,
        *,
        max_parallel: int = MAX_PARALLEL,
        heartbeat_s: float = HEARTBEAT_S,
        stale_after_s: float = STALE_AFTER_S,
        python: str | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.work = Path(work) if work else self.root / ".polyweave"
        if not self.work.is_absolute():
            self.work = self.root / self.work
        self.paths = rec.JobPaths(self.work)
        self.max_parallel = max_parallel
        self.heartbeat_s = heartbeat_s
        self.stale_after_s = stale_after_s
        self.python = python or sys.executable

    # -- starting ---------------------------------------------------------------

    def start(
        self,
        target: str,
        *,
        kind: str,
        args: dict | None = None,
        label: str | None = None,
        path: list[str | Path] | None = None,
        env: dict[str, str] | None = None,
    ) -> dict:
        """Spawn `target` as a job and return its handle, without waiting for it."""
        stages_for(kind)  # refuses an unknown kind before anything is written
        args = dict(args or {})
        running = [v for v in self.list() if not is_terminal(v["stage"])]
        if len(running) >= self.max_parallel:
            held = ", ".join(v["job"] for v in running)
            raise PolyweaveError(
                "job.at-capacity",
                f"{len(running)} jobs are already running, which is the limit",
                f"wait for one to finish, cancel one of {held}, or raise "
                f"`[render] max_parallel` above {self.max_parallel}",
            )

        job = rec.new_id()
        now = time.time()
        state = {
            "schema": rec.SCHEMA,
            "job": job,
            "kind": kind,
            "label": label,
            "target": target,
            "args": args,
            "stage": "queued",
            "status": None,
            "progress": None,
            "note": None,
            "result": None,
            "error": None,
            "started_ts": now,
            "started_at": rec.stamp(now),
            "ended_ts": None,
            "ended_at": None,
            "elapsed_s": 0.0,
            "root": str(self.root),
            "work": str(self.work),
            "heartbeat_s": self.heartbeat_s,
        }
        record_path = self.paths.record(job)
        # The beat exists before the worker does, so the window between spawning and
        # the first real beat is a grace period rather than an instant failure.
        rec.write_beat(self.paths.beat(job), now)
        rec.write_record(record_path, state)

        pid = process.spawn_detached(
            [self.python, "-m", "polyweave.jobs.worker", str(record_path)],
            cwd=self.root,
            env=self._child_env(path, env),
            log_path=self.paths.log(job),
        )
        rec.write_atomic(self.paths.pid(job), f"{pid}\n")
        return self._view(state, pid=pid)

    def _child_env(
        self,
        path: list[str | Path] | None,
        env: dict[str, str] | None,
    ) -> dict[str, str]:
        """The worker's environment, with this package importable from wherever it is.

        Deriving the entry from the installed location rather than requiring an install
        is what lets the plugin run out of a checkout.
        """
        # Merged into this process's environment rather than replacing it: a worker
        # started with a bare environment cannot find its own interpreter's libraries.
        child = dict(os.environ)
        child.update(env or {})
        entries = [str(_PACKAGE_ROOT)]
        for p in path or []:
            entries.append(str(p if Path(p).is_absolute() else self.root / p))
        existing = child.get("PYTHONPATH")
        if existing:
            entries.append(existing)
        child["PYTHONPATH"] = os.pathsep.join(entries)
        return child

    # -- reading ----------------------------------------------------------------

    def poll(self, job: str) -> dict:
        """Where it got to — promoting a dead worker to a failure, never to a wait."""
        state = self._read(job)
        pid = rec.read_pid(self.paths.pid(job))
        if is_terminal(state["stage"]):
            return self._view(state, pid=pid)
        if not self._worker_gone(state, pid):
            return self._view(state, pid=pid)

        # It may have finished in the moment between reading the record and asking the
        # OS about the process, so the record gets the last word.
        state = self._read(job)
        if is_terminal(state["stage"]):
            return self._view(state, pid=pid)
        return self._view(self._reap(state, pid), pid=pid)

    def result(
        self,
        job: str,
        *,
        wait: bool = False,
        timeout: float | None = None,
        poll_every: float = 0.25,
    ) -> dict:
        """The outcome. Blocks only if asked to, and never past `timeout`."""
        view = self.poll(job)
        if not wait:
            if view["status"] is None:
                raise PolyweaveError(
                    "job.not-finished",
                    f"{job} is still {view['stage']}",
                    "poll it, or call result again with wait=True",
                )
            return view
        deadline = None if timeout is None else time.monotonic() + timeout
        while view["status"] is None:
            if deadline is not None and time.monotonic() >= deadline:
                raise PolyweaveError(
                    "job.timeout",
                    f"{job} was still {view['stage']} after {timeout:g}s",
                    f"poll {job} for its stage, or cancel it if it is not wanted",
                )
            time.sleep(poll_every)
            view = self.poll(job)
        return view

    def list(self) -> list[dict]:
        """Every job this project knows about, freshest state first read from disk."""
        out = []
        for job in self.paths.ids():
            try:
                out.append(self.poll(job))
            except PolyweaveError:  # pragma: no cover - a record removed mid-listing
                continue
        return out

    # -- ending -----------------------------------------------------------------

    def cancel(self, job: str) -> dict:
        """End the job and everything it started.

        Not advisory: a search that has found its answer stops paying for the renders it
        no longer needs. A job that finished first keeps the outcome it earned.
        """
        state = self._read(job)
        pid = rec.read_pid(self.paths.pid(job))
        if is_terminal(state["stage"]):
            return self._view(state, pid=pid)
        process.kill_tree(pid)
        process.wait_gone(pid)
        state = self._read(job)
        if is_terminal(state["stage"]):
            return self._view(state, pid=pid)
        return self._view(self._finish(state, "cancelled"), pid=pid)

    def sweep(self, *, retain_s: float = RETAIN_S) -> dict:
        """Collect what was abandoned: dead workers, their orphans, and old records."""
        reaped: list[str] = []
        removed: list[str] = []
        now = time.time()
        for job in self.paths.ids():
            state = rec.read_record(self.paths.record(job))
            if state is None:  # pragma: no cover - removed by a parallel sweep
                continue
            pid = rec.read_pid(self.paths.pid(job))
            if not is_terminal(state["stage"]):
                if self._worker_gone(state, pid):
                    # The worker is gone but its renderer may not be, and on POSIX the
                    # group id outlives the leader.
                    process.kill_tree(pid)
                    self._reap(state, pid)
                    reaped.append(job)
                continue
            ended = state.get("ended_ts") or state["started_ts"]
            if now - ended > retain_s:
                for p in self.paths.all_of(job):
                    # A reader holding one of these on Windows blocks the unlink; the
                    # next sweep gets it.
                    with contextlib.suppress(OSError):
                        p.unlink(missing_ok=True)
                if not self.paths.record(job).exists():
                    removed.append(job)
        return {"reaped": reaped, "removed": removed}

    # -- the state itself -------------------------------------------------------

    def _read(self, job: str) -> dict:
        state = rec.read_record(self.paths.record(job))
        if state is None:
            raise PolyweaveError(
                "job.unknown",
                f"no job {job!r} under {self.work}",
                "list the jobs, or start a new one",
            )
        if state.get("schema") != rec.SCHEMA:
            raise PolyweaveError(
                "job.schema",
                f"{job} was written by another version of this plugin",
                f"delete {self.paths.record(job)} and start the work again",
            )
        return state

    def _worker_gone(self, state: dict, pid: int | None) -> bool:
        """Whether nothing is working on this job any more.

        Two questions, because neither answers alone: a pid that no longer exists is
        conclusive, and a pid that does exist may be a stranger who inherited the
        number, which only a heartbeat that stopped moving can tell you.
        """
        if not process.alive(pid):
            return True
        beat = rec.read_beat(self.paths.beat(state["job"]))
        if beat is None:  # pragma: no cover - the creator always writes one
            return False
        return (time.time() - beat) > self.stale_after_s

    def _reap(self, state: dict, pid: int | None) -> dict:
        log = self.paths.log(state["job"])
        return self._finish(
            state,
            "failed",
            error={
                "code": "job.worker-gone",
                "message": (
                    f"the worker for {state['job']} is no longer running, and it left "
                    f"no result behind"
                ),
                "remedy": (
                    f"read {log} for what it printed, then start the work again"
                ),
                "detail": rec.tail(log) or f"pid {pid} is not running",
            },
        )

    def _finish(self, state: dict, status: str, **fields: Any) -> dict:
        now = time.time()
        state.update(fields)
        state["stage"] = status
        state["status"] = status
        state["ended_ts"] = now
        state["ended_at"] = rec.stamp(now)
        state["elapsed_s"] = round(now - state["started_ts"], 3)
        rec.write_record(self.paths.record(state["job"]), state)
        return state

    def _view(self, state: dict, *, pid: int | None) -> dict:
        """What a caller gets: the record, with the derived fields filled in.

        `elapsed_s` is computed rather than stored while a job runs, because the stored
        one is only as fresh as the last stage the worker reported.
        """
        elapsed = (
            state["elapsed_s"]
            if is_terminal(state["stage"])
            else round(time.time() - state["started_ts"], 3)
        )
        return {
            "job": state["job"],
            "kind": state["kind"],
            "label": state["label"],
            "target": state["target"],
            "args": state["args"],
            "stage": state["stage"],
            "status": state["status"],
            "progress": state["progress"],
            "note": state["note"],
            "result": state["result"],
            "error": state["error"],
            "pid": pid,
            "started_at": state["started_at"],
            "ended_at": state["ended_at"],
            "elapsed_s": elapsed,
            "log": str(self.paths.log(state["job"])),
        }
