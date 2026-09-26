"""A project's config proposed from its own tree (§PW218).

Starship's `polyweave.toml` was written by hand, one key at a time, against a spec an
agent had to read before its first call. `python -m polyweave init`, and the
`project.init` operation behind it, reads the tree instead and proposes the file:

- `[project] name` from `project.godot`'s `config/name`, or from the directory;
- `[paths] godot` as `${GODOT}` where that variable is set, and never a binary's
  absolute path, which is one desk's and not the project's;
- `meshes`, `renders` and `specs` from folders that already exist, else the defaults;
- `[style]` and `[words]` only where there is something to point them at: a folder
  named `canon`, a translation CSV Godot imports;
- a `[service]` only for a key variable that is already set.

By default it answers with the proposal and writes nothing. `write` writes it, and
refuses a file that exists unless `merge` says to add only the tables it lacks, never
changing a value a person wrote. The text is checked by the loader every call uses
before anything is written, so a key nothing declares cannot land.

**It never writes a `[budget]`.** A ceiling is a person's to set, and an agent that
could set its own would be spending on its own judgement. The answer names the table as
missing and who fills it.
"""

from __future__ import annotations

import os
import re
import tomllib
from pathlib import Path
from typing import Annotated

from .config import DEFAULTS, FILENAME, _check
from .describe import Param, operation
from .errors import PolyweaveError
from .files import read_text_retrying, write_atomic

#: The services this plugin has a client for, and the variable each key is read from.
SERVICES = {
    "meshy": ("https://api.meshy.ai", "MESHY_API_KEY"),
    "ideogram": ("https://api.ideogram.ai", "IDEOGRAM_API_KEY"),
}

#: Where each produced kind is looked for, in order, before the default is proposed.
FOLDERS = {
    "meshes": ("assets/3d", "assets/models", "models"),
    "renders": ("docs/renders", "renders"),
}

#: What is missing from every proposal, and who supplies it.
MISSING_BUDGET = {
    "table": "budget",
    "who": "a person: a spending ceiling is theirs to set, with an expiry, and the "
    "plugin spends nothing until one is written",
}


@operation("project.init")
def init(
    root: Annotated[str, Param("the project whose tree is read")] = ".",
    write: Annotated[bool, Param("write it, not only propose it")] = False,
    merge: Annotated[bool, Param("add only the tables a file lacks")] = False,
    agent: Annotated[bool, Param("wire the agent: server, AGENTS.md")] = False,
) -> dict:
    """Propose polyweave.toml from what the project's tree already holds.

    Nothing is written unless `write` is true, a file that exists is refused unless
    `merge` is, and a `[budget]` is never proposed: it is named as missing instead.
    With `agent`, the server is declared and AGENTS.md gets a marked section (§PW219).
    """
    here = Path(root).expanduser().resolve()
    tables = proposed(here)
    target = here / FILENAME
    existing = read_text_retrying(target)
    if existing is not None and write and not merge:
        raise PolyweaveError(
            "config.exists",
            f"{target} already exists, and init does not overwrite a person's file",
            "pass merge to add only the tables it lacks, or edit the file by hand",
        )
    held: dict = {}
    if existing is not None:
        try:
            held = tomllib.loads(existing)
        except tomllib.TOMLDecodeError as exc:
            raise PolyweaveError(
                "config.malformed",
                f"{target} is not readable as TOML, so nothing can be merged into it",
                "fix the syntax the detail points at, then run init again",
                detail=str(exc),
            ) from exc
    if merge and existing is not None:
        # A service is one table or several named ones, never both, so an existing
        # file that declares any keeps its own.
        tables = {
            name: values
            for name, values in tables.items()
            if name not in held and not (name == "service" and "service" in held)
        }
    text = _as_toml(tables)
    combined = (existing.rstrip() + "\n\n" + text) if merge and existing else text
    _check(tomllib.loads(combined), target)
    wrote = False
    if write and (tables or existing is None):
        write_atomic(target, combined)
        wrote = True
    missing = [] if "budget" in held else [dict(MISSING_BUDGET)]
    answer = {
        "file": FILENAME,
        "proposed": text,
        "tables": sorted(tables),
        "wrote": wrote,
        "merged": bool(merge and existing is not None),
        "missing": missing,
        "says": "written" if wrote else "proposed only; pass write to write it",
    }
    if agent:
        from .config import load

        answer["agent"] = wire(here, load(here))
    return answer


