"""The window's typed SDK is generated from describe and kept fresh (§PW377).

The window calls operations by name, and a parameter renamed in Python would reach it
as a refusal at run time. The SDK carries every operation's arguments as `describe`
answers them, so the window's typecheck fails instead, and this test fails whenever the
committed file and describe disagree.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def generator():
    spec = importlib.util.spec_from_file_location(
        "operations_ts", ROOT / "tools" / "operations_ts.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_committed_sdk_is_what_describe_answers_now():
    made = generator()
    assert made.TARGET.read_text(encoding="utf-8") == made.current(), (
        "gui/packages/core/src/operations.generated.ts is stale: "
        "run python tools/operations_ts.py")


def test_a_parameter_s_choices_range_and_default_reach_the_type():
    made = generator()
    text = made.generate([{
        "operation": "clip.camera_like",
        "summary": "A made-up operation.",
        "parameters": [
            {"name": "ease", "type": "str", "required": True, "about": "how",
             "choices": ["linear", "sine"]},
            {"name": "hold", "type": "float", "required": False, "default": 1.5,
             "about": "how long", "range": [0.0, None], "unit": "s"},
        ],
    }])
    assert "export interface ClipCameraLikeArgs {" in text
    assert '  ease: "linear" | "sine"' in text
    assert "/** how long; from 0 to …; in s; default 1.5 */" in text
    assert '  hold?: number' in text
    assert 'export type Bare = never' not in text
