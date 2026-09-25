"""The specs read against the code (§PW138).

A name a spec spells that the code lacks, or the reverse, used to be found only by a
reader who checked both: `tool-surface.md` §3 named twelve error areas while the code
declared nineteen. For each kind of name a document may spell, one reader takes it out
of the documents and the code supplies the other side, and the test fails on either
difference.

Two rules keep the readers honest, after Shio's docs gate. Each reader is tested against
a fixture that plants a name only it can find, and a reader that finds nothing raises
instead of returning empty, because an empty population makes every check against it
pass.
"""

from __future__ import annotations

import importlib
import re
import shlex
import tomllib
from pathlib import Path

import pytest

from polyweave.cli import command_line
from polyweave.codes import AREAS
from polyweave.config import _FREE_TABLES, DEFAULTS
from polyweave.describe import describe, load
from polyweave.errors import codes
from polyweave.measure import COMPUTES, SUFFIXES
from polyweave.provenance import key_subset

ROOT = Path(__file__).resolve().parent.parent
SPECS = ROOT / "docs" / "specs"
SKILL = ROOT / "skills" / "polyweave"

#: A name a document spells ahead of its code, with the open line that builds it. Only
#: an open line may be named here; the test below refuses one that has shipped.
AHEAD: dict[str, str] = {}

#: What a backticked dotted token is when it is a file rather than a name.
_FILES = (".md", ".py", ".toml", ".json", ".gd", ".png", ".godot")


class NothingRead(AssertionError):
    """A reader found no names, so every check against it would pass."""


def _found(kind: str, names):
    names = sorted(set(names))
    if not names:
        raise NothingRead(
            f"the {kind} reader found nothing; it is reading the wrong text"
        )
    return names


def _documents() -> dict[str, str]:
    paths = sorted(SPECS.glob("*.md")) + sorted(SKILL.rglob("*.md"))
    return {
        p.relative_to(ROOT).as_posix(): p.read_text(encoding="utf-8") for p in paths
    }


# -- readers: each takes text and returns the names of one kind -------------------


def read_areas(text: str) -> list[str]:
    """The areas §3 says a code is namespaced by: `(`render.`, `mesh.`, …)`."""
    listed = re.search(r"namespaced by area \(([^)]*)\)", text)
    spelled = re.findall(r"`([a-z]+)\.`", listed.group(1)) if listed else []
    return _found("area", spelled)


def _dotted(text: str) -> list[str]:
    spelled = re.findall(r"`([a-z_]+\.[a-z0-9_.-]*[a-z0-9_])[`( ]", text)
    return [n for n in spelled if not n.endswith(_FILES)]


def read_dotted(text: str) -> list[str]:
    """Every backticked `a.b` name that is not a file: operations, codes, functions."""
    return _found("dotted-name", _dotted(text))


def read_measures(text: str) -> tuple[list[str], list[str]]:
    """The vocabulary table's names, and the statistic suffixes it spells."""
    rows = re.findall(r"^\| `([a-z_]+?)(?:_\{([a-z0-9,]+)\})?` \|", text, re.M)
    names = _found("measure", (name for name, _ in rows))
    suffixes = _found(
        "suffix", (s for _, group in rows if group for s in group.split(","))
    )
    return names, suffixes


def read_config(text: str) -> list[str]:
    """`table.key` for every key the first TOML example declares."""
    block = re.search(r"```toml\n(.*?)```", text, re.S)
    declared = tomllib.loads(block.group(1)) if block else {}
    return _found(
        "config-key",
        (
            f"{t}.{k}"
            for t, keys in declared.items()
            if isinstance(keys, dict)
            for k in keys
        ),
    )


def read_key(text: str) -> list[str]:
    """The fields the cache key is computed over, from **In the key:** to its first `and
    every`."""
    listed = re.search(r"\*\*In the key:\*\*(.*?)every `", text, re.S)
    spelled = re.findall(r"`([a-z_.]+)`", listed.group(1)) if listed else []
    return _found("key-field", (n.replace(".", "_") for n in spelled))


def _commands(text: str) -> list[str]:
    spelled = re.findall(r"python -m polyweave ([^`\n]+)", text)
    # `<op>` and `--<param> <value>` are the form described, not a command to run.
    return [s.strip() for s in spelled if "<" not in s]


def read_commands(text: str) -> list[str]:
    """Every `python -m polyweave …` a document spells, up to the closing backtick or
    the end of its line."""
    return _found("command", _commands(text))


# -- the readers find what is planted, and refuse to find nothing -----------------