def proposed(here: Path) -> dict[str, dict]:
    """Every table the tree gives a reason to write, and only those."""
    tables: dict[str, dict] = {"project": {"name": _name(here)}}
    paths: dict = {}
    if os.environ.get("GODOT"):
        paths["godot"] = "${GODOT}"
    for key, candidates in FOLDERS.items():
        found = next((c for c in candidates if (here / c).is_dir()), None)
        paths[key] = found or DEFAULTS["paths"][key]
    # An input, so stated only where one exists: a folder named here and missing is
    # what project.check reports.
    specs = _first(here, "*.accept.toml")
    if specs:
        paths["specs"] = _relative(specs.parent, here)
    tables["paths"] = paths
    canon = next(
        (d for d in _walk(here, "canon") if d.is_dir()),
        None,
    )
    if canon is not None:
        tables["style"] = {"canon": _relative(canon, here)}
    table = _translations(here)
    if table is not None:
        tables["words"] = {"table": _relative(table, here)}
    keyed = {n: s for n, s in SERVICES.items() if os.environ.get(s[1])}
    if len(keyed) == 1:
        base, variable = next(iter(keyed.values()))
        tables["service"] = {"base": base, "key_env": variable}
    elif keyed:
        tables["service"] = {
            name: {"base": base, "key_env": variable}
            for name, (base, variable) in keyed.items()
        }
    return tables


def _name(here: Path) -> str:
    """The game's own name, from project.godot, or the directory's."""
    text = read_text_retrying(here / "project.godot") or ""
    said = re.search(r'^config/name\s*=\s*"([^"]*)"', text, re.M)
    return said.group(1) if said and said.group(1).strip() else here.name


def _hidden(path: Path, here: Path) -> bool:
    return any(p.startswith(".") for p in path.relative_to(here).parts)


def _walk(here: Path, pattern: str):
    return sorted(p for p in here.rglob(pattern) if not _hidden(p, here))


def _first(here: Path, pattern: str) -> Path | None:
    return next(iter(_walk(here, pattern)), None)


def _translations(here: Path) -> Path | None:
    """The CSV Godot imports as translations, as its .import file says."""
    for imported in _walk(here, "*.csv.import"):
        text = read_text_retrying(imported) or ""
        if 'importer="csv_translation"' in text:
            source = imported.with_suffix("")
            if source.is_file():
                return source
    return None


def _relative(path: Path, here: Path) -> str:
    return path.relative_to(here).as_posix() or "."


def _as_toml(tables: dict[str, dict]) -> str:
    """The proposal as a person would write it: one table a block, strings quoted."""
    lines = [
        "# Proposed by `python -m polyweave init` from what this tree holds.",
        "# Edit it freely: init never overwrites a value a person wrote.",
        "# [budget] is left to a person: nothing is spent until one is written.",
    ]
    for name, values in tables.items():
        nested = {k: v for k, v in values.items() if isinstance(v, dict)}
        flat = {k: v for k, v in values.items() if not isinstance(v, dict)}
        if flat:
            lines += ["", f"[{name}]"]
            lines += [f"{key} = {_value(value)}" for key, value in flat.items()]
        for inner, own in nested.items():
            lines += ["", f"[{name}.{inner}]"]
            lines += [f"{key} = {_value(value)}" for key, value in own.items()]
    return "\n".join(lines) + "\n"


def _value(value) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int | float):
        return str(value)
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


# -- the project's agent, wired to polyweave (§PW219) --------------------------------

#: What an agent section is written between. Text outside them is never touched.
BEGIN = "<!-- polyweave:begin -->"
END = "<!-- polyweave:end -->"

#: The line inside the section that says which version wrote it, for `init --check`.
STAMP = "<!-- written by polyweave {version} (init --agent); rewritten by it -->"

#: How the server is started, as `.mcp.json` declares it.
SERVER = {"command": "python", "args": ["-m", "polyweave", "serve"]}


