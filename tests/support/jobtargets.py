"""Targets the job tests run in a real worker process.

These are imported by the worker, not by the test, so they may not import anything from
the test session. `tests` is on the worker's path because `test_jobs.py` passes it.
"""

from __future__ import annotations

import os
import time

from polyweave.errors import PolyweaveError


def immediate(report, value=7):
    """Finish before the first heartbeat, to test the fast path."""
    return {"value": value, "pid": os.getpid()}


def staged(report, hold=0.0):
    """Walk a bake's stages, leaving time to be polled in the middle of one."""
    report.stage("building", note="opening the scene")
    report.stage("rendering", progress=0.25, note="sample 1 of 4")
    if hold:
        time.sleep(hold)
    report.progress(0.75, note="sample 3 of 4")
    return "rendered"


def sleeper(report, seconds=30.0):
    """Stay alive until something ends it, for cancel and worker-gone."""
    report.stage("rendering")
    marker = os.environ.get("POLYWEAVE_TEST_MARKER")
    if marker:
        with open(marker, "w", encoding="utf-8") as fh:
            fh.write(str(os.getpid()))
    time.sleep(seconds)
    return "woke up"


def spawner(report, seconds=120.0):
    """Start a real child and wait on it, the way an engine capture does.

    §PW37 is about what happens to this child when the worker above it dies, so the
    child has to be a real process: the whole question is what the operating system does
    with it once its parent is gone, and a stand-in would answer a different question.
    """
    import subprocess
    import sys

    from polyweave.jobs import children

    child = subprocess.Popen(  # noqa: S603 - a sleep, with no shell and no input
        [sys.executable, "-c", f"import time; time.sleep({seconds})"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    children.watch(child.pid)
    report.stage("rendering")
    marker = os.environ.get("POLYWEAVE_TEST_MARKER")
    if marker:
        with open(marker, "w", encoding="utf-8") as fh:
            fh.write(str(child.pid))
    child.wait()
    return "the child finished"


def raiser(report):
    """Fail the way most code fails: an exception nobody typed."""
    raise ValueError("the boolean left no faces")


def typed_failure(report):
    """Fail the way this plugin means to: a code, a sentence and a door."""
    raise PolyweaveError(
        "post.mesh-empty",
        "the boolean returned a mesh with no faces",
        "bevel the operand after the boolean rather than before it",
    )


def takes_nothing(report):
    return "ok"
