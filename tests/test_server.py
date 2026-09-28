"""A served surface that is a shape over the registry (§PW126)."""

from __future__ import annotations

import io
import json
import subprocess
import sys

from PIL import Image

from polyweave import describe, server


def listed(blender=True):
    return {t["name"]: t for t in server.tools(blender=blender)}


def test_every_operation_is_a_tool_named_as_a_client_takes():
    tools = listed()
    assert set(tools) == {server.tool_name(op) for op in describe.operations()}
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_-")
    assert all(set(name) <= allowed for name in tools)


def test_a_schema_carries_the_range_the_choices_and_what_is_required():
    bake = listed()["render_bake"]["inputSchema"]
    assert bake["additionalProperties"] is False
    assert "out" in bake["required"]
    azimuth = bake["properties"]["azimuth"]
    assert (azimuth["minimum"], azimuth["maximum"]) == (-360, 360)
    assert azimuth["type"] == "number"
    assert "deg" in azimuth["description"]
    assert bake["properties"]["rung"]["enum"] == ["sphere", "preview", "final"]
    judge = listed()["verdict_judge"]["inputSchema"]
    assert judge["properties"]["choice"]["enum"] == ["accept", "look", "number"]


def test_the_list_and_every_tool_stay_within_their_budgets():
    tools = server.tools(blender=True)
    for one in tools:
        assert len(json.dumps(one)) <= server.TOOL_BUDGET, one["name"]
    assert len(json.dumps(tools)) <= server.LIST_BUDGET


def test_a_tool_that_needs_blender_is_left_out_where_there_is_none():
    without = listed(blender=False)
    assert "render_bake" not in without
    assert "search_sweep" not in without
    assert "accept_check" in without


def test_a_call_answers_with_what_json_prints(tmp_path):
    (tmp_path / "s.accept.toml").write_text(
        "asset = 's'\n[[predicate]]\nid = 'tone'\nmeasure = 'luma_p99'\n"
        "region = 'frame'\nmax = 0.37\n",
        encoding="utf-8",
    )
    Image.new("RGBA", (8, 8), (102, 102, 102, 255)).save(tmp_path / "s.png")
    found = server.call(
        "accept_check",
        {"spec": "s.accept.toml", "subject": "s.png", "root": str(tmp_path)},
    )
    assert found["isError"] is False
    assert json.loads(found["content"][0]["text"])["passed"] is True
    assert found["structuredContent"]["passed"] is True


def test_a_refused_call_is_an_error_result_naming_its_code():
    found = server.call("accept_check", {"spec": "nope", "subject": "x", "sixe": 1})
    assert found["isError"] is True
    assert found["structuredContent"]["refused"]["code"] == "op.unknown-argument"
    assert server.call("no_such", {})["structuredContent"]["refused"]["code"] == (
        "op.unknown"
    )


def test_an_operation_that_raises_is_refused_and_the_server_answers_on(
    tmp_path, monkeypatch
):
    """§PW261: one raise inside a tool closed the connection, and every tool with it."""
    from dataclasses import replace

    def broken(*_, **__):
        raise AttributeError("'str' object has no attribute 'get'")

    held = describe._REGISTRY["verdict.answers"]
    monkeypatch.setitem(describe._REGISTRY, "verdict.answers", replace(held, fn=broken))
    found = server.call("verdict_answers", {"root": str(tmp_path)})
    assert found["isError"] is True
    refused = found["structuredContent"]["refused"]
    assert refused["code"] == "op.crashed"
    assert "AttributeError" in refused["message"]
    assert "test_server.py" in refused["detail"]
    assert server.call("no_such", {})["isError"] is True


def test_a_sitting_of_bare_paths_is_refused_by_member_not_raised(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    found = server.call("verdict_sitting", {
        "families": {"citadel": [7]}, "out": "review", "root": str(tmp_path)})
    refused = found["structuredContent"]["refused"]
    assert refused["code"] == "verdict.bad-member"
    assert "member 0" in refused["message"]


def test_the_protocol_answers_initialize_list_and_ping_and_not_a_notification():
    lines = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "ping"},
        {"jsonrpc": "2.0", "id": 4, "method": "resources/list"},
    ]
    out = io.StringIO()
    server.serve(io.StringIO("\n".join(json.dumps(m) for m in lines) + "\n"), out)
    replies = [json.loads(line) for line in out.getvalue().splitlines()]
    assert [r["id"] for r in replies] == [1, 2, 3, 4]
    assert replies[0]["result"]["serverInfo"]["name"] == "polyweave"
    assert replies[1]["result"]["tools"]
    assert replies[2]["result"] == {}
    assert replies[3]["error"]["code"] == -32601


def test_the_server_runs_over_stdio_from_the_command_line():
    request = {"jsonrpc": "2.0", "id": 7, "method": "tools/list"}
    done = subprocess.run(
        [sys.executable, "-m", "polyweave", "serve"],
        input=json.dumps(request) + "\n",
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    (reply,) = [json.loads(line) for line in done.stdout.splitlines()]
    assert reply["id"] == 7
    assert any(t["name"] == "accept_check" for t in reply["result"]["tools"])