def wire(here: Path, config) -> dict:
    """Declare the server, and write the project's section of AGENTS.md.

    Each step is idempotent: a second run changes nothing, and says so.
    """
    import json

    changed: list[str] = []
    settings_path = here / ".claude" / "settings.json"
    settings = json.loads(read_text_retrying(settings_path) or "{}")
    enabled = {
        name
        for name, on in (settings.get("enabledPlugins") or {}).items()
        if on and name.split("@")[0] == "polyweave"
    }
    if enabled:
        server = (
            f"not declared: the plugin {sorted(enabled)[0]} is enabled for this "
            "project, and a second server would give every tool twice"
        )
    else:
        mcp_path = here / ".mcp.json"
        mcp = json.loads(read_text_retrying(mcp_path) or "{}")
        servers = mcp.setdefault("mcpServers", {})
        server = "already declared in .mcp.json"
        if "polyweave" not in servers:
            servers["polyweave"] = dict(SERVER)
            write_atomic(mcp_path, json.dumps(mcp, indent=2) + "\n")
            changed.append(".mcp.json")
            server = "declared in .mcp.json"
        listed = settings.get("enabledMcpjsonServers")
        if isinstance(listed, list) and "polyweave" not in listed:
            settings["enabledMcpjsonServers"] = [*listed, "polyweave"]
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            write_atomic(settings_path, json.dumps(settings, indent=2) + "\n")
            changed.append(".claude/settings.json")
    agents = here / "AGENTS.md"
    before = read_text_retrying(agents)
    section = agent_section(config)
    after = _placed(before, section, config)
    if after != before:
        write_atomic(agents, after)
        changed.append("AGENTS.md")
    claude = here / "CLAUDE.md"
    said = read_text_retrying(claude)
    if said is None or "@AGENTS.md" not in said:
        write_atomic(claude, (said.rstrip() + "\n\n" if said else "") + "@AGENTS.md\n")
        changed.append("CLAUDE.md")
    return {"server": server, "changed": changed}


def _placed(before: str | None, section: str, config) -> str:
    """AGENTS.md with the section between its markers, and nothing else changed."""
    if before is None:
        return f"# {config.get('project.name')}\n\n{section}"
    start, end = before.find(BEGIN), before.find(END)
    if start != -1 and end > start:
        return before[:start] + section.rstrip("\n") + before[end + len(END) :]
    return before.rstrip("\n") + "\n\n" + section


def _op(name: str) -> str:
    """An operation's name as the registry has it, or a refusal to write it."""
    from .describe import operations

    if name not in operations():
        raise PolyweaveError(
            "op.unknown",
            f"the agent section names {name!r}, which the registry lacks",
            "rename it in polyweave/project.py to the operation that replaced it",
            given=name,
            allowed=operations(),
        )
    return f"`{name}`"


