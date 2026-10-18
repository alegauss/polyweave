"""`python -m polyweave migrate`: a project carried across the layout break (§PW520).

Block W broke code and config on purpose and kept data. A project's provenance records
name only a tool and a version, never a module path, so they cross unchanged, and so do
its specs, canon, verdicts and ledgers. What does not cross is the project's own Python,
whose imports name modules that moved, and its `polyweave.toml`, which needs `[layers]
on`. Spinhold's `tools/site_assets.py` died on ImportError the day the split landed and
was fixed by hand; this is the one command that replaces that hand.

The moves are data, in `moved.toml` beside this file: old module to new, the few public
names that left their module, and any renamed table. An import that resolves in the
installed package is left alone, so a second run changes nothing; one the table cannot
map is named under `unmapped` with its line and never guessed at, and the answer is then
not clean.

By default it reports a diff and writes nothing. `--write` applies it: the imports, the
`[layers] on` table where the file has none, the renamed tables, and it clears the work
area's `jobs` and `cache`, whose keys name the old version. It never touches a
provenance record, a verdict or a canon. A record whose kind no layer declares is
reported as unreadable, and left as it is.
"""

from __future__ import annotations

import ast
import difflib
import functools
import json
import os
import re
import shutil
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import polyweave
from polyweave.kernel.config import FILENAME, _check
from polyweave.kernel.files import read_text_retrying, write_atomic

#: Folders a project's own Python is never in.
SKIPPED = {"node_modules", "venv", "site-packages", "__pycache__", "build", "dist"}

#: The documents an agent reads, where a module path it would act on is reported.
DOCUMENTS = ("*.md",)


@functools.cache
def table() -> dict:
    """The moves, as `moved.toml` states them."""
    return tomllib.loads((Path(__file__).parent / "moved.toml").read_text("utf-8"))


@functools.cache
def _package() -> Path:
    return Path(polyweave.__file__).resolve().parent


@functools.cache
def _file_of(module: str) -> Path | None:
    """The source of a module in the installed package, or None where there is none."""
    if module != "polyweave" and not module.startswith("polyweave."):
        return None
    parts = module.split(".")[1:]
    base = _package().joinpath(*parts)
    if (base / "__init__.py").is_file():
        return base / "__init__.py"
    if base.with_suffix(".py").is_file():
        return base.with_suffix(".py")
    return None


