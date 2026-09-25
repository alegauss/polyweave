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

from .. import describe
from ..errors import PolyweaveError
from . import children, process
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

    @classmethod
    def for_project(cls, root: str | Path = ".", **over: Any) -> JobStore:
        """A store whose work directory and parallelism come from `polyweave.toml`.

        Read here rather than at startup, so correcting the file does not need a session
        restart — which is the friction §PW5 exists to remove.
        """
        from ..config import load

        config = load(root)
        return cls(
            config.root,
            work=config.path("paths.work"),
            max_parallel=int(
                config.get("render.max_parallel", over.pop("max_parallel", None))
            ),
            **over,
        )

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
        # One rule with two reaches, not two rules (§PW39). A registered operation is
        # held to the same contract here as when it is called directly: a size of 8192
        # against a range of 16 to 4096 was refused at once through one door and,
        # through this one, spawned an interpreter, imported the target and came back a
        # failed job. An unregistered target has no declaration, so the worker's own
        # signature check stays the contract for those.
        operation = describe.for_target(target)
        if operation is not None:
            describe.validate(operation, args)
        # Held from the count to the record (§PW139): two starts that both counted three
        # of four would each start a fourth. The spawn comes after the release, because
        # the record already counts.
        with rec.holding(self.paths.starting()):
            state = self._recorded(target, kind=kind, args=args, label=label)
        job = state["job"]
        record_path = self.paths.record(job)
        pid = process.spawn_detached(
            [self.python, "-m", "polyweave.jobs.worker", str(record_path)],
            cwd=self.root,
            env=self._child_env(path, env),
            log_path=self.paths.log(job),
        )
        rec.write_atomic(self.paths.pid(job), f"{pid}\n")
        return self._view(state, pid=pid)

    def _recorded(
        self, target: str, *, kind: str, args: dict, label: str | None
    ) -> dict:
        """Count what is running, refuse at the bound, write the new job's record."""
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
        return state

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
        # The tree walk above should have taken them, and on Windows it takes them only
        # while the worker is still alive to be walked from. This is the same belt the
        # sweep wears, worn here because a cancel that leaves a renderer running is the
        # failure §PW37 names and the trail is already written (§PW37).
        self._end_orphans(job)
        state = self._read(job)
        if is_terminal(state["stage"]):
            return self._view(state, pid=pid)
        return self._view(self._finish(state, "cancelled"), pid=pid)

    def sweep(self, *, retain_s: float = RETAIN_S) -> dict:
        """Collect what was abandoned: dead workers, their orphans, and old records."""
        reaped: list[str] = []
        removed: list[str] = []
        orphans = 0
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
                    orphans += self._end_orphans(job)
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
        return {"reaped": reaped, "removed": removed, "orphans": orphans}

    def _end_orphans(self, job: str) -> int:
        """End what a dead worker left running, by pid rather than by tree.

        §PW37: `cancel` walks the tree from a living worker, and by the time a sweep
        finds a job abandoned there is no living worker to walk from. On Windows nothing
        at all connects a dead parent to its children. So the worker wrote each pid down
        before waiting on it, and this ends those directly — only where the recorded
        start time still matches, because ending a stranger who inherited the number is
        a worse failure than leaking a renderer.
        """
        ended = 0
        for pid, since in children.ended(self.paths.kids(job)):
            if since is None:
                # The OS would not say when it started, so this cannot be told apart
                # from a stranger. Left alone and reported by `list`, not killed.
                continue
            if process.end(pid, since=since):
                ended += 1
        return ended

    # -- the state itself -------------------------------------------------------

    def _read(self, job: str) -> dict:
        state = rec.read_record(self.paths.record(job))
        if state is None:
            raise PolyweaveError(
                "job.unknown",
                f"no job {job!r} under {self.work}",
                "list the jobs, or start a new one",
                given=job,
                allowed=self.paths.ids(),
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
        beat = rec.read_beat(self.paths.beat(state["job"]))
        if pid is None:
            # Recorded and not yet spawned: another start is between its record and its
            # pid (§PW139). The beat written at birth is the grace; a creator that died
            # there is gone once it goes stale.
            return beat is None or (time.time() - beat) > self.stale_after_s
        if not process.alive(pid):
            return True
        if beat is None:  # pragma: no cover - the creator always writes one
            return False
        return (time.time() - beat) > self.stale_after_s

    def _reap(self, state: dict, pid: int | None) -> dict:
        log = self.paths.log(state["job"])
        gone = PolyweaveError(
            "job.worker-gone",
            f"the worker for {state['job']} is no longer running, and it left no "
            f"result behind",
            f"read {log} for what it printed, then start the work again",
            detail=rec.tail(log) or f"pid {pid} is not running",
        )
        return self._finish(state, "failed", error=gone.as_dict())

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
