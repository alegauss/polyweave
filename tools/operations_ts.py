"""Write the window's typed SDK from `describe` (§PW377).

    python tools/operations_ts.py          # writes the SDK beside the core client
    python tools/operations_ts.py --check  # exits 1 where the committed file is stale

The SDK is gui/packages/core/src/operations.generated.ts.

Every operation's parameters become a TypeScript interface, its choices a union of
literals and its range, unit and default the doc comment beside it, so the window calls
an operation with the arguments `describe` accepts and its typecheck fails on any other.
Payloads are not typed here: `describe` declares none, and a type invented on this side
would be a second contract. tests/test_operations_ts.py fails when the file is stale, as
the site's own test does for roadmap.generated.ts.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "gui" / "packages" / "core" / "src" / "operations.generated.ts"

#: Each type `describe` names, as TypeScript spells it.
TYPES = {
    "str": "string",
    "int": "number",
    "float": "number",
    "bool": "boolean",
    "list": "unknown[]",
    "dict": "Record<string, unknown>",
    "Any": "unknown",
}


def _interface(name: str) -> str:
    """`game.text_fit` as `GameTextFitArgs`."""
    words = name.replace(".", "_").split("_")
    return "".join(word[:1].upper() + word[1:] for word in words) + "Args"


def _type(param: dict) -> str:
    if param.get("choices"):
        return " | ".join(json.dumps(choice) for choice in param["choices"])
    return TYPES.get(param["type"], "unknown")


def _comment(text: str) -> str:
    return text.replace("*/", "* /")


def _doc(param: dict) -> str:
    said = [_comment(param.get("about") or "")]
    if "range" in param:
        lo, hi = param["range"]
        bounds = " to ".join("…" if v is None else f"{v:g}" for v in (lo, hi))
        said.append(f"from {bounds}")
    if param.get("unit"):
        said.append(f"in {param['unit']}")
    if not param["required"] and param.get("default") not in (None, "", [], {}):
        said.append(f"default {json.dumps(param['default'], ensure_ascii=False)}")
    return "; ".join(part for part in said if part)


def generate(operations: list[dict]) -> str:
    """The module's text for every operation `describe` lists, in its order."""
    out = [
        "// Generated from `python -m polyweave describe` by tools/operations_ts.py "
        "(§PW377).",
        "// Do not edit: run `python tools/operations_ts.py`. "
        "tests/test_operations_ts.py",
        "// fails when this file and describe disagree.",
        "",
        "import type { Client } from './client'",
        "",
    ]
    names = []
    for operation in operations:
        name = operation["operation"]
        names.append(name)
        out.append(f"/** {_comment(operation['summary'])} */")
        out.append(f"export interface {_interface(name)} {{")
        for param in operation["parameters"]:
            optional = "" if param["required"] else "?"
            out.append(f"  /** {_doc(param)} */")
            out.append(f"  {param['name']}{optional}: {_type(param)}")
        out.append("}")
        out.append("")
    out.append("/** Every operation by its dotted name, with the arguments it takes. "
               "*/")
    out.append("export interface Operations {")
    out.extend(f"  {json.dumps(name)}: {_interface(name)}" for name in names)
    out.append("}")
    out.append("")
    out.append("/** The operations whose every argument may be left out. */")
    bare = [o["operation"] for o in operations
            if not any(p["required"] for p in o["parameters"])]
    out.append("export type Bare = " + " | ".join(json.dumps(n) for n in bare))
    out.append("")
    out.append("/** Every operation `describe` listed when this file was written. */")
    out.append("export const OPERATIONS = [")
    out.extend(f"  {json.dumps(name)}," for name in names)
    out.append("] as const")
    out.append("")
    out.append("/** Call one operation with the arguments describe says it takes. */")
    returns = "): Promise<unknown>"
    out.append("export function call<K extends Bare>(")
    out.append("  client: Client, operation: K, args?: Operations[K]" + returns)
    out.append("export function call<K extends keyof Operations>(")
    out.append("  client: Client, operation: K, args: Operations[K]" + returns)
    out.append("export function call(")
    out.append("  client: Client, operation: keyof Operations, args?: object,")
    out.append("): Promise<unknown> {")
    out.append("  return client.call(operation, { ...(args ?? {}) })")
    out.append("}")
    return "\n".join(out) + "\n"


def current() -> str:
    from polyweave import describe

    return generate(describe.describe())


def main(argv: list[str]) -> int:
    text = current()
    if "--check" in argv:
        stale = not TARGET.is_file() or TARGET.read_text(encoding="utf-8") != text
        if stale:
            print(f"{TARGET.relative_to(ROOT)} is stale: "
                  "run python tools/operations_ts.py")
        return 1 if stale else 0
    TARGET.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {TARGET.relative_to(ROOT)}: {text.count('export interface') - 1} "
          "operations")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
