"""What §1 of the tool surface promises, asserted against real worker processes.

These spawn actual interpreters. That is the point: a handle that only works inside one
process is not a handle that survives the session that made it.
"""

from __future__ import annotations

import json
import os
import threading
import time

import pytest

from conftest import wait_for
from polyweave.errors import PolyweaveError
from polyweave.jobs import KINDS, JobStore, stages_for
from polyweave.jobs import record as rec
from polyweave.jobs.record import holding

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


# -- one rule with two reaches (§PW39) -----------------------------------------


def test_a_registered_operation_is_held_to_its_declared_range_before_it_spawns(store):
    """The same value refused at once through one door used to spawn an interpreter,
    import the target and come back a failed job through the other."""
    with pytest.raises(PolyweaveError) as caught:
        store.start(
            "polyweave.render:bake",
            kind="bake",
            args={"out": "r.png", "elevation": 400.0},
        )
    assert caught.value.code == "op.out-of-range"
    assert store.list() == [], "and nothing was written, let alone spawned"


def test_a_missing_required_argument_is_refused_before_it_spawns(store):
    with pytest.raises(PolyweaveError) as caught:
        store.start("polyweave.render:bake", kind="bake", args={})
    assert caught.value.code == "op.missing-argument"


def test_an_unknown_argument_to_a_registered_operation_never_reaches_a_worker(store):
    with pytest.raises(PolyweaveError) as caught:
        store.start(
            "polyweave.render:bake", kind="bake", args={"out": "r.png", "sixe": 512}
        )
    assert caught.value.code == "op.unknown-argument"


def test_a_target_with_no_registration_is_still_the_workers_to_check(
    store, target_path
):
    """A project's own generator named as a file path is a legitimate target, and the
    signature check in the child is the only contract it has."""
    from polyweave import describe

    assert describe.for_target(f"{TARGET}:takes_nothing") is None
    handle = start(store, "takes_nothing", target_path, args={"sixe": 512})
    done = store.result(handle["job"], wait=True, timeout=30)
    assert done["error"]["code"] == "job.unknown-arg", "refused, just later and dearer"


def test_the_registry_answers_by_target_without_the_caller_importing_anything(store):
    """Registration is a side effect of an import, so asking whether something is an
    operation used to be asking whether its module had been imported yet."""
    from polyweave import describe

    assert describe.for_target("polyweave.render:bake") == "render.bake"
    assert describe.for_target("nothing.at.all:ever") is None


def test_a_value_inside_the_declared_range_starts_the_job(store):
    """The check refuses what the declaration refuses, and nothing more."""
    handle = store.start(
        "polyweave.render:bake",
        kind="bake",
        args={"out": "r.png", "rung": "sphere", "elevation": 20.0},
    )
    assert handle["stage"] == "queued"
    store.cancel(handle["job"])


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


