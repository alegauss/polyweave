"""A game's data tables held to the schema of one row (§PW364).

Games keep their tuning in tables (enemies, items, waves, prices), and read as loose
JSON or CSV a "10" typed as a string or a field misspelled reaches the game and shows as
a wrong number in play. The project declares each table instead, in the TOML file
`[kit.tables] schema` names (`data/tables.toml` by default):

    [enemies]
    file = "data/enemies.csv"       # a CSV with a header row, or a JSON list of objects
    key = "id"                      # unique in every row, how the game finds one
    [enemies.columns]
    id = { type = "string", required = true }
    hp = { type = "int", required = true, min = 1 }
    speed = { type = "float" }
    kind = { type = "string", choices = ["walker", "flyer"] }

A type is `int`, `float`, `bool` or `string`. The tables are the project's own and
assume no genre. `tables.check` holds every row to its schema, each finding naming the
file, the row and the column, and `write=true` generates a typed table script per table
under `[kit.tables] out` (`tables/`), which the tables kit's PolyweaveTables loads; a
generated script that no longer matches its schema is a finding too.
"""

from __future__ import annotations

import csv
import io
import json
import tomllib
from pathlib import Path
from typing import Annotated, Any

from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

TYPES = ("int", "float", "bool", "string")
#: GDScript's spelling of each type, in a generated row.
_GD = {"int": "int", "float": "float", "bool": "bool", "string": "String"}


def _declared(here: Path) -> tuple[Path, Path]:
    config = load(here)
    kit = config.table("kit") if (here / "polyweave.toml").is_file() else {}
    own = kit.get("tables", {}) if isinstance(kit, dict) else {}
    return (here / own.get("schema", "data/tables.toml"),
            here / own.get("out", "tables"))