@functools.cache
def _names(module: str) -> frozenset[str] | None:
    """What a module binds at its top level, or None where any name may be (it has a
    module `__getattr__`) or the module is not there."""
    source = _file_of(module)
    if source is None:
        return frozenset()
    tree = ast.parse(source.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            if node.name == "__getattr__":
                return None
            found.add(node.name)
        elif isinstance(node, ast.Assign | ast.AnnAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            found.update(t.id for t in targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.Import | ast.ImportFrom):
            found.update((a.asname or a.name).split(".")[0] for a in node.names)
    return frozenset(found)


def is_module(module: str) -> bool:
    return _file_of(module) is not None


def holds(module: str, name: str) -> bool:
    """Whether `from module import name` resolves in the installed package."""
    if not is_module(module):
        return False
    if is_module(f"{module}.{name}"):
        return True
    names = _names(module)
    return names is None or name in names


def _old(module: str) -> str | None:
    """The module's path under `polyweave.`, as the table keys it."""
    if module == "polyweave":
        return ""
    if module.startswith("polyweave."):
        return module[len("polyweave."):]
    return None


def moved(module: str) -> str | None:
    """Where an old module path lives now, by its longest moved prefix; None where no
    prefix moved."""
    old = _old(module)
    if not old:
        return None
    modules = table()["modules"]
    parts = old.split(".")
    for cut in range(len(parts), 0, -1):
        key = ".".join(parts[:cut])
        if key in modules:
            return ".".join([modules[key], *parts[cut:]])
    return None


def place(module: str, name: str) -> tuple[str, str] | None:
    """Where `from module import name` resolves now, as (module, name), or None."""
    if holds(module, name) and not (
        module == "polyweave" and name in table()["modules"]
    ):
        return module, name
    old = _old(module)
    if old is None:
        return None
    if old and f"{old}:{name}" in table()["names"]:
        return table()["names"][f"{old}:{name}"], name
    submodule = moved(f"{module}.{name}")
    if submodule and is_module(submodule):
        parent, leaf = submodule.rsplit(".", 1)
        return parent, leaf
    now = moved(module)
    if now and holds(now, name):
        return now, name
    return None


@dataclass
class Rewrite:
    """One file's changes, and what in it could not be mapped."""

    path: Path
    text: str
    now: str
    imports: list[dict] = field(default_factory=list)
    unmapped: list[dict] = field(default_factory=list)


def _alias(name: str, leaf: str, asname: str | None) -> str:
    said = asname or (name if leaf != name else None)
    return f"{leaf} as {said}" if said and said != leaf else leaf


def _from_lines(groups: dict[str, list[str]], indent: str) -> list[str]:
    lines = []
    for module, names in groups.items():
        one = f"{indent}from {module} import {', '.join(names)}"
        if len(one) <= 88:
            lines.append(one)
        else:
            lines += [f"{indent}from {module} import ("]
            lines += [f"{indent}    {name}," for name in names]
            lines += [f"{indent})"]
    return lines


def _statement(node: ast.stmt, indent: str) -> tuple[list[str] | None, list[str],
                                                       dict[str, str]]:
    """The lines an import becomes (None where it stays), the names it could not
    place, and the dotted paths whose uses in the file follow it."""
    if isinstance(node, ast.ImportFrom):
        if node.level or not node.module or _old(node.module) is None:
            return None, [], {}
        groups: dict[str, list[str]] = {}
        missing: list[str] = []
        changed = False
        for alias in node.names:
            found = place(node.module, alias.name)
            if found is None:
                missing.append(alias.name)
                found = (node.module, alias.name)
            module, leaf = found
            changed |= (module, leaf) != (node.module, alias.name)
            groups.setdefault(module, []).append(_alias(alias.name, leaf, alias.asname))
        if missing or not changed:
            return None, missing, {}
        return _from_lines(groups, indent), [], {}
    if isinstance(node, ast.Import):
        lines, missing, follow = [], [], {}
        changed = False
        for alias in node.names:
            name = alias.name
            if _old(name) is None or is_module(name):
                lines.append(_alias(name, name, alias.asname))
                continue
            now = moved(name)
            if not now or not is_module(now):
                missing.append(name)
                lines.append(_alias(name, name, alias.asname))
                continue
            changed = True
            lines.append(f"{now} as {alias.asname}" if alias.asname else now)
            if not alias.asname:
                follow[name] = now
        if missing or not changed:
            return None, missing, {}
        return [f"{indent}import {one}" for one in lines], [], follow
    return None, [], {}


def rewrite(path: Path, root: Path) -> Rewrite | None:
    """One Python file's imports carried across; None where none is polyweave's."""
    text = read_text_retrying(path)
    if text is None or "polyweave" not in text:
        return None
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    lines = text.splitlines(keepends=True)
    shown = path.relative_to(root).as_posix()
    done = Rewrite(path, text, text)
    edits: list[tuple[int, int, list[str]]] = []
    follow: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Import | ast.ImportFrom):
            continue
        first = lines[node.lineno - 1]
        indent = first[: len(first) - len(first.lstrip())]
        was = "".join(lines[node.lineno - 1: node.end_lineno]).strip()
        new, missing, followed = _statement(node, indent)
        for name in missing:
            done.unmapped.append({"file": shown, "line": node.lineno, "import": was,
                                  "name": name})
        if new is None:
            continue
        last = lines[node.end_lineno - 1]
        tail = last[node.end_col_offset:].rstrip("\r\n")
        if tail.strip():
            new[-1] += tail
        edits.append((node.lineno - 1, node.end_lineno, new))
        follow.update(followed)
        done.imports.append({"file": shown, "line": node.lineno, "was": was,
                             "now": "\n".join(one.strip() for one in new)})
    if edits:
        ending = "\r\n" if "\r\n" in text else "\n"
        out = list(lines)
        for start, end, new in sorted(edits, reverse=True):
            out[start:end] = [one + ending for one in new]
        now = "".join(out)
        for old, new in follow.items():
            # `import polyweave.x` is used as `polyweave.x.f()`, so the uses follow.
            now = re.sub(rf"(?<![\w.]){re.escape(old)}(?=\.)", new, now)
        done.now = now
    done.unmapped += _attributes(ast.parse(done.now), shown)
    return done if edits or done.unmapped else None


def _attributes(tree: ast.Module, shown: str) -> list[dict]:
    """Each `module.name` a file reaches through a polyweave module it imports, where
    the module no longer holds the name: an import that resolves can still be used
    for a function that left it."""
    bound: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for alias in node.names:
                module = f"{node.module}.{alias.name}"
                if _old(module) is not None and is_module(module):
                    bound[alias.asname or alias.name] = module
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname and _old(alias.name) is not None:
                    bound[alias.asname] = alias.name
    found, seen = [], set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                and node.value.id in bound):
            module = bound[node.value.id]
            if holds(module, node.attr) or (module, node.attr) in seen:
                continue
            seen.add((module, node.attr))
            found.append({"file": shown, "line": node.lineno,
                          "import": f"{node.value.id} is {module}",
                          "name": f"{node.value.id}.{node.attr}"})
    return found