def agent_section(config) -> str:
    """The project's polyweave section, drawn from its config and the registry."""
    from . import __version__

    here = config.root

    def at(address: str) -> str:
        return f"`{_relative(config.path(address), here)}`"

    rows = [
        ("Acceptance specs", at("paths.specs")),
        ("The looks a person is shown", at("paths.renders")),
        ("Models the game loads", at("paths.meshes")),
        ("Prepared references", at("paths.references")),
        ("The purchase ledger", at("paths.purchases")),
        ("What each asset cost, each way", at("paths.loop")),
        ("Work area (caches, sittings' answers)", at("paths.work")),
    ]
    if config.states("style"):
        for family, style in sorted(config.styles().items()):
            if style.get("canon"):
                rows.append(
                    (
                        f"The {family} canon, grown only by a verdict",
                        f"`{_relative(Path(style['canon']), here)}`",
                    )
                )
    if config.get("words.table"):
        rows.append(("The text a player reads", at("words.table")))
    if config.get("words.canon"):
        rows.append(("A person's verdicts on lines", at("words.canon")))
    worlds = _walk(here, "*.world.toml")
    if worlds:
        rows.append(("The world's names and rules", f"`{_relative(worlds[0], here)}`"))
    services = sorted(config.services()) if config.states("service") else []
    budgets = (
        ", ".join(f"`[budget.{n}]`" for n in services)
        if len(services) > 1
        else "`[budget]`"
    )
    lines = [
        BEGIN,
        STAMP.format(version=__version__),
        "",
        "## The game's parts go through polyweave",
        "",
        "polyweave makes and checks this game's parts. Declare what each must "
        "satisfy, and",
        "a search or a person's verdict settles it. Do not tune a look by eye.",
        "",
        "`python -m polyweave describe` lists every operation with its parameters, "
        "and it",
        "is the authority; `python -m polyweave explain <code>` says what a refusal "
        "means.",
        "",
        "### Where this project keeps things",
        "",
        "`polyweave.toml` binds all of it. Read it rather than guessing a path.",
        "",
        "| What | Where |",
        "|---|---|",
        *[f"| {what} | {where} |" for what, where in rows],
        "",
        "### Rules that save a call",
        "",
        f"- **Start with {_op('asset.brief')}.** One read gives the declaration, its "
        "bounds and where each came from, and the last verdict.",
        f"- **A look is a person's to accept.** Show it with {_op('verdict.sitting')} "
        f"and `python -m polyweave review`, and carry their words with "
        f"{_op('verdict.judge')}. Never loosen a bound a person set.",
        f"- **Nothing spends money on your judgement.** {_op('picture.buy')} and "
        f"{_op('mesh.buy')} draw on {budgets} in `polyweave.toml`, which a person "
        f"sets; check {_op('purchase.remaining')} first and never raise one yourself.",
        "- **A refusal is the answer.** It carries `code` and `remedy`, and where a "
        "name was wrong, `allowed` and `did_you_mean`.",
        f"- **Keep provenance.** Every produced file has a `.prov.json` beside it; "
        f"{_op('provenance.verify')} says what drifted.",
    ]
    if worlds:
        lines.append(
            f"- **The world is declared.** {_op('world.read')} gives an entity and its "
            f"approved lines; {_op('words.check')} holds the text to it."
        )
    return "\n".join([*lines, END]) + "\n"


# -- what an adoption is missing (§PW220) --------------------------------------------

#: What a finding is: an error fails the check, a warning is said and passes.
SEVERITIES = ("error", "warning")


@operation("project.check")
def check(root: Annotated[str, Param("the adopted project")] = ".") -> dict:
    """Every gap between this tree and a working adoption, each with its remedy.

    It reads what `init` writes and repairs nothing: each finding names the call that
    would. `clean` is false while any error is left, and `init --check` exits non-zero
    then, so a project can put it in its own gate.
    """
    import json

    from .config import load

    here = Path(root).expanduser().resolve()
    found: list[dict] = []

    def said(error: PolyweaveError, severity: str = "error") -> None:
        found.append({**error.as_dict(), "severity": severity})

    try:
        config = load(here)
    except PolyweaveError as refused:
        said(refused)
        return _checked(found)
    if config.source is None:
        said(
            PolyweaveError(
                "adopt.not-adopted",
                f"{here} has no {FILENAME}",
                "run python -m polyweave init --write --agent",
            )
        )
        return _checked(found)
    _paths(config, said)
    settings = json.loads(
        read_text_retrying(here / ".claude" / "settings.json") or "{}"
    )
    plugin = any(
        on and name.split("@")[0] == "polyweave"
        for name, on in (settings.get("enabledPlugins") or {}).items()
    )
    mcp = json.loads(read_text_retrying(here / ".mcp.json") or "{}")
    declared = "polyweave" in (mcp.get("mcpServers") or {})
    if plugin and declared:
        said(
            PolyweaveError(
                "adopt.server-twice",
                "polyweave is both an enabled plugin and a server in .mcp.json, so "
                "every tool is offered twice",
                "remove polyweave from .mcp.json; the plugin already serves it",
            )
        )
    elif not plugin and not declared:
        said(
            PolyweaveError(
                "adopt.no-server",
                "no polyweave server is declared, so a session here sees no tool",
                "run python -m polyweave init --agent",
            )
        )
    _section(here, said)
    _money(config, said)
    from .provenance import unrecorded

    missing = unrecorded(root=str(here))
    if missing:
        said(
            PolyweaveError(
                "adopt.unrecorded",
                f"{len(missing)} produced file(s) carry no provenance record, the "
                f"first {missing[0]['artefact']}",
                "produce them again through polyweave, or list the hand-made ones "
                "under [provenance] handmade",
            )
        )
    return _checked(found)