def test_two_starts_at_once_cannot_both_take_the_last_slot(
    tmp_path, target_path, monkeypatch
):
    """§PW139: the count and the record are held under one lock. The window between
    them is widened here so the race, if it were there, would be lost every run."""
    store = JobStore(root=tmp_path, max_parallel=1, heartbeat_s=0.2)
    counted = JobStore.list

    def slow_count(self):
        views = counted(self)
        time.sleep(0.3)
        return views

    monkeypatch.setattr(JobStore, "list", slow_count)
    outcomes: list[str] = []

    def one():
        try:
            start(store, "sleeper", target_path, args={"seconds": 60})
            outcomes.append("started")
        except PolyweaveError as refused:
            outcomes.append(refused.code)

    threads = [threading.Thread(target=one) for _ in range(2)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        assert sorted(outcomes) == ["job.at-capacity", "started"]
    finally:
        monkeypatch.setattr(JobStore, "list", counted)
        for view in store.list():
            if view["status"] is None:
                store.cancel(view["job"])
    assert not store.paths.starting().exists()


def test_a_lock_its_holder_abandoned_is_taken_after_the_bound(tmp_path):
    lock = tmp_path / "jobs" / "start.lock"
    lock.parent.mkdir()
    lock.write_text("somebody who died", encoding="utf-8")
    old = time.time() - 60
    os.utime(lock, (old, old))
    with holding(lock, stale_s=10):
        assert lock.read_text(encoding="utf-8") != "somebody who died"
    assert not lock.exists()


def test_only_the_holder_releases_the_lock(tmp_path):
    lock = tmp_path / "start.lock"
    with holding(lock):
        lock.write_text("a reaper's own token", encoding="utf-8")
    assert lock.read_text(encoding="utf-8") == "a reaper's own token"


def test_a_job_recorded_and_not_yet_spawned_is_not_gone(store):
    """Between a start's record and its pid another start may count it: it is still
    starting, not a worker that died."""
    job = "j_00000000"
    store.paths.jobs.mkdir(parents=True, exist_ok=True)
    rec.write_beat(store.paths.beat(job))
    assert store._worker_gone({"job": job}, None) is False
    rec.write_beat(store.paths.beat(job), time.time() - 3600)
    assert store._worker_gone({"job": job}, None) is True


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


# -- a renderer whose parent is gone (§PW37) -----------------------------------


def test_a_worker_writes_down_what_it_spawned_before_waiting_on_it(
    store, target_path, tmp_path
):
    """The trail has to exist before the wait, or a worker killed a moment later
    takes the only handle to its child with it."""
    marker = tmp_path / "child.pid"
    handle = start(
        store,
        "spawner",
        target_path,
        args={"seconds": 120},
        env={"POLYWEAVE_TEST_MARKER": str(marker)},
    )
    wait_for(lambda: store.poll(handle["job"])["stage"] == "rendering")

    from polyweave.jobs import record as rec

    kids = rec.read_kids(store.work / "jobs" / f"{handle['job']}.kids")
    assert [pid for pid, _ in kids] == [int(marker.read_text())]
    assert kids[0][1] is not None, "and with a start time, or it is only a number"


def test_a_sweep_ends_the_renderer_a_dead_worker_left_running(
    store, target_path, tmp_path
):
    """The failure §PW37 names: on Windows nothing connects a dead parent to its
    children, so the render goes on spending a core nobody is watching."""
    marker = tmp_path / "child.pid"
    handle = start(
        store,
        "spawner",
        target_path,
        args={"seconds": 120},
        env={"POLYWEAVE_TEST_MARKER": str(marker)},
    )
    job = handle["job"]
    wait_for(lambda: store.poll(job)["stage"] == "rendering")
    child = int(marker.read_text())

    from polyweave.jobs import process

    # The worker alone, not its tree: a tree walk is exactly what a sweep does not have,
    # and on POSIX taking the group would hide the bug by killing the child too.
    process.end(handle["pid"])
    process.wait_gone(handle["pid"])
    assert process.alive(child), "the orphan outlives its parent, which is the bug"

    swept = store.sweep()
    assert swept["reaped"] == [job]
    assert swept["orphans"] == 1
    assert process.wait_gone(child, 5.0), "and the sweep is what ends it"


def test_a_recorded_pid_that_belongs_to_somebody_else_now_is_left_alone(store):
    """Killing a stranger is a worse failure than leaking a renderer, and a sweep
    that might do it is one nobody will run."""
    from polyweave.jobs import process
    from polyweave.jobs import record as rec

    assert not process.end(os.getpid(), since=1.0), "a start time nothing matches"
    assert process.alive(os.getpid())

    # And a pid the OS would not date is skipped rather than guessed at.
    kids = store.work / "jobs" / "j_none.kids"
    kids.parent.mkdir(parents=True, exist_ok=True)
    rec.add_kid(kids, os.getpid(), None)
    assert rec.read_kids(kids) == [(os.getpid(), None)]


def test_a_process_can_be_told_apart_from_a_stranger_that_reused_its_number():
    """The reuse problem the heartbeat solves for a worker, for its children."""
    from polyweave.jobs import process

    mine = process.started_at(os.getpid())
    assert mine is not None, "this platform must be able to date a process"
    assert process.started_at(os.getpid()) == mine, "and date it the same way twice"


def test_a_torn_trail_does_not_stop_the_rest_being_collected(tmp_path):
    """A sweep runs after a crash, which is when a file is most likely to be torn."""
    from polyweave.jobs import record as rec

    trail = tmp_path / "j_x.kids"
    trail.write_text("123 4.0\nnot-a-pid\n456 -\n", encoding="utf-8")
    assert rec.read_kids(trail) == [(123, 4.0), (456, None)]


def test_nothing_is_recorded_outside_a_worker(tmp_path):
    """`watch` is called wherever something spawns, job or no job."""
    from polyweave.jobs import children

    assert children.watched() is None
    children.watch(os.getpid())  # no job, so nowhere to write and nothing raised


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
