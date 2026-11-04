"""A draft level from a transcription a person accepted row by row (§PW609).

Once the owner has answered every row of a reference's transcription, an agent used to
retype the rows into the game's level file, a long session and a source of the slips the
sitting had removed. The project declares once how a row becomes part of its level, in
a mapping file of its own, since no genre is compiled in:

    level  = "game/waves/phase_1.waves.toml"   # the level the rows go into, or {}
    into   = "stage.0.wave.0.group"            # the list each row becomes an item of
    offset = 3.0                               # seconds taken off a row's from and to

    [row]                                      # what one row becomes
    enemy = "{kind}"                           # a column's value, as the row holds it
    count = "{count}"
    at    = "{from}"                           # the row's span, offset

    [names.kind]                               # a column's words, the project's names
    pod = "mote"

`reference.draft(sheet, mapping, out)` refuses a sheet with a row unanswered or one a
person corrected in words, since the agent never turns their words into a value itself,
and writes the draft (TOML or JSON, by `out`'s suffix) recorded with the sheet, its
answers and the mapping as inputs, and `draft = true`. Where the project declares
`[levels] schema`, the draft is held to it and the findings come back; a draft still
gets a person's tuning.
"""

from __future__ import annotations

import json
import re
import tomllib
from typing import Annotated, Any

from polyweave.kernel import provenance
from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError
from polyweave.kernel.files import write_atomic

from . import reference_transcription as transcription

_ONE = re.compile(r"^\{(\w+)\}$")
_ANY = re.compile(r"\{(\w+)\}")


def _bad_mapping(what: str, **extra: Any) -> PolyweaveError:
    return PolyweaveError(
        "capture.bad-mapping", what,
        'write the mapping as TOML: into = "a.0.list", [row] with "{column}" values, '
        "and [names.<column>] renames where the words differ", **extra)


def _filled(template: Any, row: dict, names: dict) -> Any:
    """A [row] value with the row's own put in: one placeholder keeps the value's type,
    a placeholder inside words is written into them, anything else is as declared."""
    if not isinstance(template, str):
        return template

    def value(column: str) -> Any:
        if column not in row:
            raise _bad_mapping(f"[row] names {{{column}}}, which the sheet's rows lack",
                               given=column)
        got = row[column]
        return names.get(column, {}).get(str(got), got)

    whole = _ONE.match(template)
    if whole:
        return value(whole.group(1))
    return _ANY.sub(lambda m: str(value(m.group(1))), template)


def _list_at(document: dict, path: str) -> list:
    """The list at a dotted path, made where the path ends in nothing yet."""
    node: Any = document
    keys = path.split(".")
    for i, key in enumerate(keys):
        last = i == len(keys) - 1
        nxt = keys[i + 1] if not last else None
        if isinstance(node, list):
            if not key.isdigit() or int(key) > len(node):
                raise _bad_mapping(f"into names {path}, and {key} is past the list",
                                   given=path)
            if int(key) == len(node):
                node.append({})
            node = node[int(key)]
            continue
        if not isinstance(node, dict):
            raise _bad_mapping(f"into names {path}, which runs through a value",
                               given=path)
        if key not in node:
            node[key] = [] if last or (nxt or "").isdigit() else {}
        node = node[key]
    if not isinstance(node, list):
        raise _bad_mapping(f"into names {path}, which is no list", given=path)
    return node


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{k} = {_toml_value(v)}" for k, v in value.items()) \
            + " }"
    raise _bad_mapping(f"a value {value!r} has no TOML spelling")


def _is_tables(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(v, dict) for v in value)


def _toml(document: dict, prefix: str = "") -> list[str]:
    """A document as TOML: its plain keys, then each table and array of tables."""
    lines = [f"{k} = {_toml_value(v)}" for k, v in document.items()
             if not isinstance(v, dict) and not _is_tables(v)]
    for key, value in document.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            lines += ["", f"[{name}]", *_toml(value, name)]
        elif _is_tables(value):
            for one in value:
                lines += ["", f"[[{name}]]", *_toml(one, name)]
    return lines


@operation("reference.draft")
def draft(
    sheet: Annotated[str, Param("the transcription a person answered")],
    mapping: Annotated[str, Param("the project's mapping of a row into its level")],
    out: Annotated[str, Param("where the draft level goes, .toml or .json")],
    root: Annotated[str, Param("the project the files are under")] = ".",
) -> dict:
    """A draft level from a transcription accepted row by row (§PW609).

    Refused while a row is unanswered or corrected. Each row becomes an item of the
    mapping's `into` list as its `[row]` says, renamed by `[names.<column>]` and its
    span offset; the draft is recorded with the sheet, its answers and the mapping, and
    held to `[levels] schema` where one is declared.
    """
    config = load(root)
    here = config.root
    where = here / sheet
    said = transcription.transcribed(sheet, root=str(here))
    if not said["accepted"]:
        waiting = said["unanswered"] + [one["row"] for one in said["corrected"]]
        raise PolyweaveError(
            "capture.not-accepted",
            f"{sheet} is not accepted: {len(said['unanswered'])} row(s) unanswered and "
            f"{len(said['corrected'])} corrected, the first {waiting[0]}",
            "write each correction into the sheet, lay it out again with "
            "reference.transcription, and have the person answer it",
            detail={"unanswered": said["unanswered"], "corrected": said["corrected"]})
    try:
        declared = tomllib.loads((here / mapping).read_text(encoding="utf-8-sig"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise _bad_mapping(f"{mapping} is not a TOML file to read",
                           detail=str(exc)) from exc
    into, shape = declared.get("into"), declared.get("row")
    names = declared.get("names") or {}
    offset = declared.get("offset", 0)
    if (not isinstance(into, str) or not isinstance(shape, dict) or not shape
            or not isinstance(names, dict) or not isinstance(offset, int | float)):
        raise _bad_mapping(f"{mapping} names no into list and [row], or its names or "
                           "offset are not a table and a number")
    base = declared.get("level")
    document: dict = (transcription.read(here / base) if base else {})
    target_list = _list_at(document, into)
    for row in transcription.read(where)["rows"]:
        timed = {**row, "from": round(row["from"] - offset, 3),
                 "to": round(row["to"] - offset, 3)}
        target_list.append({key: _filled(value, timed, names)
                            for key, value in shape.items()})
    target = here / out
    if target.suffix.lower() == ".json":
        text = json.dumps(document, indent=1, ensure_ascii=False) + "\n"
    elif target.suffix.lower() == ".toml":
        text = "\n".join(_toml(document)).lstrip("\n") + "\n"
    else:
        raise _bad_mapping(f"{out} is neither .toml nor .json", given=out)
    write_atomic(target, text)
    inputs = [provenance.source("transcription", where, root=here),
              provenance.source("mapping", here / mapping, root=here)]
    answers = transcription._answers_of(where)
    if answers.is_file():
        inputs.append(provenance.source("answers", answers, root=here))
    provenance.write(provenance.build(
        "capture", target, engine={"name": "reference.draft"}, inputs=inputs,
        params={"draft": True, "rows": said["rows"], "into": into}, root=here), here)
    findings: list = []
    if config.table("levels").get("schema"):
        from polyweave.layers.engine import level_schema

        findings = level_schema.validate(out, root=str(here))["findings"]
    return {
        "draft": provenance.relative(target, here),
        "rows": said["rows"],
        "findings": findings,
        "says": f"{said['rows']} accepted row(s) drafted into {out} at {into}"
        + (f"; {len(findings)} finding(s) against the schema" if findings else "")
        + "; a person still tunes it",
    }
