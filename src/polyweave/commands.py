"""The command line, derived from the registry rather than written beside it (§PW125).

`python -m polyweave` used to answer `build` and `verify` and nothing else, so an agent
in a GDScript project that wanted to know whether Blender was present wrote and ran a
script, and a person reading its transcript could not tell the question from the
answer. Every operation is registered now, and its declaration already says what a
subcommand needs: the name, each parameter's type, range, default and sentence, and
which are required. So there is one subcommand per operation, named as the operation
is, and a parameter added to an operation is a flag without a second edit:

    python -m polyweave accept.check --spec star.accept.toml --subject star.png
    python -m polyweave render.plan --asking '["saturation_p99"]' --json
    python -m polyweave search.sweep --spec star.accept.toml --out s.png --job

Beside them are the reads a caller starts from (`capabilities`, `explain`, `describe`)
and `job`, which answers for work started with `--job`.

**One answer, two renderings.** An operation returns data. `--json` prints it, and the
text is the same data flattened to `path: value` lines, so the text can never say
something the JSON lacks. Roadkeep paid forty commits to get there late; this starts
there.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from typing import Any

from .errors import PolyweaveError

#: The verbs that are not operations: the first reads, and the job handle's.
VERBS = ("capabilities", "explain", "describe", "job")

#: What `job` does with a handle.
JOB_ACTIONS = ("list", "poll", "result", "cancel")


class Quiet:
    """The report an injected parameter gets here: nobody is listening."""

    def stage(self, stage, *, progress=None, note=None):
        return None

    def progress(self, value, *, note=None):
        return None

    def note(self, text):
        return None


def parsed(text: str, declared: dict) -> Any:
    """One flag's value, read as the type its operation declared.

    A number, a flag or a structure is read as JSON, so `--at '[40, 8]'` is a list and
    `--preview true` a boolean. A string stays the text given, so a path is never
    mistaken for anything else. A value typed `any` is JSON where it reads as JSON and
    text where it does not, which is how a path and a table are both accepted there.
    """
    kind = declared["type"]
    if kind == "str":
        return text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if kind in ("any", "Any"):
            return text
        raise PolyweaveError(
            "op.bad-type",
            f"--{declared['name']} is a {kind}, and {text!r} does not read as one",
            f"pass it as JSON, such as {_example(kind)}",
        ) from None


def _example(kind: str) -> str:
    return {
        "int": "3",
        "float": "0.5",
        "bool": "true",
        "list": '["a", "b"]',
        "dict": '{"a": 1}',
    }.get(kind, '"text"')


def add_operations(commands: Any) -> None:
    """One subcommand per registered operation, and the verbs beside them."""
    from . import describe as D

    for found in D.describe():
        name = found["operation"]
        sub = commands.add_parser(name, help=found["summary"])
        for p in found["parameters"]:
            about = p["about"]
            if p.get("unit"):
                about += f" ({p['unit']})"
            if p.get("choices"):
                about += f"; one of {', '.join(map(str, p['choices']))}"
            sub.add_argument(
                f"--{p['name']}",
                dest=p["name"],
                required=p["required"],
                default=argparse.SUPPRESS,
                metavar=p["type"].upper(),
                help=about,
            )
        if found["asynchronous"]:
            sub.add_argument(
                "--job", action="store_true", help="start it as a job, print the handle"
            )
        sub.add_argument("--json", action="store_true", help="print the answer as data")

    capabilities = commands.add_parser("capabilities", help="what this machine can do")
    capabilities.add_argument("--root", default=".")
    capabilities.add_argument(
        "--no-probe", action="store_true", help="say where things are, run nothing"
    )
    capabilities.add_argument("--json", action="store_true")
    explain = commands.add_parser("explain", help="what an error code means")
    explain.add_argument("code", nargs="?", help="a code; every code where omitted")
    explain.add_argument("--json", action="store_true")
    described = commands.add_parser("describe", help="an operation's parameters")
    described.add_argument("operation", nargs="?", help="one; every one where omitted")
    described.add_argument("--json", action="store_true")
    job = commands.add_parser("job", help="answer for work started with --job")
    job.add_argument("action", choices=JOB_ACTIONS)
    job.add_argument("handle", nargs="?", help="the job, for all but list")
    job.add_argument("--root", default=".")
    job.add_argument("--wait", action="store_true", help="for result: wait for it")
    job.add_argument("--json", action="store_true")


def answer_for(stated: argparse.Namespace) -> Any:
    """What a subcommand answers, as data: the operation's own return, or the read's."""
    from . import describe as D

    if stated.command == "capabilities":
        from .capabilities import capabilities

        return capabilities(stated.root, probe=not stated.no_probe)
    if stated.command == "explain":
        from .errors import codes, explain

        return explain(stated.code) if stated.code else codes()
    if stated.command == "describe":
        return D.describe(stated.operation)
    if stated.command == "job":
        return _job(stated)

    registered = D._REGISTRY[stated.command]
    declared = {p["name"]: p for p in registered.parameters}
    given = {
        name: parsed(getattr(stated, name), declared[name])
        for name in declared
        if hasattr(stated, name)
    }
    args = D.validate(stated.command, given)
    if getattr(stated, "job", False):
        from .jobs import JobStore

        store = JobStore.for_project(args.get("root") or ".")
        return store.start(registered.target, kind=registered.kind, args=given)
    injected = {name: Quiet() for name in registered.injects}
    return registered.fn(**injected, **args)


def _job(stated: argparse.Namespace) -> Any:
    from .jobs import JobStore

    store = JobStore.for_project(stated.root)
    if stated.action == "list":
        return store.list()
    if not stated.handle:
        raise PolyweaveError(
            "op.missing-argument",
            f"job {stated.action} needs the handle --job printed",
            f"pass it: job {stated.action} <handle>",
        )
    if stated.action == "poll":
        return store.poll(stated.handle)
    if stated.action == "cancel":
        return store.cancel(stated.handle)
    return store.result(stated.handle, wait=stated.wait)


def as_data(answer: Any) -> Any:
    """The answer as JSON has it: a path is its text, a tuple a list."""
    return json.loads(json.dumps(answer, default=str))


def text_of(answer: Any) -> list[str]:
    """The answer as lines, each a JSON path and the value at it, and nothing else."""
    lines: list[str] = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict) and value:
            for key, one in value.items():
                walk(one, f"{path}.{key}" if path else str(key))
        elif isinstance(value, list) and value and not _flat(value):
            for index, one in enumerate(value):
                walk(one, f"{path}[{index}]")
        else:
            shown = json.dumps(value) if not isinstance(value, str) else value
            lines.append(f"{path}: {shown}" if path else shown)

    walk(as_data(answer), "")
    return lines


def _flat(value: list) -> bool:
    return all(not isinstance(one, dict | list) for one in value)


def run(stated: argparse.Namespace) -> int:
    """Answer one derived subcommand; a refusal is printed and exits 1."""
    try:
        # Anything the work prints (Blender's exporter logs to stdout) goes to stderr,
        # so stdout carries the answer alone.
        with contextlib.redirect_stdout(sys.stderr):
            answer = answer_for(stated)
    except PolyweaveError as refused:
        if stated.json:
            print(json.dumps({"refused": refused.as_dict()}, indent=1))
        else:
            print(f"{refused.code}: {refused.message}", file=sys.stderr)
            if refused.remedy:
                print(f"  do: {refused.remedy}", file=sys.stderr)
        return 1
    if stated.json:
        print(json.dumps(as_data(answer), indent=1))
    else:
        print("\n".join(text_of(answer)))
    return 0

