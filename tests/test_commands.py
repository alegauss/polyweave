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


LIST = {"name": "args", "type": "list"}


def test_a_list_flag_given_once_per_item_is_the_list():
    """§PW247: PowerShell 5.1 strips JSON's inner quotes; a repeated flag has none."""
    assert commands.parsed(["--scene=res://a.tscn", "--frames=45", "3"], LIST) == [
        "--scene=res://a.tscn",
        "--frames=45",
        3,
    ]


def test_a_list_flag_may_name_a_json_file(tmp_path):
    where = tmp_path / "args.json"
    where.write_text('["--boss", "--frames=420"]', encoding="utf-8")
    assert commands.parsed([f"@{where}"], LIST) == ["--boss", "--frames=420"]


def test_a_json_file_written_by_windows_powershell_is_read_past_its_mark(tmp_path):
    """§PW334: Set-Content -Encoding utf8 in PowerShell 5.1 always writes a BOM."""
    where = tmp_path / "members.json"
    where.write_bytes(b"\xef\xbb\xbf" + b'["--boss", "--frames=420"]')
    assert commands.parsed([f"@{where}"], LIST) == ["--boss", "--frames=420"]


def test_declarations_saved_with_a_byte_order_mark_are_read(tmp_path):
    from polyweave import pressure, world
    from polyweave.config import load

    mark = b"\xef\xbb\xbf"
    (tmp_path / "polyweave.toml").write_bytes(mark + b'[project]\nname = "game"\n')
    assert load(tmp_path).get("project.name") == "game"
    (tmp_path / "game.world.toml").write_bytes(
        mark + b'[entity.ada]\nname = "Ada"\nkind = "character"\n'
    )
    assert world.validate(root=str(tmp_path))["valid"]
    (tmp_path / "waves.json").write_bytes(
        mark + b'[{"second": 0, "weight": 1, "until": 2}]'
    )
    assert pressure.pressure(file="waves.json", root=str(tmp_path))["total"] == 1.0


DICT = {"name": "families", "type": "dict"}


def test_a_dict_flag_may_name_a_json_file(tmp_path):
    """§PW337: PowerShell eats an inline object's quotes, and @file was lists only."""
    where = tmp_path / "families.json"
    where.write_bytes(b"\xef\xbb\xbf" + b'{"stars": ["renders/star.png"]}')
    assert commands.parsed(f"@{where}", DICT) == {"stars": ["renders/star.png"]}


def test_a_dict_file_that_holds_a_list_is_refused_naming_it(tmp_path):
    where = tmp_path / "families.json"
    where.write_text('["renders/star.png"]', encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        commands.parsed(f"@{where}", DICT)
    assert refused.value.code == "op.bad-type"
    assert "holds a list" in refused.value.message


def test_a_dict_that_does_not_read_says_a_file_works(tmp_path):
    with pytest.raises(PolyweaveError) as refused:
        commands.parsed("{stars: [a]}", DICT)
    assert "@families.json" in refused.value.remedy


def test_one_plain_value_is_a_list_of_one():
    assert commands.parsed(["--boss"], LIST) == ["--boss"]


def test_a_list_the_shell_mangled_is_refused_naming_the_forms_that_survive():
    with pytest.raises(PolyweaveError) as refused:
        commands.parsed(["[--scene=x, --frames=45]"], LIST)
    assert refused.value.code == "op.bad-type"
    assert "once per item" in refused.value.remedy
    assert "@args.json" in refused.value.remedy


def test_a_repeated_flag_reaches_the_operation_through_the_parser():
    """What argparse hands over when the shell passes --args=… twice."""
    import argparse

    parser = argparse.ArgumentParser()
    commands.add_operations(parser.add_subparsers(dest="command"))
    stated = parser.parse_args(
        [
            "capture.run",
            "--script",
            "x.gd",
            "--expect",
            "SHOT",
            "--args=--boss",
            "--args=--frames=420",
        ]
    )
    assert commands.parsed(stated.args, LIST) == ["--boss", "--frames=420"]
    assert commands.parsed(stated.script, {"name": "script", "type": "str"}) == "x.gd"


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
