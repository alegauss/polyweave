"""A project's own measure: declared, bounded, searched, recorded and stale (§PW517)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import polyweave.layers
from polyweave.kernel import codes as K
from polyweave.kernel import config as C
from polyweave.kernel import layer as L
from polyweave.kernel.describe import _REGISTRY
from polyweave.kernel.errors import PolyweaveError
from polyweave.loop import accept, extend, measure, search
from polyweave.surface import project

#: The fixture layer that makes a tone, whose producer the search turns (§PW512).
SHELF = Path(__file__).parent / "fixtures" / "layers"

PROJECT = '''[project]
name = "bells"

[extend.measures.pitch]
fn = "tools/hz.py:hz"
subject = "file"
unit = "Hz"
range = [0, 20000]
direction = "higher"
about = "how high the bell rings, by its rising zero crossings"
why = "polyweave measures no pitch off a sound file"
'''

HZ = '''import struct
import wave


def hz(path):
    with wave.open(path, "rb") as one:
        count, rate = one.getnframes(), one.getframerate()
        values = struct.unpack(f"<{count}h", one.readframes(count))
    rising = sum(1 for a, b in zip(values, values[1:], strict=False) if a < 0 <= b)
    return rising * rate / count
'''

SPEC = '''asset = "bell"

[[predicate]]
id = "pitched"
measure = "x.bells.pitch"
min = 400
max = 480
'''


@pytest.fixture
def bells(tmp_path, monkeypatch):
    monkeypatch.setattr(
        polyweave.layers, "__path__", [*polyweave.layers.__path__, str(SHELF)])
    for clear in (L.layers, K._every, C._schema):
        clear.cache_clear()
    game = tmp_path / "bells"
    (game / "tools").mkdir(parents=True)
    (game / C.FILENAME).write_text(PROJECT, encoding="utf-8")
    (game / "tools" / "hz.py").write_text(HZ, encoding="utf-8")
    (game / "bell.accept.toml").write_text(SPEC, encoding="utf-8")
    (game / "bell.tone.toml").write_text("pitch = 440\n", encoding="utf-8")
    yield game
    monkeypatch.undo()
    for clear in (L.layers, K._every, C._schema):
        clear.cache_clear()
    _REGISTRY.pop("tone.make", None)
    for name in [m for m in sys.modules if m.startswith("polyweave.layers.tone")]:
        del sys.modules[name]


def _tone(game: Path, pitch: float, out: str = "bell.wav") -> str:
    from polyweave.layers.tone import wave

    wave.write(game / out, pitch=pitch, seconds=0.25)
    return out


def test_a_project_measure_is_described_from_its_file_alone(bells):
    found = measure.available(str(bells))["extended"]
    assert found["x.bells.pitch"]["unit"] == "Hz"
    assert found["x.bells.pitch"]["range"] == [0.0, 20000.0]
    assert not [name for name in sys.modules if "hz" in name.split(".")[-1]]


def test_a_spec_bounds_it_and_check_runs_it_apart(bells):
    _tone(bells, 440)
    said = accept.checked("bell.accept.toml", "bell.wav", root=str(bells))
    [pitched] = said["predicates"]
    assert said["passed"] is True and 400 <= pitched["value"] <= 480
    assert pitched["unit"] == "Hz" and pitched["source"]["fn"] == "tools/hz.py:hz"
    _tone(bells, 880)
    assert accept.checked("bell.accept.toml", "bell.wav",
                          root=str(bells))["failed"] == ["pitched"]


def test_a_search_aims_at_it(bells):
    (bells / "sweep.accept.toml").write_text(
        SPEC + "\n[search.pitch]\nmin = 300\nmax = 600\n", encoding="utf-8")
    found = search.sweep("sweep.accept.toml", out="swept.wav", root=str(bells),
                         producer="tone", budget=16)
    assert found["passed"] is True


def test_a_value_is_recorded_and_stale_once_its_function_changes(bells):
    _tone(bells, 440)
    accept.checked("bell.accept.toml", "bell.wav", root=str(bells))
    assert extend.stale(bells) == []
    hz = bells / "tools" / "hz.py"
    hz.write_text(hz.read_text(encoding="utf-8") + "\n# tuned\n", encoding="utf-8")
    [stale] = extend.stale(bells)
    assert stale["measure"] == "x.bells.pitch" and stale["subject"] == "bell.wav"
    assert measure.available(str(bells))["stale"] == [stale]


@pytest.mark.parametrize(("body", "code"), [
    ("def hz(path):\n    return 30000.0\n", "spec.measure-out-of-range"),
    ("def hz(path):\n    return 'loud'\n", "spec.measure-out-of-range"),
    ("def hz(path):\n    raise ValueError('cracked')\n", "spec.measure-failed"),
], ids=["outside its range", "not a number", "raises"])
def test_a_measure_that_answers_badly_is_refused_never_clamped(bells, body, code):
    _tone(bells, 440)
    (bells / "tools" / "hz.py").write_text(body, encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        accept.checked("bell.accept.toml", "bell.wav", root=str(bells))
    assert refused.value.code == code


def test_a_spec_naming_a_measure_the_project_lacks_is_refused_with_its_own(bells):
    (bells / "odd.accept.toml").write_text(
        SPEC.replace("x.bells.pitch", "x.bells.glow"), encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        accept.read("odd.accept.toml", bells)
    assert refused.value.code == "spec.unknown-measure"
    assert refused.value.allowed == ["x.bells.pitch"]


def test_a_declaration_missing_a_field_is_a_project_check_finding(bells):
    (bells / C.FILENAME).write_text(PROJECT.replace('unit = "Hz"\n', ""),
                                    encoding="utf-8")
    found = project.check(str(bells))["findings"]
    assert "config.bad-measure" in {one["code"] for one in found}