def _checked(found: list[dict]) -> dict:
    errors = sum(1 for f in found if f["severity"] == "error")
    return {
        "clean": errors == 0,
        "errors": errors,
        "warnings": len(found) - errors,
        "findings": found,
    }


def _paths(config, said) -> None:
    """Every input path the project states is there, and the engine resolves.

    Meshes and renders are outputs, made on the first write, so their absence is not a
    gap; the specs and references a call reads are.
    """
    for key in ("references", "specs"):
        if not config.declared(f"paths.{key}"):
            continue
        where = config.path(f"paths.{key}")
        if not where.exists():
            said(
                PolyweaveError(
                    "adopt.path-missing",
                    f"[paths] {key} is {_relative(where, config.root)}, and nothing "
                    "is there",
                    f"create it, or correct [paths] {key} in {FILENAME}",
                )
            )
    if config.declared("paths.godot") or (config.root / "project.godot").is_file():
        from .engine import find

        try:
            find(root=str(config.root))
        except PolyweaveError as refused:
            said(refused)


def _section(here: Path, said) -> None:
    """The AGENTS.md section is there, current, and names only real operations."""
    from . import __version__
    from .describe import operations

    text = read_text_retrying(here / "AGENTS.md") or ""
    start, end = text.find(BEGIN), text.find(END)
    if start == -1 or end < start:
        if "polyweave" in text:
            said(
                PolyweaveError(
                    "adopt.no-agent-section",
                    "AGENTS.md speaks of polyweave in text init did not write, so no "
                    "check can say it is current",
                    "leave it, or run python -m polyweave init --agent to add the "
                    "stamped section beside it",
                ),
                "warning",
            )
            return
        said(
            PolyweaveError(
                "adopt.no-agent-section",
                "AGENTS.md has no polyweave section, so an agent here is told nothing "
                "of it",
                "run python -m polyweave init --agent",
            )
        )
        return
    section = text[start:end]
    stamped = re.search(r"written by polyweave (\S+)", section)
    if not stamped or stamped.group(1) != __version__:
        said(
            PolyweaveError(
                "adopt.stale-section",
                "the AGENTS.md section was written by polyweave "
                f"{stamped.group(1) if stamped else 'of no stated version'}, and "
                f"{__version__} is running",
                "run python -m polyweave init --agent to rewrite it",
            ),
            "warning",
        )
    known = set(operations())
    spaces = {name.split(".")[0] for name in known}
    named = {
        n
        for n in re.findall(r"`([a-z_]+\.[a-z_]+)`", section)
        if n.split(".")[0] in spaces
    }
    for gone in sorted(named - known):
        said(
            PolyweaveError(
                "adopt.stale-section",
                f"the AGENTS.md section names {gone}, which this polyweave lacks",
                "run python -m polyweave init --agent to rewrite it",
                given=gone,
                allowed=sorted(known),
            )
        )


def _money(config, said) -> None:
    """Each service's key variable is set, by name, and its budget is current."""
    if not config.states("service"):
        return
    for name, about in sorted(config.services().items()):
        variable = str(about.get("key_env") or "")
        if variable and variable not in os.environ:
            said(
                PolyweaveError(
                    "adopt.key-unset",
                    f"the {name} service's key is read from {variable}, which is not "
                    "set here",
                    f"set {variable} in this environment; its value is never read by "
                    "this check",
                )
            )
        ceiling = config.budget(service=name)
        if not ceiling["spendable"]:
            expired = ceiling["why"].startswith("the budget expired")
            said(
                PolyweaveError(
                    "adopt.budget-lapsed",
                    f"{name} can spend nothing: {ceiling['why']}",
                    f"a person sets {ceiling['table']} in {FILENAME}; the agent never "
                    "does",
                ),
                "error" if expired else "warning",
            )
