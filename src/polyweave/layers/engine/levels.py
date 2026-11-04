"""A level played by the game's own probe, and what it measured read back (§PW202).

A match-3 bot and a shooter's threat count share nothing but their shape: a script in
the game takes a level and some seeds, plays or reads it, and prints numbers. polyweave
cannot own that script without compiling one genre in, so it owns the handshake. The
project declares the script and what it reports:

    [levels]
    probe = "res://tools/level_probe.gd"
    seeds = 200
    percentiles = [10, 50, 90]

    [levels.measures]
    won        = { unit = "0 or 1", direction = "higher" }
    moves_left = { unit = "moves",  direction = "higher" }
    stars      = { unit = "stars",  direction = "higher" }

`level.probe` runs the script headless with `level=res://…` and `seeds=N` after `--`.
It prints one line a seed, `level: seed=1 won=1 moves_left=4 stars=2`, for seeds 1 to
N. A line missing a declared measure, carrying one nobody declared, or a seed missing or
twice is refused rather than read as a zero (§PW201: the measure that carried the feel
was one the bot never printed). Each measure is aggregated at the declared percentiles
and its mean, because a level's feel lives in its bad runs as much as its median.

The answer lands beside the level as `<level>.probe.json`, recorded with the level and
the probe as inputs and the engine's version, and a later run says how far each measure
moved from the one before, so a rule change that moves a level's difficulty is reported
rather than found by a player.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Annotated, Any

import numpy as np

from polyweave.kernel import provenance
from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError
from polyweave.kernel.files import write_atomic

LINE = re.compile(r"^level:[ \t]*(?P<pairs>.*)$", re.MULTILINE)
PAIR = re.compile(r"(\w+)=(-?\d+(?:\.\d+)?)")
#: The engine's version, as Godot prints it on its first line.
VERSION = re.compile(r"Godot Engine (v[^\s]+)")
DIRECTIONS = ("higher", "lower")


def _measures(declared: dict) -> dict[str, dict]:
    """Each declared measure with its unit and direction, or why the table is wrong."""
    if not isinstance(declared, dict) or not declared:
        raise PolyweaveError(
            "level.bad-measures", "[levels.measures] declares no measure",
            'declare each one the probe prints: won = { unit = "0 or 1", '
            'direction = "higher" }')
    out = {}
    for name, one in declared.items():
        if (not re.fullmatch(r"\w+", str(name)) or name == "seed"
                or not isinstance(one, dict) or not str(one.get("unit", ""))
                or one.get("direction", "higher") not in DIRECTIONS):
            raise PolyweaveError(
                "level.bad-measures", f"measure {name!r} is declared as {one!r}",
                "give it a word for a name (not seed), a unit, and a direction of "
                "higher or lower", given=str(name))
        out[str(name)] = {"unit": str(one["unit"]),
                          "direction": one.get("direction", "higher")}
    return out


def _read_lines(output: str, measures: dict, seeds: int) -> dict[str, list[float]]:
    """Each measure's value per seed, in seed order, refused on any line that does not
    say exactly what was declared, and on a seed missing or said twice."""
    values: dict[int, dict[str, float]] = {}
    for line in LINE.finditer(output):
        text = line["pairs"].strip()
        pairs = PAIR.findall(text)
        if not pairs or PAIR.sub("", text).strip():
            raise _bad_line(text, "is not name=number pairs")
        said = {name: float(value) for name, value in pairs}
        seed = said.pop("seed", None)
        if seed is None or seed != int(seed):
            raise _bad_line(text, "names no whole seed")
        missing = sorted(set(measures) - set(said))
        extra = sorted(set(said) - set(measures))
        if missing:
            raise _bad_line(text, f"misses {', '.join(missing)}")
        if extra:
            raise _bad_line(text, f"carries {', '.join(extra)}, which "
                            "[levels.measures] does not declare")
        if int(seed) in values:
            raise _bad_line(text, f"says seed {int(seed)} a second time")
        values[int(seed)] = said
    wanted = set(range(1, seeds + 1))
    if set(values) != wanted:
        absent = sorted(wanted - set(values))
        beyond = sorted(set(values) - wanted)
        raise PolyweaveError(
            "level.bad-line",
            f"the probe answered {len(values)} of {seeds} seeds"
            + (f", missing {absent[:5]}" if absent else "")
            + (f", and seeds never asked for {beyond[:5]}" if beyond else ""),
            "print one level: line for each seed from 1 to the seeds= it was passed")
    return {name: [values[s][name] for s in sorted(values)] for name in measures}


def _bad_line(text: str, why: str) -> PolyweaveError:
    return PolyweaveError(
        "level.bad-line", f"the probe's line 'level: {text[:120]}' {why}",
        "print level: seed=N and every declared measure as name=number, nothing else",
        given=text[:200])


def _aggregate(values: dict[str, list[float]], percentiles: list) -> dict[str, dict]:
    """Each measure at each percentile and its mean, rounded for reading."""
    out = {}
    for name, seen in values.items():
        held = np.array(seen, dtype=np.float64)
        out[name] = {"mean": round(float(held.mean()), 4),
                     **{f"p{int(p)}": round(float(np.percentile(held, p)), 4)
                        for p in percentiles}}
    return out


def _moved(now: dict, before: dict | None) -> dict:
    """How far each aggregate moved from the run before, where there was one."""
    if not before:
        return {}
    out = {}
    for name, held in now.items():
        was = before.get(name) or {}
        changed = {key: {"was": was[key], "now": value}
                   for key, value in held.items()
                   if key in was and was[key] != value}
        if changed:
            out[name] = changed
    return out


#: What a level's acceptance spec reads off its probe (§PW204): one name, the measure
#: and the place in its spread being the predicate's `probed` and `at`.
LEVEL: dict[str, str] = {
    "level": "a measure the game's level probe printed (probed=), at a percentile or "
    "its mean (at=, p50 unless said), off the record level.probe wrote beside it",
}


def _recorded(where: Path, here: Path) -> dict:
    """What level.probe measured of a level, refused where the level was never probed
    or changed since (§PW204)."""
    target = where.with_name(where.stem + ".probe.json")
    if not where.is_file() or not target.is_file():
        raise PolyweaveError(
            "level.unprobed", f"{where.name} has no probe record beside it",
            f"run level.probe on {provenance.relative(where, here)} first",
            given=str(where))
    record = provenance.read(str(target), root=here)
    level_in = next((one for one in record.get("inputs", [])
                     if one.get("role") == "level"), {})
    digest, _ = provenance.sha256_of(where)
    if level_in.get("sha256") != digest:
        raise PolyweaveError(
            "level.unprobed",
            f"{where.name} changed since it was probed, so its record says "
            "nothing of it now",
            f"run level.probe on {provenance.relative(where, here)} again",
            given=str(where))
    return json.loads(target.read_text(encoding="utf-8"))["measured"]


def _value(measured: dict, probed: str, at: str, where: Path) -> float:
    if probed not in measured or at not in measured[probed]:
        raise PolyweaveError(
            "level.bad-measures",
            f"the probe of {where.name} reports no "
            f"{probed or '(probed unset)'} at {at}",
            f"name probed= one of {', '.join(measured)} and at= one of "
            f"{', '.join(next(iter(measured.values()), {}))}",
            given=probed)
    return float(measured[probed][at])


def predicate(p, subject, root: str | Path, seen: dict) -> dict:
    """A level predicate for accept.check, read off `<level>.probe.json` and refused
    where the level changed since it was probed or was never probed (§PW204)."""
    here = Path(root)
    where = Path(p.of) if p.of else Path(subject)
    where = where if where.is_absolute() else here / where
    probed = str(p.arguments.get("probed") or "")
    at = str(p.arguments.get("at") or "p50")
    key = f"level:{where}"
    if key not in seen:
        seen[key] = _recorded(where, here)
    return {"value": _value(seen[key], probed, at, where), "of": str(where),
            "probed": probed, "at": at}


def _curve_rules(spec: dict, count: int) -> tuple[float, list, list]:
    step = spec.get("step", 0.0)
    regions = spec.get("regions", [])
    dips = spec.get("dips", [])
    if (not isinstance(step, int | float) or step < 0
            or not isinstance(regions, list) or not isinstance(dips, list)
            or not all(isinstance(r, list) and len(r) == 2
                       and all(isinstance(i, int) and 1 <= i <= count for i in r)
                       and r[0] < r[1] for r in regions)
            or not all(isinstance(i, int) and 1 <= i < count for i in dips)):
        raise PolyweaveError(
            "level.bad-set",
            "the set's step, regions or dips do not say a shape over its levels",
            "write step as a number from 0, regions as [[first, last], ...] and dips "
            f"as positions, each from 1 to {count}, first before last")
    return float(step), regions, dips


def _curve_findings(names: list[str], hard: list[float], step: float, regions: list,
                   dips: list) -> list[dict]:
    """Each place a set's difficulty breaks its declared shape, as the pair of levels
    that broke it. `hard` rises as a level gets harder."""
    found = []
    dipped = set(dips)
    for i in range(len(hard) - 1):
        fell = hard[i] - hard[i + 1]
        if i + 1 in dipped:
            if fell <= 0:
                found.append({"rule": "dip", "pair": [names[i], names[i + 1]],
                              "said": f"{names[i + 1]} is no easier than "
                              f"{names[i]}, after which the set dips"})
        elif fell > step:
            found.append({"rule": "step", "pair": [names[i], names[i + 1]],
                          "said": f"{names[i + 1]} is easier than {names[i]} by "
                          f"{round(fell, 4)}, past the step of {step}"})
    for first, last in regions:
        if hard[last - 1] <= hard[first - 1]:
            found.append({"rule": "region", "pair": [names[first - 1], names[last - 1]],
                          "said": f"{names[last - 1]} is no harder than "
                          f"{names[first - 1]}, though the region rises"})
    return found


@operation("level.curve")
def curve(
    set: Annotated[str, Param("the set spec, a *.levels.toml under the project")],
    root: Annotated[str, Param("the project whose levels these are")] = ".",
) -> dict:
    """A level set's difficulty held to the shape its spec declares (§PW204).

    The spec names its `levels` in order, the probe's `probed` measure and `at` where
    in its spread, and the shape: `step`, the most difficulty may fall between
    neighbours, `regions` that each end harder than they start, and `dips`, positions
    the next level is easier after. Each break is answered as the pair of levels.
    """
    import tomllib

    config = load(root)
    here = config.root
    where = here / set
    try:
        spec = tomllib.loads(where.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise PolyweaveError("level.bad-set", f"{set} is not a TOML file to read",
                             "write the set spec as TOML at that path",
                             detail=str(exc)) from exc
    files = spec.get("levels")
    probed = str(spec.get("probed") or "")
    if not isinstance(files, list) or len(files) < 2 or not probed:
        raise PolyweaveError(
            "level.bad-set",
            f"{set} names no two levels in order, or no probed measure",
            'write levels = ["data/levels/level_001.json", ...] and probed = "won"')
    at = str(spec.get("at") or "p50")
    measures = _measures(config.table("levels").get("measures"))
    if probed not in measures:
        raise PolyweaveError(
            "level.bad-measures", f"{set} reads {probed!r}, which [levels.measures] "
            "does not declare", f"name one of {', '.join(measures)}", given=probed)
    step, regions, dips = _curve_rules(spec, len(files))
    sign = -1.0 if measures[probed]["direction"] == "higher" else 1.0
    names, values = [], []
    for one in files:
        path = here / str(one)
        names.append(Path(str(one)).stem)
        values.append(_value(_recorded(path, here), probed, at, path))
    found = _curve_findings(names, [sign * v for v in values], step, regions, dips)
    return {
        "ok": not found,
        "probed": probed,
        "at": at,
        "values": dict(zip(names, values, strict=True)),
        "findings": found,
        "says": f"{len(names)} levels by {probed} at {at}: "
        + ("the curve holds its shape" if not found
           else f"{len(found)} break(s), the first {found[0]['said']}"),
    }


def _set_at(document: Any, path: str, value: Any) -> None:
    """Put `value` at a dotted path (`moves`, `goals.0.count`), keeping an integer one
    an integer, and refusing a path the level does not have."""
    keys = path.split(".")
    node = document
    for key in keys[:-1]:
        if isinstance(node, list):
            node = node[int(key)] if key.isdigit() and int(key) < len(node) else None
        else:
            node = node.get(key) if isinstance(node, dict) else None
        if node is None:
            break
    last = keys[-1]
    held = (isinstance(node, list) and last.isdigit() and int(last) < len(node)) or (
        isinstance(node, dict) and last in node)
    if not held:
        raise PolyweaveError(
            "level.bad-set", f"the level has no {path} for a search to turn",
            "name each [search.<param>] as the dotted path of a key the level holds, "
            "such as moves or goals.0.count", given=path)
    was = node[int(last)] if isinstance(node, list) else node[last]
    turned = round(value) if isinstance(was, int) and not isinstance(was, bool) \
        else value
    if isinstance(node, list):
        node[int(last)] = turned
    else:
        node[last] = turned


def sample(report: Any, *, out: str, rung: Any = None, root: str = ".",
           inline: bool = False, level: str = "", **values: Any) -> dict:
    """One candidate of a level for search.sweep (§PW204): the level `fixed` names with
    each searched value put in, written at `out` as JSON, compiled and probed, so the
    spec's level predicates read it like any level."""
    from .level_schema import compile_level

    here = load(root).root
    source = here / level if level else None
    if source is None or not source.is_file() or source.suffix.lower() != ".json":
        raise PolyweaveError(
            "level.bad-set", f"a level search was given {level or 'no level'} to turn",
            'pass fixed = {"level": "data/levels/level_020.json"}, a JSON level under '
            "the project", given=level or None)
    document = json.loads(source.read_text(encoding="utf-8-sig"))
    for path, value in values.items():
        _set_at(document, path, value)
    target = Path(out)
    target = target if target.is_absolute() else here / target
    target.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(target, json.dumps(document, indent=1) + "\n")
    candidate = provenance.relative(target, here)
    # Held to the schema and compiled where the project declares one; with none, the
    # candidate is the file the game reads.
    if load(here).table("levels").get("schema"):
        candidate = compile_level(candidate, root=str(here))["compiled"]
    probe(candidate, root=str(here))
    return {"artefact": candidate, "values": values}