def _walk(root: Path, patterns: tuple[str, ...]):
    """The project's own files, leaving out hidden folders and other checkouts."""
    for folder, dirs, files in os.walk(root):
        here = Path(folder)
        if here != root and (here / ".git").exists():
            dirs[:] = []
            continue
        dirs[:] = sorted(
            d for d in dirs
            if d not in SKIPPED and (not d.startswith(".") or d == ".claude")
        )
        for name in sorted(files):
            if any(Path(name).match(one) for one in patterns):
                yield here / name


#: A dotted module path as a document names it.
PATH = re.compile(r"(?<![\w.])polyweave(?:\.[A-Za-z_]\w*)+")


def mentions(root: Path) -> list[dict]:
    """Each moved module path an agent's documents name, and where it is now.

    Reported and never rewritten: prose names a path for a reason the table cannot
    read, and `polyweave.toml` is a file, not a module.
    """
    found = []
    for path in _walk(root, DOCUMENTS):
        text = read_text_retrying(path) or ""
        for number, line in enumerate(text.splitlines(), 1):
            for match in PATH.finditer(line):
                named = match.group(0)
                now = None if is_module(named) else moved(named)
                if now and is_module(now):
                    found.append({"file": path.relative_to(root).as_posix(),
                                  "line": number, "was": named, "now": now})
    return found


def _layers_for(root: Path, declared: dict, imported: set[str]) -> dict:
    """The layers the project uses: what `project.init` reads in the tree, the owner
    of every table the file holds, and the layer of every module its Python imports."""
    from polyweave.kernel.config import _schema
    from polyweave.kernel.layer import layer_of, layers

    from .project import _signals, proposed

    because = dict(_signals(root, {**proposed(root), **declared}))
    owner = _schema().owner
    for one in declared:
        if owner.get(one):
            because.setdefault(owner[one], f"the file's [{one}] table")
    for module in sorted(imported):
        named = layer_of(module)
        if named:
            because.setdefault(named, f"its Python imports {module}")
    every = sorted(layers())
    return {
        "on": [one for one in every if one in because],
        "because": dict(sorted(because.items())),
    }


def _with_layers(text: str, on: list[str]) -> str:
    """The file with `[layers] on` written after `[project]`, comments kept with the
    table they sit above."""
    lines = text.splitlines(keepends=True)
    ending = "\r\n" if "\r\n" in text else "\n"
    block = [
        "[layers]" + ending,
        "# What this project makes, written by `python -m polyweave migrate` from its"
        + ending,
        "# tree, its tables and its imports. A layer left off serves no tools here."
        + ending,
        "on = [" + ", ".join(json.dumps(one) for one in on) + "]" + ending,
        ending,
    ]
    headers = [n for n, line in enumerate(lines) if re.match(r"\s*\[", line)]
    project = next(
        (n for n in headers if re.match(r"\s*\[project\]", lines[n])), None
    )
    after = [n for n in headers if project is None or n > project]
    if not after:
        tail = "" if not lines or lines[-1].endswith(("\n", "\r")) else ending
        return text + tail + ending + "".join(block[:-1])
    at = after[0]
    while at - 1 > (project if project is not None else -1) and lines[
            at - 1].lstrip().startswith("#"):
        at -= 1
    return "".join(lines[:at] + block + lines[at:])


