"""What §1 of the tool surface promises, asserted against real worker processes.

These spawn actual interpreters. That is the point: a handle that only works inside one
process is not a handle that survives the session that made it.
"""

from __future__ import annotations

import json
import os
import time

import pytest

from conftest import wait_for
from polyweave.errors import PolyweaveError
from polyweave.jobs import KINDS, JobStore, stages_for

TARGET = "support.jobtargets"


def start(store, fn, target_path, **kw):
    kw.setdefault("kind", "bake")
    return store.start(f"{TARGET}:{fn}", path=target_path, **kw)


# -- the handle ----------------------------------------------------------------


def test_start_returns_a_handle_without_waiting(store, target_path):
    handle = start(store, "sleeper", target_path, args={"seconds": 30})
    assert handle["job"].startswith("j_")
    assert handle["stage"] == "queued"
    assert handle["status"] is None
    assert handle["pid"] > 0


def test_result_carries_what_the_target_returned(store, target_path):
    handle = start(store, "immediate", target_path, args={"value": 11})
    done = store.result(handle["job"], wait=True, timeout=30)
    assert done["status"] == "done"
    assert done["stage"] == "done"
    assert done["result"]["value"] == 11
    # The work really happened somewhere else.
    assert done["result"]["pid"] != os.getpid()
    assert done["elapsed_s"] >= 0


def test_the_state_lives_in_a_file_under_the_project(store, target_path):
    handle = start(store, "immediate", target_path)
    store.result(handle["job"], wait=True, timeout=30)
    record = store.work / "jobs" / f"{handle['job']}.json"
    assert record.is_file()
    assert store.work.parent == store.root  # nothing written outside the tree
    on_disk = json.loads(record.read_text(encoding="utf-8"))
    assert on_disk["status"] == "done"


def test_a_second_store_reads_a_job_it_did_not_start(store, target_path):
    """The handle outlives the session: a fresh store answers about the same job."""
    handle = start(store, "immediate", target_path)
    store.result(handle["job"], wait=True, timeout=30)
    later = JobStore(root=store.root)
    assert later.poll(handle["job"])["status"] == "done"


def test_result_without_wait_refuses_a_running_job(store, target_path):
    handle = start(store, "sleeper", target_path, args={"seconds": 30})
    with pytest.raises(PolyweaveError) as caught:
        store.result(handle["job"])
    assert caught.value.code == "job.not-finished"
    assert "wait=True" in caught.value.remedy


def test_result_times_out_without_ending_the_job(store, target_path):
    handle = start(store, "sleeper", target_path, args={"seconds": 30})
    with pytest.raises(PolyweaveError) as caught:
        store.result(handle["job"], wait=True, timeout=0.5)
    assert caught.value.code == "job.timeout"
    assert store.poll(handle["job"])["status"] is None


# -- progress ------------------------------------------------------------------


def test_poll_reports_the_stage_the_work_reached(store, target_path):
    handle = start(store, "staged", target_path, args={"hold": 5.0})
    job = handle["job"]
    view = wait_for(lambda: (v := store.poll(job))["stage"] == "rendering" and v)
    assert view["progress"] == 0.25
    assert view["note"] == "sample 1 of 4"
    assert view["elapsed_s"] > 0


def test_a_stage_outside_the_kind_is_refused(store):
    from polyweave.jobs.stages import check_stage

    with pytest.raises(PolyweaveError) as caught:
        check_stage("search", "downloading")
    assert caught.value.code == "job.unknown-stage"
    assert "rendering" in caught.value.remedy


def test_every_kind_ends_in_the_same_three_words():
    for kind in KINDS:
        assert stages_for(kind)[-3:] == ("done", "failed", "cancelled")


def test_an_unknown_kind_is_refused_before_anything_is_written(store, target_path):
    with pytest.raises(PolyweaveError) as caught:
        start(store, "immediate", target_path, kind="sculpt")
    assert caught.value.code == "job.unknown-kind"
    assert not (store.work / "jobs").exists()


# -- failure -------------------------------------------------------------------


def test_an_untyped_exception_becomes_a_typed_failure(store, target_path):
    handle = start(store, "raiser", target_path)
    done = store.result(handle["job"], wait=True, timeout=30)
    assert done["status"] == "failed"
    assert done["error"]["code"] == "job.target-failed"
    assert "the boolean left no faces" in done["error"]["message"]
    assert "Traceback" in done["error"]["detail"]
    assert "Traceback" not in done["error"]["message"]


def test_a_typed_failure_arrives_whole(store, target_path):
    handle = start(store, "typed_failure", target_path)
    done = store.result(handle["job"], wait=True, timeout=30)
    assert done["error"]["code"] == "post.mesh-empty"
    assert done["error"]["remedy"].startswith("bevel the operand")


