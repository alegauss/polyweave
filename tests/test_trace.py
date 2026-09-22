"""A search that shows its work.

§PW15's failure is specific: a spec satisfiable by a render a person would reject, where
every predicate passes and the picture is still wrong. With only a set of numbers coming
back, that is indistinguishable from success.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image as PILImage

from polyweave import accept, cache, search, trace


def project(tmp_path, text=""):
    (tmp_path / "polyweave.toml").write_text(text, encoding="utf-8")
    return tmp_path


def a_spec():
    return accept.parse(
        {
            "asset": "mascot",
            "predicate": [
                {"id": "bright", "measure": "alpha_coverage", "min": 0.5},
                {"id": "wide", "measure": "alpha_coverage", "min": 0.9},
            ],
            "search": {"light": {"min": 0.0, "max": 4.0}},
        }
    )


def found_from(tmp_path, *, with_pictures=True):
    """A search result, each sample's picture in the cache as a real one would be."""
    work = tmp_path / ".polyweave"

    def evaluate(values):
        score = max(0.0, 1.0 - abs(values["light"] - 3.0) / 4.0)
        key = f"{int(values['light'] * 1000):064d}"
        if with_pictures:
            shade = min(255, int(40 + score * 200))
            rgba = np.zeros((8, 8, 4), dtype=np.uint8)
            rgba[:, :, :3] = shade
            rgba[:, :, 3] = 255
            path = tmp_path / f"{key[-6:]}.png"
            PILImage.fromarray(rgba, "RGBA").save(path)
            cache.put(key, path, {"kind": "render"}, work=work)
        return {
            "score": score,
            "passed": False,
            "predicates": [
                {"id": "bright", "value": score, "margin": score, "passed": False},
                {"id": "wide", "value": score, "margin": score / 2, "passed": False},
            ],
            "failed": ["wide"],
            "render": {"cache_key": key, "cached": False, "artefact": "x.png"},
        }

    return search.search(a_spec(), evaluate, budget=9, points=3)


# -- the trace holds what it rejected --------------------------------------------------


def test_every_sample_is_in_the_trace(tmp_path):
    found = found_from(project(tmp_path))
    record = trace.as_record(found, a_spec(), root=tmp_path)
    assert len(record["samples"]) == found["spent"]


def test_every_sample_carries_its_score_against_every_predicate(tmp_path):
    """Which is what makes a spec arguable rather than only a verdict."""
    record = trace.as_record(found_from(project(tmp_path)), a_spec(), root=tmp_path)
    one = record["samples"][0]
    assert [p["id"] for p in one["predicates"]] == ["bright", "wide"]
    assert all("margin" in p for p in one["predicates"])


def test_the_trace_records_what_would_reproduce_it(tmp_path):
    """The seed and the search's own configuration, beside the samples it scored."""
    where = project(tmp_path, "[render]\nseed = 4242\n")
    record = trace.as_record(found_from(where), a_spec(), root=where)
    assert record["seed"] == 4242
    assert record["budget"] == 9
    assert record["searched"] == ["light"]
    assert record["ranges"] == {"light": {"min": 0.0, "max": 4.0}}
    assert record["stopped"]


def test_the_winner_is_in_the_trace_with_what_it_failed(tmp_path):
    record = trace.as_record(found_from(project(tmp_path)), a_spec(), root=tmp_path)
    assert record["best"]["params"]
    assert record["best"]["failed"] == ["wide"]


# -- the contact sheet -----------------------------------------------------------------


def test_the_best_handful_go_on_a_sheet_best_first(tmp_path):
    where = project(tmp_path)
    found = found_from(where)
    made = trace.sheet(found, where / "sheet.png", root=where, top=3, cell=16)
    assert (where / "sheet.png").is_file()
    assert len(made["shown"]) == 3
    scores = [s["score"] for s in made["shown"]]
    assert scores == sorted(scores, reverse=True)


def test_a_sheet_needs_the_cache_and_says_when_it_has_none(tmp_path):
    """Without a picture kept anywhere, there is nothing to lay out."""
    where = project(tmp_path)
    found = found_from(where, with_pictures=False)
    made = trace.sheet(found, where / "sheet.png", root=where)
    assert made["sheet"] is None
    assert "nothing to lay out" in made["why"]
    assert not (where / "sheet.png").exists()


def test_the_sheet_holds_no_more_than_it_was_asked_for(tmp_path):
    where = project(tmp_path)
    found = found_from(where)
    assert len(trace.sheet(found, where / "s.png", root=where, top=2)["shown"]) == 2


# -- written down ----------------------------------------------------------------------


def test_a_trace_is_written_beside_its_sheet(tmp_path):
    where = project(tmp_path)
    written = trace.write(found_from(where), out="out/run.trace", root=where, cell=16)
    assert (where / "out" / "run.trace.json").is_file()
    assert (where / "out" / "run.trace.png").is_file()
    assert written["samples"] > 0


def test_a_written_trace_reads_back(tmp_path):
    """A result nobody can reproduce is one nobody can check."""
    where = project(tmp_path, "[render]\nseed = 7\n")
    written = trace.write(
        found_from(where), out="run.trace", spec=a_spec(), root=where, cell=16
    )
    read = trace.read(written["trace"])
    assert read["seed"] == 7
    assert read["ranges"]["light"]["max"] == 4.0
    assert len(read["samples"]) == written["samples"]


def test_ranked_puts_the_best_first(tmp_path):
    found = found_from(project(tmp_path))
    best = trace.ranked(found, top=4)
    assert [s["score"] for s in best] == sorted(
        (s["score"] for s in best), reverse=True
    )


# -- through a real search -------------------------------------------------------------


def test_a_real_sweep_writes_a_trace_and_a_sheet(tmp_path):
    pytest.importorskip("bpy", reason="Blender is not importable in this interpreter")
    from polyweave import config as C

    (tmp_path / C.FILENAME).write_text(
        "[render]\npreview_size = 32\nfinal_size = 32\n"
        "samples = { sphere = 4, preview = 4, final = 4 }\nseed = 11\n",
        encoding="utf-8",
    )
    spec = accept.parse(
        {
            "asset": "sphere",
            "rung": "sphere",
            "predicate": [{"id": "reads-bright", "measure": "luma_p99", "min": 0.35}],
            "search": {"key": {"min": 10.0, "max": 2000.0}},
        }
    )
    found = search.sweep(
        spec, out="probe.png", root=tmp_path, budget=3, points=3, trace="run.trace"
    )
    written = found["trace_written"]
    assert (tmp_path / "run.trace.json").is_file()
    assert (tmp_path / "run.trace.png").is_file(), written
    read = trace.read(tmp_path / "run.trace.json")
    assert len(read["samples"]) == found["spent"]
    assert read["samples"][0]["predicates"][0]["id"] == "reads-bright"
    assert read["samples"][0]["cache_key"]