def _renamed(text: str) -> tuple[str, list[dict]]:
    """The file with each renamed table under its new name."""
    found = []
    for old, new in table()["tables"].items():
        pattern = rf"^(\s*\[+\s*){re.escape(old)}(?=[\].])"
        if re.search(pattern, text, re.M):
            text = re.sub(pattern, rf"\g<1>{new}", text, flags=re.M)
            found.append({"was": old, "now": new})
    return text, found


def _unreadable(root: Path) -> list[dict]:
    """Each provenance record whose kind no layer declares, left as it is."""
    from polyweave.kernel.provenance import SUFFIX, _own, kinds

    known = set(kinds())
    found = []
    for path in _own(root)[0]:
        if not path.name.endswith(SUFFIX):
            continue
        try:
            kind = json.loads(path.read_text(encoding="utf-8")).get("kind")
        except (OSError, ValueError, AttributeError):
            kind = None
        if kind not in known:
            found.append({"record": path.relative_to(root).as_posix(), "kind": kind})
    return found


def _diff(path: str, before: str, after: str) -> str:
    return "".join(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        f"a/{path}", f"b/{path}",
    ))


def migrate(root: str | Path = ".", write: bool = False) -> dict:
    """Carry a project's imports and polyweave.toml across the layout break."""
    here = Path(root).expanduser().resolve()
    files = [one for one in (rewrite(p, here) for p in _walk(here, ("*.py",))) if one]
    diffs = [_diff(f.path.relative_to(here).as_posix(), f.text, f.now)
             for f in files if f.now != f.text]
    imported = {
        node.module
        for f in files
        for node in ast.walk(ast.parse(f.now))
        if isinstance(node, ast.ImportFrom) and node.module
    } | {
        alias.name
        for f in files
        for node in ast.walk(ast.parse(f.now))
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    config: dict = {"file": FILENAME, "layers": None, "tables": []}
    target = here / FILENAME
    before = read_text_retrying(target)
    after = before
    work = here / ".polyweave"
    if before is not None:
        after, config["tables"] = _renamed(before)
        declared = tomllib.loads(after)
        if "layers" not in declared:
            config["layers"] = _layers_for(here, declared, imported)
            if config["layers"]["on"]:
                after = _with_layers(after, config["layers"]["on"])
        _check(tomllib.loads(after), target)
        stated = (declared.get("paths") or {}).get("work")
        work = here / stated if stated else work
        if after != before:
            diffs.append(_diff(FILENAME, before, after))
    clearing = [
        (work / one).relative_to(here).as_posix()
        for one in ("jobs", "cache") if (work / one).is_dir()
    ]
    unmapped = [one for f in files for one in f.unmapped]
    if write:
        for one in files:
            if one.now != one.text:
                write_atomic(one.path, one.now)
        if after is not None and after != before:
            write_atomic(target, after)
        for one in clearing:
            shutil.rmtree(here / one, ignore_errors=True)
    changes = len(diffs)
    says = (
        f"{changes} file(s) {'rewritten' if write else 'to rewrite'}"
        + (f", {len(unmapped)} import(s) the table cannot map" if unmapped else "")
        + ("" if write or not changes else "; pass --write to apply it")
    )
    return {
        "root": str(here),
        "wrote": write and bool(changes or clearing),
        "clean": not unmapped,
        "says": says,
        "imports": [one for f in files for one in f.imports],
        "unmapped": unmapped,
        "config": config,
        "cleared" if write else "clears": clearing,
        "mentions": mentions(here),
        "unreadable": _unreadable(here),
        "diff": "".join(diffs),
    }
