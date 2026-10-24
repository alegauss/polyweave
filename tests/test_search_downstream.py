"""A sample judged downstream of what made it (§PW621).

Cottony's sky is a panel the project draws, and it is judged in the board's capture,
so each seed was drawn, imported, captured and checked by a throwaway loop.
"""

from __future__ import annotations

import pytest
from PIL import Image

from polyweave.kernel.errors import PolyweaveError
from polyweave.loop import accept, search

#: What the fake engine was asked to run, in order.
RAN: list = []


def after(runs, root="."):
    """The engine layer's part, standing in: the capture is the sample, a shade lit."""
    from pathlib import Path

    RAN.append(list(runs))
    if runs == ["broken"]:
        raise PolyweaveError("search.downstream-failed", "it did not run", "read it")
    with Image.open(Path(root) / "sky.png") as drawn:
        lit = drawn.point(lambda v: min(255, v + 40))
        lit.save(Path(root) / "board.png")


def _spec(root):
    where = root / "board.accept.toml"
    where.write_text(
        "asset = 'board'\n"
        "[[predicate]]\n"
        "id = 'sky-not-too-bright'\n"
        "measure = 'luma_p99'\n"
        "region = 'frame'\n"
        "max = 0.3\n"
        "[search.grey]\n"
        "min = 0\n"
        "max = 200\n",
        encoding="utf-8",
    )
    return accept.read(where)


def sky(report, *, out, rung=None, root=".", inline=True, grey=0):
    from pathlib import Path

    grey = int(grey)
    Image.new("RGB", (16, 16), (grey, grey, grey)).save(Path(root) / out)
    return {"artefact": out}


@pytest.fixture
def fake_engine(monkeypatch):
    RAN.clear()
    monkeypatch.setattr(search, "needed", lambda name: "test_search_downstream:after")


def test_each_sample_is_judged_in_the_capture_its_runs_make(tmp_path, fake_engine):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    evaluate = search.renderer(_spec(tmp_path), out="sky.png", root=tmp_path,
                               bake=sky, producer="render", rung="preview",
                               then=("board",), judged="board.png")
    # 130 drawn would pass; the capture lights it past the bound, and it is the
    # capture that is judged.
    dark, lit = evaluate({"grey": 10}), evaluate({"grey": 130})
    assert RAN == [["board"], ["board"]]
    assert dark["passed"]
    assert not lit["passed"]


def test_a_run_that_fails_refuses_the_sample(tmp_path, fake_engine):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    evaluate = search.renderer(_spec(tmp_path), out="sky.png", root=tmp_path,
                               bake=sky, rung="preview", then=("broken",),
                               judged="board.png")
    with pytest.raises(PolyweaveError) as refused:
        evaluate({"grey": 10})
    assert refused.value.code == "search.downstream-failed"


def test_with_no_runs_the_sample_itself_is_judged(tmp_path, fake_engine):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    evaluate = search.renderer(_spec(tmp_path), out="sky.png", root=tmp_path,
                               bake=sky, rung="preview")
    assert evaluate({"grey": 130})["passed"]
    assert RAN == []


def test_a_project_producer_s_seed_is_its_own_and_not_noise():
    """A sky's layout seed is what Cottony searched; a render's seed is still noise."""
    def drawn(report, *, out, seed=0):  # pragma: no cover - never called here
        return {}

    assert search.turnable(drawn, {"seed": {}}, producer="x.cottony.sky") == ["seed"]
    with pytest.raises(PolyweaveError) as refused:
        search.turnable(drawn, {"seed": {}}, producer="render")
    assert refused.value.code == "search.noise-axis"
