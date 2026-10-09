"""A Godot project that imports and parses clean, decided without playing it (§PW358).

Godot 4 refers to a resource by UID, and since 4.4 a script carries a `.uid` file beside
it. Moving a file without its `.uid`, or writing a `.tscn` as text, leaves a reference
that resolves to nothing until that scene loads, and a script that does not parse waits
the same way. An agent moves and writes files with no editor open, so it meets both, and
learnt of them from a person or a crash.

`engine.check` reads the tree as text first, which needs no engine:

- every UID the project declares: a `.uid` file beside its source, an `.import` file's
  remap, a scene's or resource's header;
- each `ext_resource`, each value in `project.godot` and each literal `res://` or
  `uid://` string in a script, held to a file that is there: one whose UID and path both
  resolve to nothing is `engine.broken-reference`; one whose UID resolves to a file that
  moved is `engine.moved-reference`, which `fix` repoints; one whose path is there but
  whose UID nothing declares is `engine.stale-uid`;
- a `.uid` or `.import` left without its source (`engine.orphan-uid`,
  `engine.orphan-import`, which `fix` removes), and an import older than its source
  (`engine.stale-import`, by the MD5 Godot keeps beside it);
- a path a script names that is not there is `engine.missing-path`, a warning only,
  since a script may name a file it reads where the project keeps one; the scripts under
  `addons/` are a plugin's or a kit's, which prove themselves, and are not read;
- each resource nothing refers to, as information, since a game may load one by a path
  it builds.

With an engine, it imports the project headless, which builds the class cache a script
that names another's `class_name` needs, and then parses every script, so each one that
does not parse is `engine.parse-error` with its line and Godot's own words.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Annotated

from .describe import Param, operation
from .errors import PolyweaveError

#: What Godot never imports or a project never keeps by hand.
_SKIP = {".godot", ".git", ".polyweave", "node_modules", ".import"}

#: The files a game refers to as resources, which an unreferenced one is counted among.
_RESOURCES = (".tscn", ".tres", ".gd", ".gdshader", ".png", ".jpg", ".jpeg", ".webp",
              ".svg", ".wav", ".ogg", ".mp3", ".glb", ".gltf", ".ttf", ".otf", ".res")

_UID = re.compile(r'uid="(uid://[a-z0-9]+)"')
_PATH = re.compile(r'path="(res://[^"]+)"')
_LITERAL = re.compile(r'"\*?((?:res|uid)://[^"%{}]*)"')
_SOURCE = re.compile(r'^source_file="(res://[^"]+)"', re.MULTILINE)
_PARSE = re.compile(
    r"SCRIPT ERROR: Parse Error: (?P<said>.+?)\s*\n\s*at: GDScript::reload "
    r"\((?P<file>res://[^:)]+):(?P<line>\d+)\)"
)

#: The calls a script tests a path against, whose argument is a prefix and not a file.
_TESTS = ("begins_with(", "ends_with(", "contains(", "find(")

#: The parser a project is held to: polyweave's own script, run from where it ships.
PARSER = Path(__file__).parent / "godot" / "parse_all.gd"


def _files(root: Path) -> list[Path]:
    out = []
    for path in sorted(root.rglob("*")):
        parts = path.relative_to(root).parts
        if any(p in _SKIP for p in parts) or not path.is_file():
            continue
        if any((root.joinpath(*parts[:i]) / ".gdignore").exists()
               for i in range(len(parts))):
            continue
        out.append(path)
    return out


def _res(path: Path, root: Path) -> str:
    return "res://" + path.relative_to(root).as_posix()


def _on_disk(res: str, root: Path) -> Path:
    return root / res.removeprefix("res://")


def _finding(code: str, file: str, line: int, said: str, remedy: str,
             severity: str = "warning", **fix: str) -> dict:
    return {"code": code, "file": file, "line": line, "said": said, "remedy": remedy,
            "severity": severity, **({"fix": fix} if fix else {})}


def scan(root: str | Path) -> dict:
    """What the tree says of itself, read as text: every finding but a parse error."""
    here = Path(root).resolve()
    files = _files(here)
    uids: dict[str, str] = {}
    found: list[dict] = []
    for path in files:
        res = _res(path, here)
        if path.suffix == ".uid":
            source = path.with_suffix("")
            uid = path.read_text(encoding="utf-8", errors="replace").strip()
            if source.exists():
                uids[uid] = _res(source, here)
            else:
                found.append(_finding(
                    "engine.orphan-uid", res, 1,
                    f"{res} names {_res(source, here)}, which is not there",
                    "remove it with engine.check fix=true, or put its file back",
                    remove=res))
        elif path.suffix == ".import":
            text = path.read_text(encoding="utf-8", errors="replace")
            source = _SOURCE.search(text)
            target = source[1] if source else _res(path.with_suffix(""), here)
            uid = _UID.search(text)
            if not _on_disk(target, here).exists():
                found.append(_finding(
                    "engine.orphan-import", res, 1,
                    f"{res} imports {target}, which is not there",
                    "remove it with engine.check fix=true, or put its source back",
                    remove=res))
                continue
            if uid:
                uids[uid[1]] = target
            found.extend(_stale(path, text, target, here))
        elif path.suffix in (".tscn", ".tres"):
            head = path.read_text(encoding="utf-8", errors="replace").split("\n", 1)[0]
            uid = _UID.search(head)
            if uid:
                uids[uid[1]] = res
    referred: set[str] = set()
    for path in files:
        if path.suffix in (".tscn", ".tres", ".gd") or path.name == "project.godot":
            found.extend(_references(path, here, uids, referred))
    unreferenced = [
        _res(p, here) for p in files
        if p.suffix in _RESOURCES and not _res(p, here).startswith("res://addons/")
        and _res(p, here) not in referred
        and not (p.suffix == ".gd" and "class_name" in p.read_text(
            encoding="utf-8", errors="replace"))
    ]
    return {"findings": found, "unreferenced": unreferenced, "uids": len(uids)}


def _stale(path: Path, text: str, target: str, here: Path) -> list[dict]:
    """An import whose source changed since Godot last imported it.

    Godot keeps the source's MD5 in `.godot/imported/<name>-<md5 of its path>.md5`,
    whatever the import made (a texture, or a CSV's one translation a locale).
    """
    imported = here / ".godot" / "imported"
    if not imported.is_dir():
        return []
    named = target.rsplit("/", 1)[-1]
    digest = hashlib.md5(target.encode()).hexdigest()  # noqa: S324
    kept = imported / f"{named}-{digest}.md5"
    was = (re.search(r'source_md5="([0-9a-f]+)"', kept.read_text(encoding="utf-8"))
           if kept.is_file() else None)
    now = hashlib.md5(_on_disk(target, here).read_bytes()).hexdigest()  # noqa: S324
    if was and was[1] == now:
        return []
    return [_finding("engine.stale-import", _res(path, here), 1,
                     f"{target} changed since Godot last imported it",
                     "import it again: engine.check imports where an engine is set")]


def _references(path: Path, here: Path, uids: dict, referred: set) -> list[dict]:
    res = _res(path, here)
    out = []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for number, line in enumerate(lines, 1):
        if path.suffix in (".tscn", ".tres") and line.startswith("[ext_resource"):
            uid = _UID.search(line)
            named = _PATH.search(line)
            out.extend(_resolve(res, number, uid[1] if uid else "",
                                named[1] if named else "", here, uids, referred))
            continue
        if path.suffix == ".gd" and (line.lstrip().startswith("#")
                                     or res.startswith("res://addons/")):
            continue
        for match in _LITERAL.finditer(line):
            literal = match[1]
            after = line[match.end():].lstrip()[:1]
            before = line[:match.start()].rstrip()
            # a prefix a script joins to more or tests a path against, or a pattern,
            # names no file of its own
            tested = before.endswith(_TESTS)
            if (literal in ("res://", "uid://") or after in ("+", "%") or tested
                    or any(c in literal for c in r"[]\^*()|?")
                    or any(f"/{skipped}" in literal for skipped in _SKIP)):
                continue
            on_path = literal.startswith("res://")
            uid, named = ("", literal) if on_path else (literal, "")
            said = _resolve(res, number, uid, named, here, uids, referred)
            if path.suffix == ".gd":
                # a script may name a file it reads only where the project keeps one
                said = [{**one, "code": "engine.missing-path", "severity": "warning",
                         "remedy": "point it at a file that is there, or check the "
                         "path exists before loading it"}
                        if one["code"] == "engine.broken-reference" else one
                        for one in said]
            out.extend(said)
    return out


def _resolve(res: str, line: int, uid: str, named: str, here: Path, uids: dict,
             referred: set) -> list[dict]:
    """One reference: there, moved, stale, or nothing at all."""
    at = uids.get(uid) if uid else None
    there = bool(named) and _on_disk(named, here).exists()
    for one in (at, named if there else None):
        if one:
            referred.add(one)
    if at and named and not there:
        return [_finding(
            "engine.moved-reference", res, line,
            f"{named} moved to {at}; Godot finds it by {uid} and warns on each load",
            "repoint it with engine.check fix=true", repoint=f"{named}>{at}")]
    if at or there:
        if uid and not at and named:
            return [_finding(
                "engine.stale-uid", res, line,
                f"{uid} is no UID the project declares, so Godot falls back to {named}",
                "open and save the scene in the editor, or drop the uid attribute")]
        return []
    said = f"{uid or named} resolves to nothing" + (
        f" ({named} is not there either)" if uid and named else "")
    return [_finding("engine.broken-reference", res, line, said,
                     "point it at the file as it is now, or put the file back",
                     severity="error")]


def _repair(here: Path, findings: list[dict]) -> list[str]:
    """Each fix a finding carries: a moved reference repointed, an orphan removed."""
    done = []
    for one in findings:
        fix = one.get("fix") or {}
        if "remove" in fix:
            _on_disk(fix["remove"], here).unlink(missing_ok=True)
            done.append(f"removed {fix['remove']}")
        elif "repoint" in fix:
            old, new = fix["repoint"].split(">")
            where = _on_disk(one["file"], here)
            lines = where.read_text(encoding="utf-8").split("\n")
            lines[one["line"] - 1] = lines[one["line"] - 1].replace(
                f'"{old}"', f'"{new}"')
            where.write_text("\n".join(lines), encoding="utf-8", newline="\n")
            done.append(f"{one['file']}:{one['line']} now points at {new}")
    return done


def parsed(root: str | Path, binary: str = "", timeout: float = 300.0) -> dict:
    """Every script that does not parse, after an import has built the class cache."""
    from . import engine

    here = Path(root).resolve()
    godot = binary or engine.find(here)
    imported, _ = engine._launch([godot, "--headless", "--import", "--path", str(here)],
                                 cwd=here, timeout=timeout)
    output, _ = engine._launch(
        [godot, "--headless", "--path", str(here), "--script", str(PARSER)],
        cwd=here, timeout=timeout)
    errors = [
        _finding("engine.parse-error", one["file"], int(one["line"]),
                 f"{one['file']}:{one['line']} does not parse: {one['said']}",
                 "fix the line Godot names; nothing loads the script until it parses",
                 severity="error")
        for one in _PARSE.finditer(output)
    ]
    checked = len(re.findall(r"^PARSED ", output, re.MULTILINE))
    return {"findings": errors, "scripts": checked}


@operation("engine.check")
def check(
    root: Annotated[str, Param("the Godot project: the folder of project.godot")] = ".",
    *,
    fix: Annotated[
        bool, Param("repoint moved references and remove orphaned .uid and .import")
    ] = False,
    parse: Annotated[
        bool, Param("import headless and parse every script, where an engine is set")
    ] = True,
) -> dict:
    """Every reference that resolves to nothing and every script that does not parse.

    Reads the tree as text: each `ext_resource`, `project.godot` value and literal
    `res://` or `uid://` in a script, held to a file that is there by its UID or path,
    each `.uid` and `.import` left without its source, and each import older than its
    source, every one with its file, line and remedy; `fix` applies the ones a call can.
    With an engine it imports headless and parses every script, each parse error with
    its line. `clean` is false while an error is left (§PW358).
    """
    from . import engine

    here = Path(root).resolve()
    if not (here / "project.godot").is_file():
        raise PolyweaveError(
            "engine.no-project",
            f"there is no project.godot at {here}, so no Godot project to check",
            "check the Godot project's own folder",
        )
    read = scan(here)
    fixed = _repair(here, read["findings"]) if fix else []
    if fixed:
        read = scan(here)
    findings = list(read["findings"])
    answer: dict = {"parsed": None}
    if parse:
        try:
            godot = engine.find(here)
        except PolyweaveError as refused:
            answer["parsed"] = {"skipped": refused.message}
        else:
            run = parsed(here, binary=godot)
            findings += run["findings"]
            answer["parsed"] = {"scripts": run["scripts"]}
    errors = sum(1 for f in findings if f["severity"] == "error")
    return {
        **answer,
        "clean": errors == 0,
        "errors": errors,
        "warnings": len(findings) - errors,
        "findings": findings,
        "fixed": fixed,
        "unreferenced": read["unreferenced"],
        "says": f"{errors} error(s), {len(findings) - errors} warning(s), "
        f"{len(read['unreferenced'])} resource(s) nothing refers to",
    }
