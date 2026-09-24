"""A run recorded rather than reported (§PW115)."""

from __future__ import annotations

import pytest

from polyweave import config as C
from polyweave import loop


def test_a_bake_counts_itself_into_the_open_run_and_a_hit_is_not_a_render(tmp_path):
    run = loop.start("star", "after", root=tmp_path)
    with loop.recording(run):
        loop.bake_seen({"cached": False, "elapsed_s": 11.4})
        loop.bake_seen({"cached": True, "elapsed_s": 0.004})
    assert run["renders"] == 1
    assert run["cache_hits"] == 1
    assert run["render_seconds"] == pytest.approx(11.404)


def test_no_run_open_counts_nothing(tmp_path):
    run = loop.start("star", "after", root=tmp_path)
    loop.bake_seen({"cached": False})
    assert run["renders"] == 0


def test_the_run_is_closed_when_the_block_ends(tmp_path):
    run = loop.start("star", "after", root=tmp_path)
    with loop.recording(run):
        pass
    loop.bake_seen({"cached": False})
    assert run["renders"] == 0


def test_the_ledger_shows_hits_beside_renders(tmp_path):
    before = loop.start("star", "before", root=tmp_path)
    loop.spent(before, seconds=3.0, renders=4)
    loop.judged(before, tool_passed=True, person_accepted=True)
    loop.finish(before, root=tmp_path)
    after = loop.start("star", "after", root=tmp_path)
    with loop.recording(after):
        for cached in (False, False, True, True):
            loop.bake_seen({"cached": cached, "elapsed_s": 1.0})
    loop.judged(after, tool_passed=True, person_accepted=True)
    loop.finish(after, root=tmp_path)
    found = loop.compare("star", root=tmp_path)
    assert found["after"]["renders"] == 2
    assert found["after"]["cache_hits"] == 2


def test_a_real_bake_and_its_repeat_are_a_render_and_a_hit(tmp_path):
    pytest.importorskip("bpy", reason="Blender is not importable in this interpreter")
    from polyweave import render

    (tmp_path / C.FILENAME).write_text(
        "[render]\npreview_size = 32\n"
        "samples = { sphere = 4, preview = 4, final = 8 }\n",
        encoding="utf-8",
    )

    class Quiet:
        def stage(self, stage, *, progress=None, note=None):
            return None

    run = loop.start("ball", "after", root=tmp_path)
    with loop.recording(run):
        for name in ("a.png", "b.png"):
            render.bake(Quiet(), out=name, rung="sphere", inline=False, root=tmp_path)
    assert (run["renders"], run["cache_hits"]) == (1, 1)
