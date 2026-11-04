"""A game's level files held to the project's own schema and its world (§PW203).

Both consumers already keep levels as data: Cottony's JSON written from a curve,
Spinhold's `*.waves.toml` read by the game. What neither had was a check before the
engine sees a level. The project declares its schema, never polyweave, since a wave
and a goal are a genre's words:

    [levels]
    schema = "data/level.schema.json"
    files  = ["game/waves/phase_*.waves.toml"]

The schema is JSON Schema, in the part of it a level needs: `type`, `properties`,
`required`, `additionalProperties`, `items`, `enum`, `minimum`, `maximum`, `minItems`
and `maxItems`. A keyword outside that is refused rather than ignored, because a check
that skips what it does not read passes what it never checked. `"x-entity": true` on a
string says it names one of the world's entities (`docs/specs/world.md`), so a wave
spawning an enemy the world never declared is found here, with its place.
"""

from __future__ import annotations

import difflib
import json
import re
import tomllib
from pathlib import Path
from typing import Annotated, Any

from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError

#: The keywords read; any other is refused.
KEYWORDS = frozenset({
    "type", "properties", "required", "additionalProperties", "items", "enum",
    "minimum", "maximum", "minItems", "maxItems", "x-entity", "x-unit", "x-step",
    "$schema", "$id", "title", "description", "default", "examples",
})
TYPES = {"object": dict, "array": list, "string": str, "boolean": bool,
         "integer": int, "number": (int, float), "null": type(None)}


def _no_schema(what: str, remedy: str, **extra: Any) -> PolyweaveError:
    return PolyweaveError("level.no-schema", what, remedy, **extra)


def _checked(node: Any, at: str = "#") -> None:
    """Refuse a schema this cannot read in full, naming where."""
    if not isinstance(node, dict):
        raise _no_schema(f"the schema at {at} is not an object",
                         "write each schema as a JSON object")
    unknown = sorted(set(node) - KEYWORDS)
    if unknown:
        raise _no_schema(
            f"the schema at {at} uses {', '.join(unknown)}, which level.validate does "
            "not read", f"use only {', '.join(sorted(KEYWORDS))}", given=unknown[0])
    kinds = node.get("type")
    for kind in kinds if isinstance(kinds, list) else [kinds] if kinds else []:
        if kind not in TYPES:
            raise _no_schema(f"the schema at {at} has type {kind!r}",
                             f"use one of {', '.join(TYPES)}", given=str(kind))
    for name, child in (node.get("properties") or {}).items():
        _checked(child, f"{at}/properties/{name}")
    if isinstance(node.get("items"), dict):
        _checked(node["items"], f"{at}/items")
    if isinstance(node.get("additionalProperties"), dict):
        raise _no_schema(f"the schema at {at} gives additionalProperties a schema",
                         "write additionalProperties as true or false")


def _is(value: Any, kind: str) -> bool:
    if isinstance(value, bool) and kind in ("integer", "number"):
        return False
    if kind == "integer" and isinstance(value, float):
        return value.is_integer()
    return isinstance(value, TYPES[kind])


def _place(at: str, key: Any) -> str:
    return f"{at}[{key}]" if isinstance(key, int) else (f"{at}.{key}" if at else key)


