"""Renders are content-addressed, so the same picture is paid for once.

§PW14's cost is a search revisiting neighbourhoods. What matters is that a hit is safe
to return — the key holds everything that can change the output and nothing that cannot
— and that a hit says it was one.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image as PILImage

from polyweave import cache, provenance
from polyweave.errors import PolyweaveError


def artefact(tmp_path, name="shot.png", *, colour=(200, 40, 40)):
    rgba = np.zeros((8, 8, 4), dtype=np.uint8)
    rgba[:, :, :3] = colour
    rgba[:, :, 3] = 255
    path = tmp_path / name
    PILImage.fromarray(rgba, "RGBA").save(path)
    return path


def a_record(tmp_path, name="shot.png", **over):
    artefact(tmp_path, name)
    fields = {
        "engine": {"name": "cycles", "version": "4.2.1", "bindings": "bpy 4.2.0"},
        "rung": "preview",
        "seed": 11,
        "samples": 64,
        "params": {"key": 400.0},
        "root": tmp_path,
    }
    fields.update(over)
    return provenance.build("render", name, **fields)


# -- the key is knowable before the render ---------------------------------------------


def test_the_planned_key_is_the_key_the_render_gets(tmp_path):
    """Which is the whole of what makes a lookup cheaper than a path trace."""
    common = {
        "engine": {"name": "cycles", "version": "4.2.1", "bindings": "bpy 4.2.0"},
        "rung": "preview",
        "seed": 11,
        "samples": 64,
        "params": {"key": 400.0},
    }
    before = provenance.cache_key(provenance.planned("render", **common))
    after = provenance.cache_key(a_record(tmp_path, **common))
    assert before == after


def test_the_colour_pipeline_is_in_the_key(tmp_path):
    """Two installations that disagree about it must not share an entry."""

    def with_transform(name):
        return provenance.planned(
            "render", engine={"name": "cycles", "view_transform": name}
        )

    one, two = with_transform("Standard"), with_transform("AgX")
    assert provenance.cache_key(one) != provenance.cache_key(two)


# -- keeping and finding ---------------------------------------------------------------


def test_what_goes_in_comes_back_out(tmp_path):
    work = tmp_path / ".polyweave"
    record = a_record(tmp_path)
    key = provenance.cache_key(record)
    cache.put(key, tmp_path / "shot.png", record, work=work)

    hit = cache.look(key, work=work)
    assert hit is not None
    assert hit["key"] == key
    assert hit["record"]["seed"] == 11
    assert hit["bytes"] > 0


def test_a_key_nothing_holds_is_a_miss(tmp_path):
    assert cache.look("f" * 64, work=tmp_path / ".polyweave") is None


def test_a_hit_is_copied_out_where_it_was_wanted(tmp_path):
    work = tmp_path / ".polyweave"
    record = a_record(tmp_path)
    key = provenance.cache_key(record)
    cache.put(key, tmp_path / "shot.png", record, work=work)

    out = tmp_path / "somewhere" / "else.png"
    cache.take(cache.look(key, work=work), out)
    assert out.is_file()
    assert out.read_bytes() == (tmp_path / "shot.png").read_bytes()


def test_the_store_is_laid_out_where_the_spec_says(tmp_path):
    work = tmp_path / ".polyweave"
    key = "abcdef" + "0" * 58
    cache.put(key, artefact(tmp_path), {"kind": "render"}, work=work)
    assert (work / "cache" / "ab" / f"{key}.png").is_file()
    assert (work / "cache" / "ab" / f"{key}.json").is_file()


def test_a_key_that_is_not_one_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        cache.look("ab", work=tmp_path)
    assert caught.value.code == "prov.bad-key"


def test_caching_something_that_is_not_there_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        cache.put("a" * 64, tmp_path / "never.png", {}, work=tmp_path / ".polyweave")
    assert caught.value.code == "prov.missing-artefact"


# -- half an entry is no entry ---------------------------------------------------------


def test_a_record_whose_artefact_is_gone_is_dropped_rather_than_repaired(tmp_path):
    work = tmp_path / ".polyweave"
    record = a_record(tmp_path)
    key = provenance.cache_key(record)
    cache.put(key, tmp_path / "shot.png", record, work=work)

    held, beside = cache.slot(key, work)
    held.unlink()

    assert cache.look(key, work=work) is None
    assert not beside.exists(), "the orphaned record went with it"


def test_a_record_that_is_not_readable_is_dropped(tmp_path):
    work = tmp_path / ".polyweave"
    key = "b" * 64
    cache.put(key, artefact(tmp_path), {"kind": "render"}, work=work)
    cache.slot(key, work)[1].write_text("{broken", encoding="utf-8")
    assert cache.look(key, work=work) is None


# -- eviction --------------------------------------------------------------------------


def keep(tmp_path, work, key, colour):
    path = artefact(tmp_path, f"{key[:4]}.png", colour=colour)
    return cache.put(key, path, {"kind": "render"}, work=work)


def test_the_least_recently_used_goes_first(tmp_path):
    import time

    work = tmp_path / ".polyweave"
    first, second = "1" * 64, "2" * 64
    keep(tmp_path, work, first, (10, 10, 10))
    time.sleep(0.01)
    keep(tmp_path, work, second, (20, 20, 20))
    cache.look(first, work=work)  # touching the older one makes it the newer one

    held = cache.stats(work)["bytes"]
    dropped = cache.evict(work=work, max_bytes=held - 1)
    assert dropped["dropped"] == [second]
    assert cache.look(first, work=work) is not None


def test_nothing_is_dropped_while_it_fits(tmp_path):
    work = tmp_path / ".polyweave"
    keep(tmp_path, work, "3" * 64, (30, 30, 30))
    assert cache.evict(work=work, max_bytes=10_000_000)["dropped"] == []


def test_what_the_store_holds_is_answerable(tmp_path):
    work = tmp_path / ".polyweave"
    assert cache.stats(work) == {"entries": 0, "bytes": 0, "where": str(work / "cache")}
    keep(tmp_path, work, "4" * 64, (40, 40, 40))
    found = cache.stats(work)
    assert found["entries"] == 1
    assert found["bytes"] > 0


def test_an_entry_can_be_forgotten(tmp_path):
    work = tmp_path / ".polyweave"
    key = "5" * 64
    keep(tmp_path, work, key, (50, 50, 50))
    assert cache.forget(key, work=work) is True
    assert cache.look(key, work=work) is None
    assert cache.forget(key, work=work) is False


# -- through a real render -------------------------------------------------------------


def test_a_second_identical_render_is_a_hit_and_says_so(tmp_path):
    """A caller timing a sweep needs to know what it actually measured."""
    pytest.importorskip("bpy", reason="Blender is not importable in this interpreter")
    from polyweave import config as C
    from polyweave import render

    (tmp_path / C.FILENAME).write_text(
        "[render]\npreview_size = 32\nfinal_size = 32\n"
        "samples = { sphere = 4, preview = 4, final = 4 }\nseed = 11\n",
        encoding="utf-8",
    )

    class Quiet:
        def stage(self, *a, **k):
            pass

        def progress(self, *a, **k):
            pass

        def note(self, *a, **k):
            pass

    at = {"rung": "sphere", "root": tmp_path, "inline": False}
    first = render.bake(Quiet(), out="a.png", **at)
    second = render.bake(Quiet(), out="b.png", **at)

    assert first["cached"] is False
    assert second["cached"] is True
    assert second["cache_key"] == first["cache_key"]
    assert (tmp_path / "b.png").read_bytes() == (tmp_path / "a.png").read_bytes()
    assert second["elapsed_s"] < first["elapsed_s"]


def test_a_preview_rung_is_cached_too(tmp_path):
    """Those are the renders a search asks for thousands of times."""
    pytest.importorskip("bpy", reason="Blender is not importable in this interpreter")
    from polyweave import config as C
    from polyweave import render

    (tmp_path / C.FILENAME).write_text(
        "[render]\npreview_size = 32\nfinal_size = 32\n"
        "samples = { sphere = 4, preview = 4, final = 4 }\nseed = 11\n",
        encoding="utf-8",
    )

    class Quiet:
        def stage(self, *a, **k):
            pass

        def progress(self, *a, **k):
            pass

        def note(self, *a, **k):
            pass

    render.bake(Quiet(), out="s.png", rung="sphere", root=tmp_path, inline=False)
    held = cache.stats(tmp_path / ".polyweave")
    assert held["entries"] == 1


def test_a_caller_may_refuse_the_cache(tmp_path):
    pytest.importorskip("bpy", reason="Blender is not importable in this interpreter")
    from polyweave import config as C
    from polyweave import render

    (tmp_path / C.FILENAME).write_text(
        "[render]\npreview_size = 32\nfinal_size = 32\n"
        "samples = { sphere = 4, preview = 4, final = 4 }\nseed = 11\n",
        encoding="utf-8",
    )

    class Quiet:
        def stage(self, *a, **k):
            pass

        def progress(self, *a, **k):
            pass

        def note(self, *a, **k):
            pass

    render.bake(Quiet(), out="a.png", rung="sphere", root=tmp_path, inline=False)
    again = render.bake(
        Quiet(), out="b.png", rung="sphere", root=tmp_path, inline=False, cached=False
    )
    assert again["cached"] is False


# -- a hit is the picture, and says which of its bars have moved (§PW51) ---------------


class _Quiet:
    def stage(self, *a, **k):
        pass

    def progress(self, *a, **k):
        pass

    def note(self, *a, **k):
        pass


def _project(tmp_path, tolerance=""):
    from polyweave import config as C

    (tmp_path / C.FILENAME).write_text(
        "[render]\npreview_size = 32\nfinal_size = 32\n"
        "samples = { sphere = 4, preview = 4, final = 4 }\nseed = 11\n" + tolerance,
        encoding="utf-8",
    )


def test_a_render_records_the_bars_its_measurements_were_taken_against(tmp_path):
    pytest.importorskip("bpy", reason="Blender is not importable in this interpreter")
    from polyweave import provenance, render

    _project(tmp_path)
    render.bake(_Quiet(), out="a.png", rung="sphere", root=tmp_path, inline=False)
    written = provenance.read("a.png", root=tmp_path)
    assert written["tolerances"]["alpha_floor"] == pytest.approx(0.02)
    assert provenance.remeasure(written, written["tolerances"]) == []


def test_a_hit_taken_under_the_same_bars_has_nothing_stale(tmp_path):
    pytest.importorskip("bpy", reason="Blender is not importable in this interpreter")
    from polyweave import render

    _project(tmp_path)
    at = {"rung": "sphere", "root": tmp_path, "inline": False}
    render.bake(_Quiet(), out="a.png", **at)
    second = render.bake(_Quiet(), out="b.png", **at)
    assert second["cached"] is True
    assert second["stale"] == []


def test_a_hit_whose_floor_moved_is_still_the_picture_and_names_the_bar(tmp_path):
    """A tolerance is read after the pixels exist, so the render is not paid again."""
    pytest.importorskip("bpy", reason="Blender is not importable in this interpreter")
    from polyweave import render

    _project(tmp_path)
    at = {"rung": "sphere", "root": tmp_path, "inline": False}
    first = render.bake(_Quiet(), out="a.png", **at)

    _project(tmp_path, tolerance="\n[tolerance]\nalpha_floor = 0.4\n")
    second = render.bake(_Quiet(), out="b.png", **at)

    assert second["cached"] is True
    assert second["cache_key"] == first["cache_key"]
    assert (tmp_path / "b.png").read_bytes() == (tmp_path / "a.png").read_bytes()
    assert second["stale"] == ["alpha_floor"]
