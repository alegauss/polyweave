"""A transcription read from a reference video, checked by a person row by row (§PW383).

The owner of Spinhold checked the agent's reading of a Resogun video as free prose, its
rows citing no frames and the corrections kept in a conversation. Here each row cites
its frames or tracks, the sitting shows them beside it, and the answers are kept.
"""

from __future__ import annotations

import json

import pytest
from PIL import Image, ImageDraw

from polyweave.kernel import provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.reference import reference_objects, reference_transcription
from polyweave.loop import verdict

CYAN = (63, 232, 255)
KINDS = {"lander": {"colour": "#3fe8ff", "size": [40, 400]}}


@pytest.fixture
def frames(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    folder = tmp_path / ".polyweave" / "references" / "clip"
    folder.mkdir(parents=True)
    listed = []
    for n in range(4):
        image = Image.new("RGB", (640, 360), (8, 8, 20))
        draw = ImageDraw.Draw(image)
        for row in range(3):
            draw.rectangle((200 + 20 * n, 100 + 60 * row, 212 + 20 * n, 112 + 60 * row),
                           fill=CYAN)
        name = f"t{n * 500:08d}.png"
        image.save(folder / name)
        listed.append({"ms": n * 500, "file": name})
    (folder / "frames.json").write_text(json.dumps({"frames": listed}),
                                        encoding="utf-8")
    reference_objects.objects(".polyweave/references/clip", KINDS, root=str(tmp_path))
    return tmp_path


def sheet(root, rows=None):
    written = {
        "frames": ".polyweave/references/clip",
        "columns": ["side", "count", "formation"],
        "rows": rows if rows is not None else [
            {"id": "w1", "from": 0.0, "to": 1.5, "side": "left", "count": 3,
             "formation": "line", "frames": ["t00000000.png", "t00001500.png"]},
            {"id": "w2", "from": 0.0, "to": 1.5, "side": "left", "count": 4,
             "formation": "line", "tracks": [1, 2, 3]},
        ],
    }
    where = root / "notes" / "phase1.transcription.json"
    where.parent.mkdir(exist_ok=True)
    where.write_text(json.dumps(written), encoding="utf-8")
    return "notes/phase1.transcription.json"


def test_each_row_is_laid_out_beside_the_frames_it_cites(frames):
    made = reference_transcription.transcription(sheet(frames), root=str(frames))
    assert made["rows"] == 2
    laid = json.loads((frames / made["sitting"]).read_text("utf-8"))
    assert laid["kind"] == "transcription"
    assert set(laid["families"]) == {"w1", "w2"}
    assert laid["families"]["w1"]["about"].startswith("0–1.5 s: side left, count 3")
    record = provenance.read("notes/phase1.transcription.json", root=str(frames))
    assert record["inputs"][0]["path"].endswith("frames.json")


def test_a_person_s_answers_are_kept_and_read_back_row_by_row(frames):
    made = reference_transcription.transcription(sheet(frames), root=str(frames))
    folder = made["sitting"].rsplit("/", 1)[0]
    verdict.answer(folder, "accept", "that is the line", family="w1", root=str(frames))
    said = reference_transcription.transcribed(sheet(frames), root=str(frames))
    assert said["answered"] == 1 and said["unanswered"] == ["w2"]
    assert said["accepted"] is False
    verdict.answer(folder, "look", "three, not four", family="w2", root=str(frames))
    said = reference_transcription.transcribed(sheet(frames), root=str(frames))
    assert said["unanswered"] == []
    assert said["corrected"][0]["row"] == "w2"
    assert said["corrected"][0]["why"] == "three, not four"
    assert said["accepted"] is False


def test_a_sheet_every_row_of_which_is_right_is_accepted(frames):
    made = reference_transcription.transcription(sheet(frames), root=str(frames))
    folder = made["sitting"].rsplit("/", 1)[0]
    verdict.answer(folder, "accept", "both right", root=str(frames))
    assert reference_transcription.transcribed(sheet(frames),
                                               root=str(frames))["accepted"] is True


@pytest.mark.parametrize(
    "rows",
    [[],
     [{"id": "a", "from": 0, "to": 1, "side": "l", "count": 1, "formation": "x"}],
     [{"id": "a", "from": 0, "to": 1, "side": "l", "count": 1, "formation": "x",
       "frames": ["t99999999.png"]}],
     [{"id": "a", "from": 0, "to": 1, "side": "l", "count": 1, "formation": "x",
       "tracks": [99]}],
     [{"id": "a", "from": 2, "to": 1, "side": "l", "count": 1, "formation": "x",
       "frames": ["t00000000.png"]}],
     [{"id": "a", "from": 0, "to": 1, "count": 1, "formation": "x",
       "frames": ["t00000000.png"]}]],
)
def test_a_row_that_cites_nothing_that_exists_is_refused(frames, rows):
    with pytest.raises(PolyweaveError) as refused:
        reference_transcription.transcription(sheet(frames, rows), root=str(frames))
    assert refused.value.code == "capture.bad-transcription"
