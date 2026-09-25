"""The command line, derived from the registry (§PW125)."""

from __future__ import annotations

import json

import pytest
from PIL import Image

from polyweave import cli, commands, describe
from polyweave.errors import PolyweaveError


def run(argv, capsys):
    status = cli.main(argv)
    return status, capsys.readouterr()


def spec(tmp_path, bound=0.37):
    (tmp_path / "star.accept.toml").write_text(
        f"asset = 'star'\n[[predicate]]\nid = 'tone'\nmeasure = 'luma_p99'\n"
        f"region = 'frame'\nmax = {bound}\n",
        encoding="utf-8",
    )
    Image.new("RGBA", (8, 8), (102, 102, 102, 255)).save(tmp_path / "star.png")


def test_every_operation_is_a_subcommand_with_its_parameters(capsys):
    import argparse

    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command")
    commands.add_operations(subcommands)
    offered = set(subcommands.choices)
    assert set(describe.operations()) <= offered
    assert set(commands.VERBS) <= offered
    with pytest.raises(SystemExit):
        cli.main(["accept.check", "--help"])
    shown = capsys.readouterr().out
    for flag in ("--spec", "--subject", "--rung"):
        assert flag in shown


def test_an_operation_is_called_by_name_and_answers_as_data(tmp_path, capsys):
    spec(tmp_path)
    argv = ["accept.check", "--spec", "star.accept.toml", "--subject", "star.png"]
    status, printed = run([*argv, "--root", str(tmp_path), "--json"], capsys)
    assert status == 0
    assert json.loads(printed.out)["passed"] is True


def test_the_text_never_says_anything_the_json_lacks(tmp_path, capsys):
    spec(tmp_path)
    argv = ["accept.check", "--spec", "star.accept.toml", "--subject", "star.png"]
    argv += ["--root", str(tmp_path)]
    _, as_text = run(argv, capsys)
    _, as_json = run([*argv, "--json"], capsys)
    data = json.loads(as_json.out)
    for line in as_text.out.splitlines():
        path, _, shown = line.partition(": ")
        value = data
        for step in path.replace("[", ".[").split("."):
            value = value[int(step[1:-1])] if step.startswith("[") else value[step]
        assert shown == (value if isinstance(value, str) else json.dumps(value))


def test_a_refusal_prints_its_code_and_exits_one(tmp_path, capsys):
    status, printed = run(
        ["accept.check", "--spec", "nope.toml", "--subject", "x.png"], capsys
    )
    assert status == 1
    assert "spec.missing" in printed.err
    assert "do: " in printed.err


def test_a_required_parameter_left_out_is_argparse_refusing(capsys):
    with pytest.raises(SystemExit):
        cli.main(["accept.check", "--spec", "star.accept.toml"])
    assert "--subject" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("text", "kind", "value"),
    [
        ("star.png", "str", "star.png"),
        ("3", "int", 3),
        ("true", "bool", True),
        ('["a", "b"]', "list", ["a", "b"]),
        ("star.glb", "any", "star.glb"),
        ('{"covers": [2, 1]}', "any", {"covers": [2, 1]}),
    ],
)
def test_a_value_is_read_as_its_declared_type(text, kind, value):
    assert commands.parsed(text, {"name": "x", "type": kind}) == value


def test_a_value_that_is_not_its_type_is_refused():
    with pytest.raises(PolyweaveError) as refused:
        commands.parsed("three", {"name": "budget", "type": "int"})
    assert refused.value.code == "op.bad-type"
    assert "3" in refused.value.remedy


def test_the_first_reads_are_verbs(capsys):
    status, printed = run(["explain", "spec.no-screen", "--json"], capsys)
    assert status == 0
    assert json.loads(printed.out)["code"] == "spec.no-screen"
    status, printed = run(["describe", "render.plan", "--json"], capsys)
    assert json.loads(printed.out)["operation"] == "render.plan"
    status, printed = run(["capabilities", "--no-probe", "--json"], capsys)
    assert "operations" in json.loads(printed.out)


def test_an_asynchronous_operation_can_be_started_as_a_job(
    tmp_path, capsys, monkeypatch
):
    started = []

    class Store:
        def start(self, target, *, kind, args):
            started.append((target, kind, args))
            return {"job": "j1", "kind": kind}

    from polyweave import jobs

    monkeypatch.setattr(jobs.JobStore, "for_project", classmethod(lambda c, r: Store()))
    spec(tmp_path)
    status, printed = run(
        [
            "search.sweep",
            "--spec",
            "star.accept.toml",
            "--out",
            "s.png",
            "--budget",
            "4",
            "--root",
            str(tmp_path),
            "--job",
            "--json",
        ],
        capsys,
    )
    assert status == 0
    assert json.loads(printed.out)["job"] == "j1"
    ((target, kind, args),) = started
    assert target == "polyweave.search:sweep"
    assert kind == "search"
    assert args["budget"] == 4
