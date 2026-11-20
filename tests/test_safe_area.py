"""Burned-in text held to the part of a frame a platform leaves visible (§PW698)."""

from __future__ import annotations

import pytest

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.store.safe import safe_area

#: A 1080x1920 script: a caption style centred at the bottom, 200 px up.
ASS = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, Bold, ScaleX, ScaleY, Outline, \
Shadow, Alignment, MarginL, MarginR, MarginV
Style: Caption,Arial,70,&H00FFFFFF,0,100,100,4,0,2,40,40,200
Style: Hook,Arial,90,&H00FFFFFF,1,100,100,4,0,8,40,40,300

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.50,Hook,,0,0,0,,Scion in one minute
Dialogue: 0,0:00:02.50,0:00:05.00,Caption,,0,0,0,,a caption the title covers
Dialogue: 0,0:00:05.00,0:00:07.00,Caption,,0,0,0,,{\\an5\\pos(540,960)}centred, clear
Dialogue: 0,0:00:07.00,0:00:09.00,Caption,,0,0,0,,{\\an5\\pos(900,1200)}under buttons
"""


@pytest.fixture
def project(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "short.ass").write_text(ASS, encoding="utf-8")
    return tmp_path


def test_lines_under_a_shorts_controls_are_named_with_their_time_and_reach(project):
    said = safe_area("short.ass", size=[1080, 1920], root=str(project))
    assert said["lines"] == 4 and said["passed"] is False
    crossed = {one["line"]: one for one in said["crossed"]}
    assert set(crossed) == {2, 4}
    assert "title" in {hit["area"] for hit in crossed[2]["crosses"]}
    assert crossed[2]["start"] == 2.5 and crossed[2]["end"] == 5.0
    assert "buttons" in {hit["area"] for hit in crossed[4]["crosses"]}
    assert all(hit["by_px"] > 0 for hit in crossed[4]["crosses"])
    assert said["exclude"]["buttons"] == [940.0, 900.0, 1080.0, 1700.0]


def test_the_call_s_own_bounds_replace_the_preset_s(project):
    said = safe_area("short.ass", size=[1080, 1920], exclude={},
                     safe=[0, 0, 1080, 1920], root=str(project))
    # With nothing covered, only the line pushed past the frame's right edge crosses.
    assert [one["line"] for one in said["crossed"]] == [4]
    assert {hit["area"] for hit in said["crossed"][0]["crosses"]} == {"safe"}
    narrow = safe_area("short.ass", size=[1080, 1920], preset="none",
                       safe=[400, 0, 680, 1920], root=str(project))
    assert {one["line"] for one in narrow["crossed"]} >= {1, 3}
    assert narrow["crossed"][0]["crosses"][0]["area"] == "safe"


def test_a_script_is_scaled_to_the_video_size(project):
    half = safe_area("short.ass", size=[540, 960], root=str(project))
    whole = safe_area("short.ass", size=[1080, 1920], root=str(project))
    assert [one["line"] for one in half["crossed"]] == [
        one["line"] for one in whole["crossed"]]
    assert half["crossed"][0]["box"][3] == pytest.approx(
        whole["crossed"][0]["box"][3] / 2, abs=2)


def test_a_file_with_no_line_is_refused(project):
    (project / "empty.ass").write_text("[Script Info]\nPlayResX: 10\n", "utf-8")
    with pytest.raises(PolyweaveError) as refused:
        safe_area("empty.ass", root=str(project))
    assert refused.value.code == "video.bad-subtitles"