PLANTED = {
    read_areas: ("namespaced by area (`zeta.`, `render.`)", ["render", "zeta"]),
    read_dotted: ("run `zeta.probe` or `zeta.md`", ["zeta.probe"]),
    read_config: ("```toml\n[zeta]\nprobe = 1\n```", ["zeta.probe"]),
    read_key: ("**In the key:** `zeta.probe`, and every `x`", ["zeta_probe"]),
    read_commands: ("`python -m polyweave zeta --probe`", ["zeta --probe"]),
}


@pytest.mark.parametrize("reader", list(PLANTED), ids=lambda r: r.__name__)
def test_each_reader_finds_what_was_planted(reader):
    text, expected = PLANTED[reader]
    assert reader(text) == expected


def test_the_measure_reader_finds_a_planted_name_and_its_suffixes():
    assert read_measures("| `zeta_{p1,p9}` | 0–1 | a planted row |") == (
        ["zeta"],
        ["p1", "p9"],
    )


@pytest.mark.parametrize("reader", [*PLANTED, read_measures], ids=lambda r: r.__name__)
def test_a_reader_that_finds_nothing_raises(reader):
    with pytest.raises(NothingRead):
        reader("prose that names nothing any reader looks for")


# -- the documents against the code -----------------------------------------------


def _resolves(name: str, operations: set[str], declared: set[str]) -> bool:
    """An operation, a declared code, a key field, or an attribute of the package."""
    if name in operations or name in declared or name in AHEAD:
        return True
    if name.replace(".", "_") in key_subset({}):
        return True
    head, *rest = name.split(".")
    try:
        found = importlib.import_module(f"polyweave.{head}")
    except ImportError:
        return False
    for part in rest:
        if not hasattr(found, part):
            return False
        found = getattr(found, part)
    return True


def test_the_areas_the_spec_lists_are_the_areas_the_code_declares():
    spelled = read_areas((SPECS / "tool-surface.md").read_text(encoding="utf-8"))
    assert spelled == sorted(AREAS)


def test_every_dotted_name_a_document_spells_exists():
    load()
    operations = {one["operation"] for one in describe()}
    spaces = {name.split(".")[0] for name in operations} | set(AREAS)
    declared = set(codes())
    spelled = [
        (where, name) for where, text in _documents().items() for name in _dotted(text)
    ]
    _found("dotted-name", (name for _, name in spelled))
    missing = [
        f"{where}: {name}"
        for where, name in spelled
        if name.split(".")[0] in spaces and not _resolves(name, operations, declared)
    ]
    assert missing == []


def test_every_operation_is_named_in_the_skill():
    load()
    listed = set(
        read_dotted((SKILL / "references" / "operations.md").read_text("utf-8"))
    )
    registered = {one["operation"] for one in describe()}
    assert sorted(registered - listed) == []


def test_a_name_spelled_ahead_of_its_code_waits_on_an_open_line():
    changelog = (ROOT / "docs" / "CHANGELOG.md").read_text(encoding="utf-8")
    shipped = set(re.findall(r"\*\*(PW\d+)\*\*", changelog))
    assert {name: line for name, line in AHEAD.items() if line in shipped} == {}


def test_the_measures_spec_is_the_vocabulary():
    names, suffixes = read_measures((SPECS / "measurements.md").read_text("utf-8"))
    assert names == sorted(COMPUTES)
    assert suffixes == sorted(s.lstrip("_") for s in SUFFIXES)


def test_the_config_example_declares_every_key_and_only_those():
    spelled = read_config((SPECS / "project-config.md").read_text(encoding="utf-8"))
    known = sorted(f"{t}.{k}" for t, keys in DEFAULTS.items() for k in keys)
    # A free table takes the project's own keys, so the example may add one there.
    free = tuple(f"{t}." for t in _FREE_TABLES)
    assert [k for k in spelled if k not in known and not k.startswith(free)] == []
    assert [k for k in known if k not in spelled] == []


def test_the_cache_key_spec_is_the_key():
    spelled = read_key((SPECS / "provenance.md").read_text(encoding="utf-8"))
    computed = sorted(set(key_subset({})) - {"inputs", "params"})
    assert spelled == computed


def test_every_command_a_document_spells_parses():
    spelled = [
        (where, line)
        for where, text in _documents().items()
        for line in _commands(text)
    ]
    _found("command", (line for _, line in spelled))
    refused = []
    for where, line in spelled:
        try:
            command_line().parse_args(shlex.split(line))
        except SystemExit:
            refused.append(f"{where}: python -m polyweave {line}")
    assert refused == []
