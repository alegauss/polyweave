"""A canonical task, and a naive client beside it (§PW130).

Every other test was written by someone who had read the implementation, so none makes
a first call. Shio found its worst class this way: an unrecognised argument reported
success and did something else. Two instruments:

- the **canonical task**, "declare a small prop and reach a passing verdict", driven
  through the derived command line and counted in calls, with the output's size as a
  loose estimate of what it costs in tokens;
- a **naive client** that replays calls with the spellings a model reaches for first
  and requires every one to be refused with something to act on, never accepted and
  ignored.
"""

from __future__ import annotations

import json

import pytest

from polyweave import cli, server

PROP = """name = "crate"
output = "crate"

[params]
size = 4

[voxels]
cell = 1

[[nodes]]
id = "crate"
op = "primitive"
kind = "cube"
size = "size"
"""

SPEC = """asset = "crate"
artefact = "crate.voxels.png"

[[predicate]]
id      = "is-there"
measure = "alpha_coverage"
region  = "frame"
min     = 0.05
"""

#: The canonical task's calls, exactly: the first read, the build, the check.
CALLS = 3

#: A loose ceiling on what the task's answers cost to read, at four characters a token.
TOKENS = 2_500


def test_the_canonical_task_reaches_a_passing_verdict_in_three_calls(tmp_path, capsys):
    (tmp_path / "crate.toml").write_text(PROP, encoding="utf-8")
    (tmp_path / "crate.accept.toml").write_text(SPEC, encoding="utf-8")
    root = ["--root", str(tmp_path)]
    calls = [
        ["describe", "geometry.build", "--json"],
        ["geometry.build", "--source", "crate.toml", "--preview", "true", *root],
        [
            "accept.check",
            "--spec",
            "crate.accept.toml",
            "--subject",
            "crate.voxels.png",
            *root,
        ],
    ]
    said = []
    for argv in calls:
        assert cli.main([*argv, "--json"] if "--json" not in argv else argv) == 0
        said.append(capsys.readouterr().out)
    assert len(calls) == CALLS
    verdict = json.loads(said[-1])
    assert verdict["passed"] is True
    assert sum(len(one) for one in said) / 4 <= TOKENS


def test_the_cache_saves_the_second_build(tmp_path, capsys):
    """A mechanism's own floor: an unchanged declaration is not built again."""
    (tmp_path / "crate.toml").write_text(PROP, encoding="utf-8")
    argv = ["geometry.build", "--source", "crate.toml", "--root", str(tmp_path)]
    argv += ["--force", "false", "--json"]
    for expected in ("built", "cached"):
        assert cli.main(argv) == 0
        assert json.loads(capsys.readouterr().out)["status"] == expected


#: What a model reaches for first, and what each must come back as.
NAIVE = [
    ("render_plan", {"rungs": "sphere"}, "op.unknown-argument", "rung"),
    ("measure_take", {"subject": "a.png", "measure": ["luma_p99"]}, None, "measures"),
    ("accept_check", {"spec_path": "s.toml", "subject": "a.png"}, None, "spec"),
    ("geometry_build", {"path": "crate.toml"}, "op.unknown-argument", "force"),
    ("geometry_build", {"source": "crate.toml", "preview": "yes"}, "op.bad-type", None),
    (
        "geometry_build",
        {"source": "crate.toml", "given": "size=2"},
        "op.bad-type",
        None,
    ),
    ("render_bake", {"out": "a.png", "samples": "64"}, "op.bad-type", None),
    (
        "search_sweep",
        {"spec": "s.toml", "out": "a.png", "budget": "24"},
        "op.bad-type",
        None,
    ),
    ("loop_start", {"asset": "star", "way": "after", "change": 3}, "op.bad-type", None),
    (
        "verdict_judge",
        {"members": [], "choice": "yes", "why": "ok"},
        "op.bad-choice",
        None,
    ),
]


@pytest.mark.parametrize(("tool", "arguments", "code", "meant"), NAIVE)
def test_a_first_guess_is_refused_with_something_to_act_on(
    tool, arguments, code, meant
):
    answer = server.call(tool, arguments)
    assert answer["isError"] is True, f"{tool} accepted {arguments}"
    refused = answer["structuredContent"]["refused"]
    if code:
        assert refused["code"] == code
    if meant:
        assert refused.get("did_you_mean") == meant or meant in refused.get(
            "allowed", ()
        )
    assert refused.get("allowed") or refused.get("example") or refused["remedy"]