def schema(here: Path) -> dict:
    """Every table the project declares, each checked for a usable shape."""
    where, _ = _declared(here)
    if not where.is_file():
        raise PolyweaveError(
            "tables.no-schema",
            f"there is no table schema at {where}",
            "declare each table and its columns there, or set [kit.tables] schema",
        )
    try:
        tables = tomllib.loads(where.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise PolyweaveError("tables.no-schema", f"{where.name} is not TOML",
                             "fix the syntax the detail points at",
                             detail=str(exc)) from exc
    for name, table in tables.items():
        columns = table.get("columns") if isinstance(table, dict) else None
        if not isinstance(columns, dict) or not table.get("file"):
            raise PolyweaveError(
                "tables.no-schema",
                f"[{name}] declares no file and columns",
                f'write [{name}] file = "data/{name}.csv" and [{name}.columns]',
            )
        for column, rule in columns.items():
            if not isinstance(rule, dict) or rule.get("type") not in TYPES:
                raise PolyweaveError(
                    "tables.no-schema",
                    f"[{name}.columns] {column} has no type of {', '.join(TYPES)}",
                    f'write {column} = {{ type = "int" }}, or float, bool or string',
                )
    return tables


def rows(path: Path) -> list[tuple[int, dict]]:
    """A table's rows, each with the line (CSV) or place (JSON) it is at."""
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        listed = json.loads(text)
        if isinstance(listed, dict):
            listed = listed.get("rows", [])
        return [(index + 1, row) for index, row in enumerate(listed)]
    reader = csv.DictReader(io.StringIO(text))
    return [(reader.line_num, dict(row)) for row in reader]


def _typed(value: Any, rule: dict, from_csv: bool) -> tuple[Any, str]:
    """The value as its column's type, or why it is not one."""
    kind = rule["type"]
    if from_csv and isinstance(value, str):
        text = value.strip()
        try:
            if kind == "int":
                return int(text), ""
            if kind == "float":
                return float(text), ""
            if kind == "bool":
                if text.lower() in ("true", "false"):
                    return text.lower() == "true", ""
                return None, f"{value!r} is no bool, which a table writes true or false"
        except ValueError:
            return None, f"{value!r} is no {kind}"
        return value, ""
    wanted = {"int": int, "float": (int, float), "bool": bool, "string": str}[kind]
    if isinstance(value, bool) and kind != "bool" or not isinstance(value, wanted):
        return None, f"{value!r} is a {type(value).__name__}, not the {kind} declared"
    return value, ""


def check_table(name: str, table: dict, here: Path) -> list[dict]:
    """Every row of one table held to its columns, each finding with its place."""
    path = here / table["file"]
    found: list[dict] = []

    def said(row: int, column: str, words: str) -> None:
        found.append({"table": name, "file": table["file"], "row": row,
                      "column": column, "said": words})

    if not path.is_file():
        said(0, "", f"{table['file']} is not there")
        return found
    columns: dict = table["columns"]
    from_csv = path.suffix.lower() != ".json"
    seen: dict[Any, int] = {}
    for at, row in rows(path):
        for column in sorted(set(row) - set(columns)):
            said(at, column, f"{column} is no column [{name}] declares")
        for column, rule in columns.items():
            value = row.get(column)
            empty = value is None or (from_csv and str(value).strip() == "")
            if empty:
                if rule.get("required"):
                    said(at, column, f"{column} is required and missing")
                continue
            typed, why = _typed(value, rule, from_csv)
            if why:
                said(at, column, why)
                continue
            if rule.get("choices") and typed not in rule["choices"]:
                said(at, column, f"{typed!r} is none of {rule['choices']}")
            if "min" in rule and typed < rule["min"]:
                said(at, column, f"{typed} is under its least, {rule['min']}")
            if "max" in rule and typed > rule["max"]:
                said(at, column, f"{typed} is over its most, {rule['max']}")
            if column == table.get("key"):
                if typed in seen:
                    said(at, column, f"{typed!r} is the key of row {seen[typed]} too")
                seen.setdefault(typed, at)
    return found


def generated(name: str, table: dict) -> str:
    """The typed table script the game loads one table through."""
    columns = table["columns"]
    lines = [
        f"# The {name} table, generated by tables.check write=true from its schema;",
        "# write it again rather than by hand (polyweave, §PW364).",
        "extends RefCounted",
        "",
        f'const FILE := "res://{table["file"]}"',
        f'const KEY := "{table.get("key", "")}"',
        "const COLUMNS := {"
        + ", ".join(f'"{c}": "{rule["type"]}"' for c, rule in columns.items()) + "}",
        "",
        "",
        "class Row:",
    ]
    lines += [f"\tvar {column}: {_GD[rule['type']]}"
              for column, rule in columns.items()]
    lines += ["", "", "## each row, typed as the schema declares it",
              "static func read() -> Array:",
              "\tvar out := []",
              "\tfor values in load(\"res://addons/polyweave/tables/tables.gd\")"
              ".values_of(FILE, COLUMNS):",
              "\t\tvar row := Row.new()",
              "\t\tfor column in values:",
              "\t\t\trow.set(column, values[column])",
              "\t\tout.append(row)",
              "\treturn out", ""]
    return "\n".join(lines)


@operation("tables.check")
def check(
    root: Annotated[str, Param("the project whose tables these are")] = ".",
    *,
    write: Annotated[
        bool, Param("write each table's typed script for the game to load")
    ] = False,
) -> dict:
    """Every row of every declared table held to its schema, and each typed script.

    Each finding names the table, file, row (the CSV line, or the JSON place) and
    column: a value of another type than declared, a "10" in a JSON number column
    included, a required column missing, a column the schema does not declare, a choice
    outside its set, a number outside its least or most, a key used twice. A generated
    script that no longer matches its schema is a finding; `write` writes them again
    (§PW364).
    """
    here = load(root).root
    tables = schema(here)
    _, out = _declared(here)
    findings: list[dict] = []
    wrote = []
    for name, table in tables.items():
        findings += check_table(name, table, here)
        script = out / f"{name}.gd"
        text = generated(name, table)
        if write:
            script.parent.mkdir(parents=True, exist_ok=True)
            script.write_text(text, encoding="utf-8", newline="\n")
            wrote.append(script.relative_to(here).as_posix())
        elif not script.is_file() or script.read_text(encoding="utf-8") != text:
            findings.append({"table": name, "file": script.relative_to(here).as_posix(),
                             "row": 0, "column": "",
                             "said": f"the {name} script does not match its schema; "
                             "write it again with tables.check write=true"})
    return {
        "clean": not findings,
        "tables": sorted(tables),
        "findings": findings,
        "wrote": wrote,
        "says": f"{len(tables)} table(s), "
        + ("every row as declared" if not findings else
           f"{len(findings)} finding(s), the first {findings[0]['file']} row "
           f"{findings[0]['row']} {findings[0]['column']}: {findings[0]['said']}"),
    }
