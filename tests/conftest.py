from __future__ import annotations

import time
from pathlib import Path

import pytest

from polyweave.jobs import JobStore

TESTS = Path(__file__).resolve().parent


@pytest.fixture
def store(tmp_path):
    """A job store on a throwaway project tree, with every job killed afterwards."""
    made = JobStore(root=tmp_path, heartbeat_s=0.2, stale_after_s=3.0)
    yield made
    for view in made.list():
        if view["status"] is None:
            made.cancel(view["job"])


@pytest.fixture
def target_path():
    """The worker's extra import path, so it can reach `support.jobtargets`."""
    return [TESTS]


def wait_for(predicate, timeout=20.0, every=0.05):
    """Poll until `predicate` holds, and fail loudly rather than hanging forever."""
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = predicate()
        if last:
            return last
        time.sleep(every)
    raise AssertionError(f"condition never held within {timeout}s (last: {last!r})")