@operation("level.probe", kind="capture")
def probe(
    level: Annotated[str, Param("the level file the probe plays, under the project")],
    *,
    seeds: Annotated[
        int, Param("how many seeds, from 1; [levels] seeds where 0", lo=0)
    ] = 0,
    root: Annotated[str, Param("the Godot project the probe is in")] = ".",
) -> dict:
    """Play one level with the game's own probe and read back what it measured.

    Runs `[levels] probe` headless with the level and seeds 1 to N, reads one
    `level: seed=… name=…` line a seed, refuses a line that does not say exactly the
    `[levels.measures]` declared, and answers each measure at the declared percentiles
    and its mean. Written beside the level as `<level>.probe.json`, recorded, with how
    far each moved from the run before (§PW202).
    """
    from . import engine

    config = load(root)
    here = config.root
    table = config.table("levels")
    script = str(table.get("probe") or "")
    if not script:
        raise PolyweaveError(
            "level.no-probe",
            "polyweave.toml declares no [levels] probe to play a level",
            'write [levels] probe = "res://tools/level_probe.gd", a script of the '
            "game's that prints one level: line a seed")
    measures = _measures(table.get("measures"))
    count = int(seeds or table.get("seeds", 100))
    percentiles = [float(p) for p in table.get("percentiles", [10, 50, 90])]
    where = Path(level)
    where = where if where.is_absolute() else here / where
    if not where.is_file():
        raise PolyweaveError(
            "level.no-level", f"there is no level at {level}",
            "name the level's file as a path under the project", given=level)
    probe_path = here / script.removeprefix("res://")
    ran = engine.run(
        probe_path, expect=r"^level:", root=here, headless=True,
        args=("--", f"level={engine._as_res(where, here)}", f"seeds={count}"))
    log = Path(ran["log"])
    output = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
    if not ran["ok"]:
        raise PolyweaveError(
            "level.probe-failed", f"the probe did not finish playing {level}: "
            f"{ran['why'] or ran['verdict']}",
            "read the log, and run the probe on the level by hand to see it fail",
            detail=ran["log"])
    held = _aggregate(_read_lines(output, measures, count), percentiles)
    target = where.with_name(where.stem + ".probe.json")
    before = (json.loads(target.read_text(encoding="utf-8")).get("measured")
              if target.is_file() else None)
    version = VERSION.search(output)
    written = {"level": provenance.relative(where, here), "seeds": count,
               "percentiles": percentiles, "measures": measures, "measured": held}
    write_atomic(target, json.dumps(written, indent=1) + "\n")
    provenance.write(provenance.build(
        "capture", target,
        engine={"name": "godot", **({"version": version[1]} if version else {})},
        inputs=[provenance.source("level", where, root=here),
                provenance.source("probe", probe_path, root=here)],
        params={"seeds": count, "percentiles": percentiles, "measures": measures},
        root=here,
    ), root=here)
    shift = _moved(held, before)
    return {
        "probe": provenance.relative(target, here),
        "seeds": count,
        "measured": held,
        "moved": shift,
        "says": f"{level} over {count} seeds: "
        + ", ".join(f"{name} median {one.get('p50', one['mean'])}"
                    for name, one in held.items())
        + (f"; moved since the last run: {', '.join(shift)}" if shift
           else "; nothing moved since the last run" if before is not None else ""),
    }
