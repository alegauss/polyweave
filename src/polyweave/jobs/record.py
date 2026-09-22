"""Where a job's state lives, and how it is written without tearing.

`docs/specs/tool-surface.md` §1: state lives in a file so a handle survives the session
that made it. Four files carry one job, and each has exactly one writer:

    <job>.json   the record         — the worker, once running; the creator at birth
    <job>.pid    the OS process id  — the creator, before `start` returns
    <job>.beat   a heartbeat        — the worker's heartbeat thread
    <job>.log    stdout and stderr  — the worker's own streams

The pid and the heartbeat are separate files rather than fields so that the creator and
the worker never write the same file: a merge with two writers loses one of them, and
the loss would be the pid a `cancel` needs.

The atomic write and the retrying read live in `polyweave.files`, because the cache
needs the same two and one home for them beats two copies.
"""

from __future__ import annotations

import json
import secrets
import time
from datetime import UTC, datetime
from pathlib import Path

from ..files import read_text_retrying, write_atomic

#: Bumped when the record's fields change meaning. A record from a future schema is
#: refused rather than misread.
SCHEMA = 1


def new_id() -> str:
    """A handle, in the `j_7f3a` shape §1 prints."""
    return "j_" + secrets.token_hex(4)


def stamp(ts: float) -> str:
    """An ISO-8601 instant in UTC, which is the only form that appears in a record."""
    return datetime.fromtimestamp(ts, tz=UTC).isoformat().replace("+00:00", "Z")


class JobPaths:
    """The four files of one job, under `<work>/jobs/`."""

    def __init__(self, work: Path) -> None:
        self.work = Path(work)
        self.jobs = self.work / "jobs"

    def record(self, job: str) -> Path:
        return self.jobs / f"{job}.json"

    def pid(self, job: str) -> Path:
        return self.jobs / f"{job}.pid"

    def beat(self, job: str) -> Path:
        return self.jobs / f"{job}.beat"

    def log(self, job: str) -> Path:
        return self.jobs / f"{job}.log"

    def all_of(self, job: str) -> list[Path]:
        return [self.record(job), self.pid(job), self.beat(job), self.log(job)]

    def ids(self) -> list[str]:
        if not self.jobs.is_dir():
            return []
        return sorted(p.stem for p in self.jobs.glob("j_*.json"))


def write_record(path: Path, record: dict) -> None:
    write_atomic(path, json.dumps(record, indent=2, sort_keys=True) + "\n")


def read_record(path: Path) -> dict | None:
    text = read_text_retrying(path)
    if text is None:
        return None
    return json.loads(text)


def write_beat(path: Path, ts: float | None = None) -> None:
    write_atomic(path, f"{ts if ts is not None else time.time():.3f}\n")


def read_beat(path: Path) -> float | None:
    text = read_text_retrying(path)
    if text is None:
        return None
    try:
        return float(text.strip())
    except ValueError:
        return None


def read_pid(path: Path) -> int | None:
    text = read_text_retrying(path)
    if text is None:
        return None
    try:
        return int(text.strip())
    except ValueError:
        return None


def tail(path: Path, limit: int = 2000) -> str:
    """The last `limit` characters of a log, for an error's `detail`."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    text = text.strip()
    return text if len(text) <= limit else "…" + text[-limit:]
