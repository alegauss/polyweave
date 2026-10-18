"""A project's own operation: listed, described, called, run as a job, swept and
recorded (§PW518)."""

from __future__ import annotations

import json

import pytest

from polyweave.kernel import config as C
from polyweave.kernel import provenance
from polyweave.kernel.jobs import JobStore
from polyweave.loop import extend, search
from polyweave.surface import cli, project, server

PROJECT = '''[project]
name = "bells"

[extend.measures.pitch]
fn = "tools/hz.py:hz"
subject = "file"
unit = "Hz"
range = [0, 20000]
about = "how high the bell rings"

[extend.operations.ring]
fn = "tools/ring.py:ring"
about = "ring a bell at a pitch, into a wav"
produces = "sound"
producer = true
[extend.operations.ring.params]
out = { type = "str", about = "where the wav is written" }
pitch = { type = "float", about = "how high", lo = 50, hi = 2000, unit = "Hz", \
default = 440.0 }

[extend.operations.peal]
fn = "tools/ring.py:ring"
about = "ring a bell as a job"
produces = "sound"
kind = "fetch"
[extend.operations.peal.params]
out = { type = "str", about = "where the wav is written" }
pitch = { type = "float", about = "how high", lo = 50, hi = 2000, default = 440.0 }
'''

RING = '''import math
import struct
import wave


def ring(out, pitch=440.0):
    rate = 8000
    frames = b"".join(
        struct.pack("<h", int(20000 * math.sin(2 * math.pi * pitch * i / rate)))
        for i in range(rate // 4))
    with wave.open(out, "wb") as one:
        one.setnchannels(1)
        one.setsampwidth(2)
        one.setframerate(rate)
        one.writeframes(frames)
    return {"artefact": out, "pitch": pitch}
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

[search.pitch]
min = 300
max = 600
'''


@pytest.fixture
def bells(tmp_path, monkeypatch):
    game = tmp_path / "bells"
    (game / "tools").mkdir(parents=True)
    (game / C.FILENAME).write_text(PROJECT, encoding="utf-8")
    (game / "tools" / "ring.py").write_text(RING, encoding="utf-8")
    (game / "tools" / "hz.py").write_text(HZ, encoding="utf-8")
    (game / "bell.accept.toml").write_text(SPEC, encoding="utf-8")
    # The server and the command line serve the project they are started in.
    monkeypatch.chdir(game)
    return game


def _said(answer: dict) -> dict:
    assert not answer["isError"], answer["structuredContent"]
    return answer["structuredContent"]


def test_it_is_listed_as_a_tool_with_its_declared_schema(bells):
    tools = {one["name"]: one for one in server.tools(blender=False, root=bells)}
    ring = tools["x_bells_ring"]["inputSchema"]
    assert ring["properties"]["pitch"]["minimum"] == 50
    assert ring["properties"]["pitch"]["maximum"] == 2000
    assert ring["required"] == ["out"]
    assert server.session(bells)["size"] > 0
    assert "project" in server.shares(server.tools(blender=True, root=bells))


def test_it_is_described_by_its_own_name_and_its_tools(bells):
    for name in ("x.bells.ring", "x_bells_ring"):
        said = _said(server.call("describe", {"operation": name}))
        assert said["operation"] == "x.bells.ring" and said["produces"] == "sound"
        assert {p["name"] for p in said["parameters"]} == {"out", "pitch"}


def test_a_call_runs_it_apart_and_records_what_it_made(bells):
    said = _said(server.call("x_bells_ring", {"out": "a.wav", "pitch": 440}))
    assert said["result"]["pitch"] == 440 and said["artefact"] == "a.wav"
    record = provenance.read("a.wav", bells)
    assert record["kind"] == "extend"
    assert [one["role"] for one in record["inputs"]] == ["fn"]


def test_a_call_outside_its_declaration_is_refused_before_it_runs(bells):
    refused = server.call("x_bells_ring", {"out": "b.wav", "pitch": 5})
    assert refused["isError"] and refused["structuredContent"]["refused"]["code"]
    assert not (bells / "b.wav").exists()
    unknown = server.call("x_bells_ring", {"out": "b.wav", "volume": 3})
    assert unknown["structuredContent"]["refused"]["code"] == "op.unknown-argument"


def test_one_with_a_kind_runs_as_a_job(bells):
    handle = extend.called("x.bells.peal", {"out": "j.wav"}, bells)
    result = JobStore.for_project(bells).result(handle["job"], wait=True)
    assert result["stage"] == "done", result
    assert (bells / "j.wav").is_file()
    assert provenance.read("j.wav", bells)["kind"] == "extend"


def test_a_search_turns_it_as_a_producer(bells):
    found = search.sweep("bell.accept.toml", out="swept.wav", root=str(bells),
                         producer="x.bells.ring", budget=16)
    assert found["passed"] is True
    assert 300 <= found["best"]["pitch"] <= 600


def test_what_it_made_goes_stale_when_its_function_changes(bells):
    _said(server.call("x_bells_ring", {"out": "a.wav"}))
    assert provenance.outdated(root=str(bells))["outdated"] == []
    ring = bells / "tools" / "ring.py"
    ring.write_text(ring.read_text(encoding="utf-8") + "\n# retuned\n",
                    encoding="utf-8")
    [stale] = provenance.outdated(root=str(bells))["outdated"]
    assert stale["moved"] == ["tools/ring.py"]


def test_the_command_line_takes_its_flags(bells, capsys):
    assert cli.main(["x.bells.ring", "--out", "c.wav", "--pitch", "500", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["result"]["pitch"] == 500
    assert (bells / "c.wav").is_file()


def test_a_declaration_it_cannot_serve_is_a_project_check_finding(bells):
    (bells / C.FILENAME).write_text(
        PROJECT.replace('kind = "fetch"', 'kind = "build"'), encoding="utf-8")
    found = project.check(str(bells))["findings"]
    assert "config.bad-operation" in {one["code"] for one in found}
