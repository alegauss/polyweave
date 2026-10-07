"""The payload the window's client reads, as the server writes it (§PW303).

`gui/packages/core` reads `structuredContent` and `isError` off a `tools/call`, with
the operation's dotted name spelled with underscores. Its own tests run against a fake
server, so this holds the real one to the same shape from this side.
"""

from __future__ import annotations

from polyweave import server


def test_an_inventory_call_answers_the_shape_the_window_reads(tmp_path):
    reply = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "project_inventory",
                "arguments": {"root": str(tmp_path)},
            },
        }
    )
    result = reply["result"]
    assert result["isError"] is False
    assert set(result["structuredContent"]) == {"items", "total", "kinds", "next"}


def test_a_refusal_answers_under_refused_with_its_code(tmp_path):
    reply = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "project_inventory",
                "arguments": {"root": str(tmp_path), "kind": "hologram"},
            },
        }
    )
    result = reply["result"]
    assert result["isError"] is True
    assert result["structuredContent"]["refused"]["code"] == "op.bad-choice"