def test_an_unknown_argument_is_refused_rather_than_dropped(store, target_path):
    handle = start(store, "takes_nothing", target_path, args={"sixe": 512})
    done = store.result(handle["job"], wait=True, timeout=30)
    assert done["status"] == "failed"
    assert done["error"]["code"] == "job.unknown-arg"
    assert "sixe" in done["error"]["message"]


def test_a_target_that_does_not_exist_names_the_door(store, target_path):
    handle = store.start(f"{TARGET}:nope", kind="bake", path=target_path)
    done = store.result(handle["job"], wait=True, timeout=30)
    assert done["error"]["code"] == "job.target-not-found"


def test_a_dead_worker_is_a_failure_not_a_hang(store, target_path):
    """§1: a poll that finds no live process and no result returns `job.worker-gone`."""
    handle = start(store, "sleeper", target_path, args={"seconds": 60})
    job = handle["job"]
    wait_for(lambda: store.poll(job)["stage"] == "rendering")

    from polyweave.jobs import process

    process.kill_tree(handle["pid"])
    process.wait_gone(handle["pid"])

    view = store.poll(job)
    assert view["status"] == "failed"
    assert view["error"]["code"] == "job.worker-gone"
    # And it stays failed, rather than being decided again on the next read.
    assert store.poll(job)["error"]["code"] == "job.worker-gone"


def test_a_stale_heartbeat_outvotes_a_living_pid(store, target_path):
    """A pid is reused; a heartbeat that stopped moving is what catches that."""
    handle = start(store, "sleeper", target_path, args={"seconds": 60})
    job = handle["job"]
    wait_for(lambda: store.poll(job)["stage"] == "rendering")

    beat = store.work / "jobs" / f"{job}.beat"
    beat.write_text(f"{time.time() - 120:.3f}\n", encoding="utf-8")

    view = store.poll(job)
    assert view["status"] == "failed"
    assert view["error"]["code"] == "job.worker-gone"


# -- cancel --------------------------------------------------------------------


def test_cancel_ends_the_process(store, target_path):
    handle = start(store, "sleeper", target_path, args={"seconds": 120})
    job = handle["job"]
    wait_for(lambda: store.poll(job)["stage"] == "rendering")

    view = store.cancel(job)
    assert view["status"] == "cancelled"

    from polyweave.jobs import process

    assert not process.alive(handle["pid"])
    assert store.poll(job)["status"] == "cancelled"


def test_cancel_leaves_a_finished_job_alone(store, target_path):
    handle = start(store, "immediate", target_path)
    store.result(handle["job"], wait=True, timeout=30)
    view = store.cancel(handle["job"])
    assert view["status"] == "done"


# -- the bound and the sweep ---------------------------------------------------


def test_concurrency_is_bounded_and_says_how_to_raise_it(tmp_path, target_path):
    store = JobStore(root=tmp_path, max_parallel=2, heartbeat_s=0.2)
    try:
        first = start(store, "sleeper", target_path, args={"seconds": 60})
        second = start(store, "sleeper", target_path, args={"seconds": 60})
        with pytest.raises(PolyweaveError) as caught:
            start(store, "sleeper", target_path, args={"seconds": 60})
        assert caught.value.code == "job.at-capacity"
        assert "max_parallel" in caught.value.remedy
        assert first["job"] in caught.value.remedy
    finally:
        for view in store.list():
            if view["status"] is None:
                store.cancel(view["job"])
    # And the slot comes back once one ends.
    assert store.poll(second["job"])["status"] == "cancelled"
    start(store, "immediate", target_path)


def test_parallel_handles_run_at_the_same_time(store, target_path):
    handles = [
        start(store, "staged", target_path, args={"hold": 1.0}) for _ in range(3)
    ]
    assert len({h["job"] for h in handles}) == 3
    started = time.monotonic()
    for handle in handles:
        view = store.result(handle["job"], wait=True, timeout=60)
        assert view["status"] == "done", view["error"]
    # Three one-second holds in less than their sum is the whole claim.
    assert time.monotonic() - started < 3.0


def test_sweep_reaps_an_abandoned_job(store, target_path):
    handle = start(store, "sleeper", target_path, args={"seconds": 60})
    job = handle["job"]
    wait_for(lambda: store.poll(job)["stage"] == "rendering")

    from polyweave.jobs import process

    process.kill_tree(handle["pid"])
    process.wait_gone(handle["pid"])

    swept = store.sweep()
    assert swept["reaped"] == [job]
    assert store.poll(job)["error"]["code"] == "job.worker-gone"


def test_sweep_collects_an_old_record(store, target_path):
    handle = start(store, "immediate", target_path)
    job = handle["job"]
    store.result(job, wait=True, timeout=30)

    assert store.sweep(retain_s=3600)["removed"] == []
    assert store.sweep(retain_s=-1)["removed"] == [job]
    assert not (store.work / "jobs" / f"{job}.json").exists()
    with pytest.raises(PolyweaveError) as caught:
        store.poll(job)
    assert caught.value.code == "job.unknown"