def _held(value: Any, schema: dict, entities: set | None, at: str = "") -> list[dict]:
    """Every place a value breaks its schema, each with what it said."""
    out: list[dict] = []

    def said(words: str, where: str = at) -> None:
        out.append({"at": where or "(the file)", "said": words})

    kinds = schema.get("type")
    kinds = kinds if isinstance(kinds, list) else [kinds] if kinds else []
    if kinds and not any(_is(value, kind) for kind in kinds):
        said(f"{json.dumps(value)[:60]} is no {' or '.join(kinds)}")
        return out
    if "enum" in schema and value not in schema["enum"]:
        said(f"{value!r} is none of {schema['enum']}")
    if isinstance(value, int | float) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            said(f"{value} is under its least, {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            said(f"{value} is over its most, {schema['maximum']}")
    if schema.get("x-entity") and isinstance(value, str) and entities is not None \
            and value not in entities:
        near = difflib.get_close_matches(value, sorted(entities), n=1)
        said(f"{value!r} is no entity the world declares"
             + (f"; did you mean {near[0]!r}?" if near else ""))
    if isinstance(value, dict):
        properties = schema.get("properties") or {}
        for name in schema.get("required") or []:
            if name not in value:
                said(f"{name} is required and missing")
        for name, child in value.items():
            if name in properties:
                out += _held(child, properties[name], entities, _place(at, name))
            elif schema.get("additionalProperties") is False:
                said(f"{name} is no key the schema declares", _place(at, name))
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            said(f"{len(value)} item(s), under its least, {schema['minItems']}")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            said(f"{len(value)} item(s), over its most, {schema['maxItems']}")
        if isinstance(schema.get("items"), dict):
            for index, item in enumerate(value):
                out += _held(item, schema["items"], entities, _place(at, index))
    return out


def _uses_entities(node: dict) -> bool:
    if node.get("x-entity"):
        return True
    children = list((node.get("properties") or {}).values())
    if isinstance(node.get("items"), dict):
        children.append(node["items"])
    return any(_uses_entities(child) for child in children)


def _read(path: Path) -> Any:
    text = path.read_text(encoding="utf-8-sig")
    return json.loads(text) if path.suffix.lower() == ".json" else tomllib.loads(text)


def _schema(here: Path, table: dict) -> tuple[str, dict]:
    named = str(table.get("schema") or "")
    if not named:
        raise _no_schema("polyweave.toml declares no [levels] schema",
                         'write [levels] schema = "data/level.schema.json", a JSON '
                         "Schema for one level file")
    try:
        schema = json.loads((here / named).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise _no_schema(f"{named} is not a JSON file to read",
                         "write the schema as JSON at that path",
                         detail=str(exc)) from exc
    _checked(schema)
    return named, schema


def _findings(paths: list[Path], schema: dict, here: Path) -> list[dict]:
    entities = None
    if _uses_entities(schema):
        from polyweave.layers.words import world

        entities = set(world.declared(None, here)[1])
    findings = []
    for path in paths:
        name = path.relative_to(here).as_posix()
        try:
            value = _read(path)
        except (ValueError, tomllib.TOMLDecodeError) as exc:
            findings.append({"file": name, "at": "(the file)",
                             "said": f"not readable: {exc}"})
            continue
        findings += [{"file": name, **one} for one in _held(value, schema, entities)]
    return findings


def _filled(text: str, source: Path, out: Path | None, here: Path) -> str:
    rel = source.relative_to(here)
    return text.format(source=rel.as_posix(), dir=rel.parent.as_posix(),
                       stem=source.stem, out=out.relative_to(here).as_posix()
                       if out else "")


@operation("level.compile")
def compile_level(
    level: Annotated[str, Param("the level source to compile, under the project")],
    root: Annotated[str, Param("the project whose level this is")] = ".",
) -> dict:
    """Turn one level source into the file the game loads, checked and recorded.

    Holds the source to `[levels] schema` first and refuses it with its findings. Then
    runs `[levels] compile`, the project's own command with `{source}` and `{out}`
    filled in, and holds it to writing `[levels] out`. The record names the source,
    the schema and the command, each file it names with its digest. With no command
    the source is what the game loads, and only the record is written (§PW203).
    """
    import hashlib
    import subprocess

    from polyweave.kernel import provenance

    config = load(root)
    here = config.root
    table = config.table("levels")
    named, schema = _schema(here, table)
    source = here / level
    if not source.is_file():
        raise PolyweaveError("level.no-level", f"there is no level at {level}",
                             "name the level source as a path under the project",
                             given=level)
    findings = _findings([source], schema, here)
    if findings:
        first = findings[0]
        raise PolyweaveError(
            "level.invalid",
            f"{level} breaks its schema in {len(findings)} place(s), the first "
            f"{first['at']}: {first['said']}",
            "fix each place level.validate names, then compile again",
            detail=findings)
    command = [str(one) for one in table.get("compile") or []]
    target = source
    ran: dict = {}
    if command:
        template = str(table.get("out") or "")
        if not template:
            raise PolyweaveError(
                "level.compile-failed", "[levels] compile is declared with no out",
                'write [levels] out = "{dir}/{stem}.json", where the command writes')
        target = here / _filled(template, source, None, here)
        argv = [_filled(one, source, target, here) for one in command]
        before = target.stat().st_mtime_ns if target.is_file() else None
        done = subprocess.run(  # noqa: S603 - the project's own declared command
            argv, cwd=here, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=float(table.get("timeout", 120)), check=False)
        wrote = target.is_file() and target.stat().st_mtime_ns != before
        if done.returncode != 0 or not wrote:
            raise PolyweaveError(
                "level.compile-failed",
                f"{' '.join(argv)} " + (f"exited {done.returncode}" if done.returncode
                                        else f"wrote nothing at {target.name}"),
                "run the command by hand on the source and read what it says",
                detail=(done.stderr or done.stdout)[-2000:])
        ran = {"command": argv, "exit": done.returncode}
    inputs = [provenance.source("level", source, root=here)] if command else []
    inputs.append(provenance.source("schema", here / named, root=here))
    inputs += [provenance.source("compiler", here / one, root=here)
               for one in command if (here / one).is_file()]
    provenance.write(provenance.build(
        "level", target, inputs=inputs,
        params={"compile": command, "command_sha256": hashlib.sha256(
            "\0".join(command).encode()).hexdigest()[:16]},
        root=here), root=here)
    loaded = provenance.relative(target, here)
    return {
        "compiled": loaded,
        **ran,
        "says": f"{level} holds its schema and compiled to {loaded}" if command
        else f"{level} holds its schema and is what the game loads; recorded",
    }


#: What a field says of itself to a game's tools, from the keyword it is read off.
_SAID = (("type", "type"), ("minimum", "min"), ("maximum", "max"), ("x-step", "step"),
         ("x-unit", "unit"), ("default", "default"), ("enum", "choices"),
         ("description", "help"), ("x-entity", "entity"))


def _fields(node: dict, at: str = "", required: bool = False) -> list[dict]:
    """Every field a schema declares, its dotted path (`[]` for a list's items) and
    what a tool needs of it, in the schema's own order (§PW608)."""
    out = []
    if at:
        one = {"path": at, "required": required}
        one.update({name: node[key] for key, name in _SAID if key in node})
        if "help" in one:
            # The key its help is shown by in every locale (§PW683).
            one["help_key"] = "LEVEL_" + "_".join(
                part for part in re.split(r"[^A-Za-z0-9]+", at.upper()) if part) \
                + "_HELP"
        out.append(one)
    wanted = set(node.get("required") or [])
    for name, child in (node.get("properties") or {}).items():
        out += _fields(child, f"{at}.{name}" if at else name, name in wanted)
    if isinstance(node.get("items"), dict):
        out += _fields(node["items"], f"{at}[]", False)
    return out


@operation("level.fields")
def fields(
    out: Annotated[str, Param("where to write them as JSON, under the project; "
                              "nowhere if empty")] = "",
    strings: Annotated[
        bool, Param("add each help's key missing from [words] table, untranslated")
    ] = False,
    root: Annotated[str, Param("the project whose level schema this is")] = ".",
) -> dict:
    """Each field of the project's level schema, for a game's own editor (§PW608).

    Per field its dotted path, type, min and max, step and unit (`x-step`, `x-unit`),
    default, choices, help (`description`), whether it is required and whether it names
    a world entity, read off `[levels] schema` so the editor, the reader and the docs
    say one declaration. `out` writes them as JSON, recorded with the schema.
    """
    from polyweave.kernel import provenance
    from polyweave.kernel.files import write_atomic

    config = load(root)
    here = config.root
    named, schema = _schema(here, config.table("levels"))
    listed = _fields(schema)
    answer: dict = {"schema": named, "fields": listed}
    if strings:
        from polyweave.layers.words import words

        answer["strings"] = words.added(
            {one["help_key"]: one["help"] for one in listed if "help_key" in one},
            root=here)
    if out:
        target = here / out
        write_atomic(target, json.dumps({"schema": named, "fields": listed}, indent=1)
                     + "\n")
        provenance.write(provenance.build(
            "level", target, root=here,
            inputs=[provenance.source("schema", here / named, root=here)]), root=here)
        answer["written"] = provenance.relative(target, here)
    answer["says"] = (f"{len(listed)} field(s) in {named}"
                      + (f", written to {answer['written']}" if out else ""))
    return answer


#: GDScript's spelling of each JSON Schema type a field may hold.
_GD = {"integer": "int", "number": "float", "string": "String", "boolean": "bool"}


def _class_name(path: list[str]) -> str:
    """An inner class's name off its path, behind an underscore: a game's own
    `class_name Level` is global, and an inner class of that name hides it and the
    reader fails to load (Cottony's did, 2026-11-04)."""
    return "_" + ("".join(part[:1].upper() + part[1:] for part in
                          "_".join(path).replace("-", "_").split("_") if part)
                  or "Level")


def _gd_check(kind: str, value: str) -> str:
    return {"integer": f"({value} is int or ({value} is float and "
                       f"{value} == floorf({value})))",
            "number": f"({value} is int or {value} is float)",
            "string": f"{value} is String",
            "boolean": f"{value} is bool"}[kind]


def _reader_class(node: dict, path: list[str], classes: list[str]) -> str:
    """One inner class for an object node, its children written first, and its name."""
    name = _class_name(path)
    properties = node.get("properties") or {}
    wanted = set(node.get("required") or [])
    lines = [f"class {name}:"]
    reads = []
    for key, child in properties.items():
        kind = child.get("type")
        if kind == "object":
            inner = _reader_class(child, [*path, key], classes)
            lines.append(f"\tvar {key}: {inner} = null")
            reads.append((key, child, "object", inner))
        elif kind == "array" and isinstance(child.get("items"), dict) \
                and child["items"].get("type") == "object":
            inner = _reader_class(child["items"], [*path, key], classes)
            lines.append(f"\tvar {key}: Array = []")
            reads.append((key, child, "objects", inner))
        elif kind in _GD:
            lines.append(f"\tvar {key}: {_GD[kind]}")
            reads.append((key, child, kind, None))
        else:
            lines.append(f"\tvar {key}: Variant = null")
            reads.append((key, child, "any", None))
    keys = ", ".join(f'"{k}"' for k in properties)
    lines += ["",
              f"\tstatic func of(d: Dictionary, at: String, errors: Array) -> {name}:",
              f"\t\tvar it := {name}.new()"]
    if node.get("additionalProperties") is False:
        lines += ["\t\tfor key in d:",
                  f"\t\t\tif not key in [{keys}]:",
                  '\t\t\t\terrors.append("%s%s is no key the schema declares" % '
                  '[at + "." if at else "", key])']
    for key, child, kind, inner in reads:
        where = f'(at + ".{key}" if at else "{key}")'
        lines.append(f'\t\tif d.has("{key}"):')
        lines.append(f'\t\t\tvar v: Variant = d["{key}"]')
        if kind == "object":
            lines += ["\t\t\tif v is Dictionary:",
                      f"\t\t\t\tit.{key} = {inner}.of(v, {where}, errors)",
                      "\t\t\telse:",
                      f'\t\t\t\terrors.append("%s is no object" % {where})']
        elif kind == "objects":
            lines += ["\t\t\tif v is Array:",
                      "\t\t\t\tfor i in v.size():",
                      "\t\t\t\t\tif v[i] is Dictionary:",
                      f'\t\t\t\t\t\tit.{key}.append({inner}.of(v[i], "%s[%d]" % '
                      f"[{where}, i], errors))",
                      "\t\t\t\t\telse:",
                      '\t\t\t\t\t\terrors.append("%s[%d] is no object" % '
                      f"[{where}, i])",
                      "\t\t\telse:",
                      f'\t\t\t\terrors.append("%s is no list" % {where})']
        elif kind in _GD:
            lines += [f"\t\t\tif {_gd_check(kind, 'v')}:",
                      f"\t\t\t\tit.{key} = {_GD[kind]}(v)" if kind != "string"
                      else f"\t\t\t\tit.{key} = v"]
            for bound, word, compare in (("minimum", "least", "<"),
                                         ("maximum", "most", ">")):
                if bound in child and kind in ("integer", "number"):
                    lines += [f"\t\t\t\tif it.{key} {compare} {child[bound]}:",
                              f'\t\t\t\t\terrors.append("%s is past its {word}, '
                              f'{child[bound]}" % {where})']
            if "enum" in child:
                choices = ", ".join(json.dumps(c) for c in child["enum"])
                lines += [f"\t\t\t\tif not it.{key} in [{choices}]:",
                          f'\t\t\t\t\terrors.append("%s is none of its choices" % '
                          f"{where})"]
            lines += ["\t\t\telse:",
                      f'\t\t\t\terrors.append("%s is no {kind}" % {where})']
        else:
            lines.append(f"\t\t\tit.{key} = v")
            if "enum" in child:
                choices = ", ".join(json.dumps(c) for c in child["enum"])
                lines += [f"\t\t\tif not v in [{choices}]:",
                          f'\t\t\t\terrors.append("%s is none of its choices" % '
                          f"{where})"]
        if key in wanted:
            lines += ["\t\telse:",
                      f'\t\t\terrors.append("%s is required and missing" % {where})']
    lines += ["\t\treturn it", ""]
    classes.append("\n".join(lines))
    return name


def _reader(schema: dict, named: str) -> str:
    """The typed reader a game loads its levels through, written from the schema."""
    classes: list[str] = []
    _reader_class(schema, [], classes)
    return "\n".join([
        f"# One level as {named} declares it, generated by level.reader;",
        "# write it again rather than by hand (polyweave, §PW608).",
        "extends RefCounted",
        "",
        "",
        "## the level the game parsed, typed, and every place it breaks the schema",
        "static func read(data: Dictionary) -> Dictionary:",
        "\tvar errors: Array = []",
        '\tvar level := _Level.of(data, "", errors)',
        '\treturn {"level": level, "errors": errors}',
        "",
        "",
        *classes,
    ])


@operation("level.reader")
def reader(
    out: Annotated[str, Param("where the script goes, a .gd under the project")],
    root: Annotated[str, Param("the project whose level schema this is")] = ".",
) -> dict:
    """Write the typed reader a game loads its levels through, from its schema.

    A GDScript with one class per object the schema declares, typed fields, and
    `read(data)`, which takes the level the game parsed and answers `level` and
    `errors`, each naming its place: a key the schema does not declare, one missing, a
    type, a bound or a choice broken (§PW608). Written again where the schema changed.
    """
    from polyweave.kernel import provenance
    from polyweave.kernel.files import write_atomic

    config = load(root)
    here = config.root
    named, schema = _schema(here, config.table("levels"))
    if not out.endswith(".gd"):
        raise PolyweaveError("level.no-level", f"{out} is not a .gd script to write",
                             "name the reader as a .gd under the project", given=out)
    target = here / out
    text = _reader(schema, named)
    changed = not target.is_file() or target.read_text(encoding="utf-8") != text
    if changed:
        target.parent.mkdir(parents=True, exist_ok=True)
        write_atomic(target, text)
        provenance.write(provenance.build(
            "level", target, root=here,
            inputs=[provenance.source("schema", here / named, root=here)]), root=here)
    return {"reader": provenance.relative(target, here), "written": changed,
            "says": f"{out} reads a level as {named} declares it"
            + ("" if changed else ", unchanged")}


@operation("level.validate")
def validate(
    level: Annotated[str, Param("one level file; every [levels] files match if empty")]
    = "",
    root: Annotated[str, Param("the project whose levels these are")] = ".",
) -> dict:
    """Every declared level file held to the project's schema and its world.

    Reads `[levels] schema`, a JSON Schema the project wrote, and each file `[levels]
    files` matches (TOML or JSON). Each finding names the file, the place in it and
    what is wrong: a type, a missing or undeclared key, a value outside its enum or
    bounds, or an `x-entity` string naming no entity of the world (§PW203).
    """
    config = load(root)
    here = config.root
    table = config.table("levels")
    named, schema = _schema(here, table)
    if level:
        files = [here / level]
    else:
        files = sorted({path for pattern in table.get("files") or []
                        for path in here.glob(str(pattern)) if path.is_file()})
    if not files or not all(path.is_file() for path in files):
        raise PolyweaveError(
            "level.no-level",
            f"there is no level at {level}" if level
            else "[levels] files matches no level file",
            "name a level file under the project, or list its pattern in "
            '[levels] files, such as ["data/levels/*.json"]', given=level or None)
    findings = _findings(files, schema, here)
    return {
        "ok": not findings,
        "files": len(files),
        "findings": findings,
        "says": f"{len(files)} level file(s) against {named}: "
        + ("every one holds" if not findings
           else f"{len(findings)} finding(s), the first {findings[0]['file']} "
           f"{findings[0]['at']}: {findings[0]['said']}"),
    }
