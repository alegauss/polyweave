"""A timeline of what a reference video says happened, to split it at (§PW381).

The frames here are drawn: dark play with one white flash at 1.5 s and a score region.
The soundtrack is a WAV of silence with two clicks, which ffmpeg reads as it reads a
video's audio.
"""

from __future__ import annotations

import json
import shutil
import wave

import numpy as np
import pytest
from PIL import Image

from polyweave.kernel import provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.reference import reference_events

DECLARED = """\
[reference]
size = [320, 180]
regions = { play = [0, 20, 320, 180], score = [0, 0, 120, 20] }
"""


def film(tmp_path, clicks=(1.0, 2.5)):
    (tmp_path / "polyweave.toml").write_text(DECLARED, encoding="utf-8")
    folder = tmp_path / ".polyweave" / "references" / "clip"
    folder.mkdir(parents=True)
    rate = 22050
    sound = np.zeros(int(rate * 3.5))
    for at in clicks:
        start = int(at * rate)
        sound[start:start + 400] = np.sin(np.linspace(0, 200, 400)) * 0.9
    video = tmp_path / "clip.wav"
    with wave.open(str(video), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes((sound * 32767).astype(np.int16).tobytes())
    listed = []
    for n in range(12):
        at = n * 0.25
        shade = 250 if at == 1.5 else 20 + (n % 3)
        Image.new("RGB", (320, 180), (shade, shade, shade)).save(
            folder / f"t{int(at * 1000):08d}.png")
        listed.append({"ms": int(at * 1000), "file": f"t{int(at * 1000):08d}.png"})
    (folder / "frames.json").write_text(
        json.dumps({"video": video.as_posix(), "frames": listed}), encoding="utf-8")
    return ".polyweave/references/clip"


def test_a_flash_is_found_where_the_play_area_spikes(tmp_path):
    made = reference_events.events(film(tmp_path), play="play", sound=False,
                                   root=str(tmp_path))
    written = json.loads((tmp_path / made["events"]).read_text("utf-8"))
    flashes = [e for e in written["events"] if e["kind"] == "flash"]
    assert {e["at"] for e in flashes} == {1.5}
    assert {e["what"] for e in flashes} == {"bright", "changed"}
    assert (tmp_path / made["timeline"]).is_file()
    record = provenance.read(made["events"], root=str(tmp_path))
    assert record["params"]["play"] == "play"


def test_the_soundtrack_s_strong_onsets_are_on_the_timeline(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("no ffmpeg on this machine")
    made = reference_events.events(film(tmp_path), root=str(tmp_path))
    written = json.loads((tmp_path / made["events"]).read_text("utf-8"))
    heard = [e["at"] for e in written["events"] if e["kind"] == "onset"]
    assert heard, written["sound"]
    assert all(min(abs(at - click) for click in (1.0, 2.5)) < 0.1 for at in heard)
    assert written["sound"] == "read"


def test_a_number_s_changes_are_events_and_its_unread_frames_are_listed(
        tmp_path, monkeypatch):
    film(tmp_path)
    folder = tmp_path / ".polyweave" / "references" / "clip"
    shown = json.loads((folder / "frames.json").read_text("utf-8"))["frames"]
    said = iter([100, 100, None, 250] + [250] * 8)
    monkeypatch.setattr(reference_events, "_read", lambda *_: next(said))
    found, failed = reference_events.numbers(
        shown, folder, {"score": [0, 0, 120, 20]}, engine="tesseract")
    assert found == [{"at": 0.75, "kind": "number", "what": "score", "from": 100,
                      "to": 250}]
    assert failed == {"score": [0.5]}


def test_without_an_ocr_engine_a_number_is_said_unread_never_guessed(tmp_path):
    film(tmp_path)
    folder = tmp_path / ".polyweave" / "references" / "clip"
    found, failed = reference_events.numbers([], folder, {"score": [0, 0, 1, 1]}, None)
    assert found == [] and failed == {"score": "no OCR engine to read it"}


# -- music sections, and the timeline under its frames (§PW405) ---------------------


def tones(first, second, seconds=8.0, rate=reference_events.ONSET_RATE):
    """One tone for half the soundtrack, another for the rest, both with harmonics."""
    t = np.arange(int(rate * seconds)) / rate
    pitch = np.where(t < seconds / 2, first, second)
    phase = 2 * np.pi * np.cumsum(pitch) / rate
    return 0.4 * (np.sin(phase) + 0.5 * np.sin(2 * phase) + 0.25 * np.sin(3 * phase))


def test_two_tones_in_turn_are_one_section_at_the_turn():
    found = reference_events.sections(tones(220.0, 660.0))
    assert [one["kind"] for one in found] == ["section"]
    assert found[0]["at"] == pytest.approx(4.0, abs=0.5)


def test_one_tone_throughout_and_silence_have_no_section():
    assert reference_events.sections(tones(330.0, 330.0)) == []
    assert reference_events.sections(np.zeros(reference_events.ONSET_RATE * 8)) == []


def test_a_section_is_read_off_a_video_s_soundtrack(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("no ffmpeg on this machine")
    folder = film(tmp_path)
    video = tmp_path / "clip.wav"
    rate = reference_events.ONSET_RATE
    with wave.open(str(video), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes((tones(220.0, 660.0) * 32767).astype(np.int16).tobytes())
    made = reference_events.events(folder, root=str(tmp_path))
    written = json.loads((tmp_path / made["events"]).read_text("utf-8"))
    turns = [e["at"] for e in written["events"] if e["kind"] == "section"]
    assert turns == [pytest.approx(4.0, abs=0.5)]
    assert made["counted"]["section"] == 1


def test_a_flash_s_tick_is_drawn_under_the_white_frame(tmp_path):
    made = reference_events.events(film(tmp_path), play="play", sound=False,
                                   root=str(tmp_path))
    folder = tmp_path / ".polyweave" / "references" / "clip"
    shown = reference_events.thumbnailed(
        json.loads((folder / "frames.json").read_text("utf-8"))["frames"])
    written = json.loads((tmp_path / made["events"]).read_text("utf-8"))
    flash = [e for e in written["events"] if e["kind"] == "flash"]
    starts = [one["ms"] / 1000 for one in shown]
    for index, _ in reference_events.placed(flash, starts):
        assert shown[index]["ms"] == 1500  # the white frame
    # And on the picture: the flash row under that thumbnail holds the tick.
    with Image.open(tmp_path / made["timeline"]) as picture:
        index, share = reference_events.placed(flash[:1], starts)[0]
        x = 70 + index * 160 + round(share * 159)
        y = 90 + reference_events.KINDS.index("flash") * 20 + 10
        assert picture.convert("RGB").getpixel((x, y)) == (255, 220, 90)


def test_a_region_the_reference_does_not_declare_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        reference_events.events(film(tmp_path), numbers_in=["lives"], sound=False,
                                root=str(tmp_path))
    assert refused.value.code == "capture.unknown-region"
