"""What makes a render of this asset correct, as a file rather than as a memory.

`docs/specs/acceptance-spec.md` is the contract. The evidence is §PW12: nothing in
Cottony's repository states that the face should read the drawing's own colour or that
the silhouette should match the drawn outline. The knowledge exists — in commit messages
and in somebody's memory — so no later change can be checked against it and no search
can aim at it.

    spec = read("mascot.accept.toml")
    check(spec, "renders/mascot.png")   # per predicate: pass, value, margin

**Every predicate yields a margin, not only a verdict.** A pure boolean gives a search
a cliff and nothing to climb; the margin is what lets §PW13 converge on something rather
than wander. Written for one asset this documents intent; written for all of them it is
a regression suite nobody had to invent separately.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any

from . import measure as M
from .describe import Param, operation
from .errors import PolyweaveError
from .render.ladder import RUNGS, check_rung, lowest_rung

SUFFIX = ".accept.toml"

#: What a predicate may say, beyond the arguments its own measure takes. `min` and
#: `max` are the only comparisons: a predicate states a bound, never an expression.
BOUNDS = ("min", "max")
FIELDS = ("id", "measure", "region", "weight", *BOUNDS)

#: Arguments a predicate may pass through to the measure it names.
ARGUMENTS = ("target", "against", "display", "delta")


@dataclass(frozen=True)
class Predicate:
    """One checkable claim about a render."""

    id: str
    measure: str
    region: Any = None
    minimum: float | None = None
    maximum: float | None = None
    weight: float = 1.0
    arguments: dict = field(default_factory=dict)
    #: Where each bound came from, by side, for the bounds written as a table (§PW106).
    origins: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        out = {"id": self.id, "measure": self.measure, "weight": self.weight}
        if self.region is not None:
            out["region"] = self.region
        for side, value in (("min", self.minimum), ("max", self.maximum)):
            if value is None:
                continue
            origin = self.origins.get(side)
            out[side] = {"value": value, **origin} if origin else value
        out.update(self.arguments)
        return out


@dataclass(frozen=True)
class Spec:
    """One asset's acceptance spec."""

    asset: str
    rung: str | None
    predicates: tuple[Predicate, ...]
    search: dict
    path: Path | None = None
    #: The committed file this spec holds to its bar, relative to the project (§PW111).
    artefact: str | None = None
    #: Where the asset stands on screen: a capture and the region it named (§PW112).
    screen: dict | None = None

    def needs_rung(self) -> str:
        """The lowest rung a verdict on this asset may be taken at.

        Its own `rung` is a floor and never a ceiling: it raises what the predicates
        require and can never lower it.
        """
        return lowest_rung([p.measure for p in self.predicates], self.rung)


# -- reading ------------------------------------------------------------------------


def read(path: str | Path, root: str | Path = ".") -> Spec:
    """Read an acceptance spec, refusing anything it could not check."""
    where = Path(path)
    if not where.is_absolute():
        where = Path(root) / where
    if not where.is_file():
        raise PolyweaveError(
            "spec.missing",
            f"there is no acceptance spec at {where}",
            f"write one as <asset>{SUFFIX}, beside the asset or under [paths] specs",
        )
    try:
        declared = tomllib.loads(where.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise PolyweaveError(
            "spec.malformed",
            f"{where.name} is not readable as TOML",
            "fix the syntax the detail below points at",
            detail=str(exc),
        ) from exc
    return parse(declared, where)


def parse(declared: dict, path: Path | None = None) -> Spec:
    unknown = sorted(
        set(declared) - {"asset", "artefact", "screen", "rung", "predicate", "search"}
    )
    if unknown:
        raise PolyweaveError(
            "spec.unknown-field",
            f"an acceptance spec has no {', '.join(unknown)}",
            "it takes asset, artefact, screen, rung, [[predicate]] and "
            "[search.<param>]",
            given=unknown[0],
            allowed=("asset", "artefact", "screen", "rung", "predicate", "search"),
        )
    screen = declared.get("screen")
    if screen is not None and (
        not isinstance(screen, dict)
        or set(screen) != {"capture", "region"}
        or not all(isinstance(v, str) and v for v in screen.values())
    ):
        raise PolyweaveError(
            "spec.unknown-field",
            f"screen is {screen!r}, which does not say where the asset stands",
            'write screen = { capture = "<picture>", region = "<name>" }, the region '
            "being one the capture script printed",
            allowed=("capture", "region"),
            example='screen = { capture = "captures/title.png", region = "star" }',
            at="screen",
        )
    rung = declared.get("rung")
    if rung is not None:
        check_rung(rung)

    raw = declared.get("predicate") or []
    if not raw:
        raise PolyweaveError(
            "spec.no-predicates",
            "an acceptance spec with no predicates checks nothing",
            "add a [[predicate]] naming a measure and a bound",
        )
    predicates = tuple(_predicate(entry, index) for index, entry in enumerate(raw))
    seen: dict[str, int] = {}
    for p in predicates:
        if p.id in seen:
            raise PolyweaveError(
                "spec.duplicate-id",
                f"two predicates are both called {p.id!r}",
                "give each one a name of its own; the trace addresses them by it",
            )
        seen[p.id] = 1
    return Spec(
        asset=declared.get("asset") or (path.name.split(".")[0] if path else ""),
        rung=rung,
        predicates=predicates,
        search=_search(declared.get("search") or {}),
        path=path,
        artefact=str(declared["artefact"]) if declared.get("artefact") else None,
        screen=dict(screen) if screen else None,
    )


def _predicate(entry: dict, index: int) -> Predicate:
    if "id" not in entry:
        raise PolyweaveError(
            "spec.anonymous-predicate",
            f"the predicate at position {index + 1} has no id",
            "give it one; a search reports a score per predicate and the trace "
            "addresses them by name, so an anonymous one cannot be discussed",
        )
    name = str(entry["id"])
    if "measure" not in entry:
        raise PolyweaveError(
            "spec.no-measure",
            f"the predicate {name!r} names no measure",
            f"name one of {', '.join(sorted(M.COMPUTES))}",
        )
    unknown = sorted(set(entry) - set(FIELDS) - set(ARGUMENTS))
    if unknown:
        raise PolyweaveError(
            "spec.unknown-field",
            f"the predicate {name!r} has no {', '.join(unknown)}",
            f"a predicate takes {', '.join(FIELDS)}, and "
            f"{', '.join(ARGUMENTS)} for the measure",
            given=unknown[0],
            allowed=(*FIELDS, *ARGUMENTS),
            at=f"predicate.{name}",
        )
    M.resolve(str(entry["measure"]))  # refuses a name the vocabulary does not carry
    if not any(b in entry for b in BOUNDS):
        raise PolyweaveError(
            "spec.no-bound",
            f"the predicate {name!r} states no bound, so nothing can fail it",
            "give it a min, a max, or both",
        )
    return Predicate(
        id=name,
        measure=str(entry["measure"]),
        region=entry.get("region"),
        minimum=_number(entry, "min", name),
        maximum=_number(entry, "max", name),
        weight=float(entry.get("weight", 1.0)),
        arguments={k: entry[k] for k in ARGUMENTS if k in entry},
        origins={
            side: found
            for side in BOUNDS
            if (found := _origin(entry, side, name)) is not None
        },
    )


#: Where a bound's number came from (§PW106): read off an artefact, put around a
#: measured value by hand, or agreed by a person on a look.
ORIGINS = ("measured", "margin", "person")

#: What a bound written as a table may say beside its number. `spread` is how far the
#: measure moved on its own under harmless changes, where calibration found it (§PW107).
BOUND_KEYS = ("value", "origin", "measured", "spread", "date", "why")


def _origin(entry: dict, key: str, name: str) -> dict | None:
    """A bound's origin, where it was written as a table; None for a bare number."""
    stated = entry.get(key)
    if not isinstance(stated, dict):
        return None
    unknown = sorted(set(stated) - set(BOUND_KEYS))
    if unknown:
        raise PolyweaveError(
            "spec.unknown-field",
            f"{name}'s {key} has no {', '.join(unknown)}",
            f"a bound written as a table takes {', '.join(BOUND_KEYS)}",
            given=unknown[0],
            allowed=BOUND_KEYS,
            at=f"predicate.{name}.{key}",
        )
    origin = stated.get("origin")
    if origin not in ORIGINS:
        raise PolyweaveError(
            "spec.bad-origin",
            f"{name}'s {key} says it came from {origin!r}",
            f"say which of {', '.join(ORIGINS)} it is; a bound that cannot say where "
            "it came from is the guess this field exists to expose",
        )
    return {k: v for k, v in stated.items() if k != "value"}


def _number(entry: dict, key: str, name: str) -> float | None:
    if key not in entry:
        return None
    value = entry[key]
    if isinstance(value, dict):
        value = value.get("value")
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise PolyweaveError(
            "spec.bad-bound",
            f"{name}'s {key} is {value!r}, which is not a number",
            "a bound is a number; anything else is a measure that does not exist yet",
        )
    return float(value)


def _search(declared: dict) -> dict:
    """What a search is permitted to turn, and nothing else.

    A parameter not named here is not searched, whatever an optimiser would like. It can
    tune the exposure; it cannot decide the asset should be twice as large.
    """
    out = {}
    for name, bounds in declared.items():
        unknown = sorted(set(bounds) - {"min", "max", "step"})
        if unknown:
            raise PolyweaveError(
                "spec.unknown-field",
                f"[search.{name}] has no {', '.join(unknown)}",
                "a search range takes min, max and step",
                given=unknown[0],
                allowed=("min", "max", "step"),
                at=f"search.{name}",
            )
        if "min" not in bounds or "max" not in bounds:
            raise PolyweaveError(
                "spec.no-bound",
                f"[search.{name}] needs both a min and a max",
                "a range open at one end is not a range a search can cover",
            )
        out[name] = dict(bounds)
    return out


# -- checking ------------------------------------------------------------------------


def margin(value: float, low: float | None, high: float | None) -> float:
    """How comfortably a value sits inside its bound, in 0–1.

    Continuous on both sides of the bound on purpose. A pure boolean gives a search a
    cliff and nothing to climb, so a failing value still reports how close it came.
    """
    scores = []
    if low is not None:
        scores.append(1.0 if value >= low else (value / low if low > 0 else 0.0))
    if high is not None:
        scores.append(1.0 if value <= high else (high / value if value > 0 else 0.0))
    if not scores:
        return 1.0
    return round(float(max(0.0, min(1.0, min(scores)))), 6)


def headroom(value: float, low: float | None, high: float | None) -> float | None:
    """How far inside its bound a value sits, as a share of the room it had (§PW104).

    `margin` is 1.0 anywhere inside, which is right for the verdict and says nothing
    about how close a pass came: the stars' gold facet passed at 0.4695 under 0.47.
    This is the distance to the nearer bound, as a share of the band where there are
    two and of the bound itself where there is one. Below zero is outside. None where
    nothing bounds the value.
    """
    shares = []
    if low is not None and high is not None and high > low:
        shares.append(min(value - low, high - value) / (high - low))
    else:
        if low is not None:
            shares.append((value - low) / (abs(low) or 1.0))
        if high is not None:
            shares.append((high - value) / (abs(high) or 1.0))
    return round(float(min(shares)), 6) if shares else None


def check(
    spec: Spec,
    subject: Any,
    *,
    rung: str | None = None,
    alpha_floor: float | None = None,
    root: str | Path = ".",
) -> dict:
    """Every predicate against one render: its value, whether it holds, and by how much.

    The rung is carried through and reported. A verdict taken lower than the spec's own
    floor is refused rather than quietly accepted, because that is the whole difference
    between a gate and an opinion.

    This has a root, so the tolerance is resolved here and the measures below take it
    (§PW40). The old default of zero disagreed with the 0.02 the config declares, and a
    verdict taken against the wrong subject is the opinion this is meant to replace.
    """
    from .config import load as load_config

    floor = float(load_config(root).get("tolerance.alpha_floor", alpha_floor))
    needed = spec.needs_rung()
    if rung is not None and RUNGS.index(rung) < RUNGS.index(needed):
        raise PolyweaveError(
            "spec.rung-too-low",
            f"{spec.asset} is judged at {needed!r} and this render is a {rung!r}",
            f"render it at {needed!r}, which is what its predicates need",
        )

    results = []
    for p in spec.predicates:
        arguments = dict(p.arguments)
        for key in ("against", "target"):
            if key == "against" and isinstance(arguments.get(key), str):
                arguments[key] = str(Path(root) / arguments[key])
        taken = M.measure(
            subject,
            [p.measure],
            region=p.region,
            alpha_floor=floor,
            rung=rung,
            **arguments,
        )
        value = taken[0]["value"]
        scalar = _scalar(value, p)
        results.append(
            {
                "id": p.id,
                "measure": p.measure,
                "region": taken[0]["region"],
                "rung": rung,
                "value": value,
                "min": p.minimum,
                "max": p.maximum,
                "weight": p.weight,
                "passed": _passes(scalar, p),
                "margin": margin(scalar, p.minimum, p.maximum),
                "headroom": headroom(scalar, p.minimum, p.maximum),
                **_bound(p, scalar),
            }
        )

    total = sum(r["weight"] for r in results) or 1.0
    bounded = [r for r in results if r["headroom"] is not None]
    tightest = min(bounded, key=lambda r: r["headroom"]) if bounded else None
    return {
        "asset": spec.asset,
        "rung": rung,
        "needs_rung": needed,
        "passed": all(r["passed"] for r in results),
        "score": round(sum(r["margin"] * r["weight"] for r in results) / total, 6),
        "predicates": results,
        "failed": [r["id"] for r in results if not r["passed"]],
        # The smallest room any bound left, and whose it was (§PW104).
        "headroom": tightest["headroom"] if tightest else None,
        "tightest": tightest["id"] if tightest else None,
        # Misses on a bound somebody guessed, where the number may be what is wrong.
        "guessed": [
            r["id"]
            for r in results
            if not r["passed"] and r["bound"].get("origin") == "margin"
        ],
    }


@operation("accept.check")
def checked(
    spec: Annotated[str, Param("the acceptance spec, as a path under the project")],
    subject: Annotated[str, Param("the picture to check, as a path under the project")],
    rung: Annotated[
        str, Param("the rung the picture was made at, if known", choices=RUNGS + ("",))
    ] = "",
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """Check one picture against one spec: each predicate's value, verdict and margin.

    The form a caller reaches by name: paths in, the answer out. `check` is the same
    work on a `Spec` already in memory.
    """
    here = Path(root)
    picture = Path(subject) if Path(subject).is_absolute() else here / subject
    return check(read(spec, here), picture, rung=rung or None, root=here)


def _bound(p: Predicate, value: float) -> dict:
    """The bound that decided a predicate, where it came from, and what a miss means.

    §PW106: a bound read off pixels, a margin put over one and a value a person agreed
    to were all spelled `max = 0.37`, so a miss on a guess read exactly like a miss on
    a look. The side is the one broken, or the nearer one where nothing is.
    """
    low, high = p.minimum, p.maximum
    if low is not None and value < low:
        side = "min"
    elif high is not None and value > high:
        side = "max"
    elif low is not None and high is not None:
        side = "min" if value - low <= high - value else "max"
    else:
        side = "min" if low is not None else "max"
    origin = p.origins.get(side) or {}
    answer = {"bound": {"side": side, **origin}}
    broken = (side == "min" and value < low) or (side == "max" and value > high)
    if broken and origin:
        answer["why"] = _meaning(p.id, side, origin)
    return answer


def _meaning(name: str, side: str, origin: dict) -> str:
    kind = origin["origin"]
    if kind == "margin":
        guarded = origin.get("measured")
        return (
            f"{name} missed its {side}, a margin put by hand"
            + (f" over the measured {guarded:g}" if guarded is not None else "")
            + ": the number may be what is wrong, not the look"
        )
    if kind == "person":
        when = origin.get("date")
        return (
            f"{name} missed its {side}, which a person agreed on"
            + (f" {when}" if when else "")
            + ": the look moved"
        )
    read = origin.get("measured")
    noise = origin.get("spread")
    return (
        f"{name} missed its {side}, read off an artefact"
        + (f" at {read:g}" if read is not None else "")
        + (f" with {noise:g} of noise" if noise is not None else "")
        + ": the render drifted from what it was measured on"
    )


# -- the specs as a gate ---------------------------------------------------------------


@operation("accept.verify")
def verify(
    root: Annotated[str, Param("the project the specs and artefacts are under")] = ".",
    *,
    under: Annotated[str, Param("where the specs are; [paths] specs by default")] = "",
) -> dict:
    """Every spec under `[paths] specs` against the artefact it names (§PW111).

    A spec is consulted while a search runs and not after it, so a sprite overwritten
    after it was accepted was never held to the bar it passed. This needs no render:
    each spec's `artefact` is checked as it sits on disk, at the rung its own record
    says it was made at where there is one. A spec naming no artefact is reported as
    `unanchored` rather than given a path guessed from its name, which would be one
    project's layout compiled in.

    `passed` is false when any artefact fails, is missing, or its spec is refused, so a
    CI job fails on it; an unanchored spec is said, not failed.

    A spec with a `screen` gets a second answer, on the capture (§PW112), and the spec
    fails where either does. Where the bake passes and the screen fails, `disagree`
    says the engine draws it differently, which is the finding the second check is for.
    """
    from . import provenance
    from .config import load as load_config

    here = Path(root).resolve()
    folder = Path(under) if under else load_config(here).path("paths.specs")
    folder = folder if folder.is_absolute() else here / folder
    results = []
    for found in sorted(folder.rglob(f"*{SUFFIX}")) if folder.is_dir() else ():
        one = {"spec": provenance.relative(found, here)}
        try:
            spec = read(found)
        except PolyweaveError as refused:
            results.append({**one, "status": "refused", "refusal": refused.as_dict()})
            continue
        one.update(asset=spec.asset, artefact=spec.artefact, **_baked(spec, here))
        if spec.screen:
            one["screen"] = _attempt(lambda s=spec: check_screen(s, root=here))
            one["status"] = _worse(one["status"], one["screen"]["status"])
            if one.get("baked") == "passed" and one["screen"]["status"] == "failed":
                one["disagree"] = (
                    f"{spec.asset} passes baked and fails on screen: the engine "
                    "draws it differently from the bake"
                )
        results.append(one)
    counts = {
        status: sum(1 for r in results if r["status"] == status)
        for status in ("passed", "failed", "missing", "refused", "unanchored")
    }
    return {
        "specs": results,
        "counts": counts,
        "passed": not (counts["failed"] or counts["missing"] or counts["refused"]),
    }


#: How bad each answer is, worst last: a spec reads as the worse of its two answers.
_ORDER = ("unanchored", "passed", "failed", "missing", "refused")


def _worse(one: str, other: str) -> str:
    return max(one, other, key=_ORDER.index)


def _failed(checked: dict) -> list[str]:
    return [
        r.get("why") or f"{r['id']}: {r['measure']} is {r['value']:g}"
        for r in checked["predicates"]
        if not r["passed"]
    ]


def _attempt(checking) -> dict:
    """One check as a status and what failed, a refusal kept rather than raised."""
    try:
        checked = checking()
    except PolyweaveError as refused:
        return {"status": "refused", "refusal": refused.as_dict()}
    return {
        "status": "passed" if checked["passed"] else "failed",
        "failed": _failed(checked),
        **({"box": checked["screen"]["box"]} if "screen" in checked else {}),
    }


def _baked(spec: Spec, here: Path) -> dict:
    """The spec against its committed artefact, at the rung its record names."""
    from . import provenance

    if not spec.artefact:
        return {"status": "unanchored"}
    picture = here / spec.artefact
    if not picture.is_file():
        return {"status": "missing", "baked": "missing"}
    try:
        made_at = provenance.read(picture, here).get("rung")
    except PolyweaveError:
        made_at = None
    found = _attempt(lambda: check(spec, picture, rung=made_at, root=here))
    return {**found, "baked": found["status"], "rung": made_at}


@operation("accept.check_screen")
def check_screen(
    spec: Annotated[str, Param("the acceptance spec, as a path under the project")],
    *,
    root: Annotated[str, Param("the project the spec and capture are under")] = ".",
) -> dict:
    """The same spec, held to where the asset stands in a capture (§PW112).

    Once the game loads a mesh, its material is what the player sees and the bake is a
    reference. The capture's record carries the rectangles its script printed, and the
    spec's `screen` names one; the predicates are checked on that crop exactly as they
    are on a bake, so the bar stays one file and moving it moves both checks.
    """
    import numpy as np

    from . import provenance
    from .image import Image, load

    if not isinstance(spec, Spec):
        spec = read(spec, root)
    if not spec.screen:
        raise PolyweaveError(
            "spec.no-screen",
            f"{spec.asset} says nothing about where it stands on screen",
            'add screen = { capture = "<picture>", region = "<name>" } to the spec',
        )
    here = Path(root).resolve()
    picture = here / spec.screen["capture"]
    named = provenance.read(picture, here).get("regions") or {}
    box = named.get(spec.screen["region"])
    if box is None:
        raise PolyweaveError(
            "spec.no-screen",
            f"{spec.screen['capture']} names no region {spec.screen['region']!r}",
            "have the capture script print `region: "
            f"{spec.screen['region']}=x0,y0,x1,y1`, or name one of: "
            + (", ".join(sorted(named)) or "it printed none"),
        )
    whole = load(picture)
    x0, y0, x1, y1 = (int(v) for v in box)
    crop = Image(
        path=None,
        rgba=np.ascontiguousarray(whole.rgba[y0:y1, x0:x1]),
        had_alpha=whole.had_alpha,
    )
    found = check(spec, crop, root=here)
    found["screen"] = {**spec.screen, "box": [x0, y0, x1, y1]}
    return found


def _scalar(value: Any, p: Predicate) -> float:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    raise PolyweaveError(
        "spec.unbounded-measure",
        f"{p.measure} answers with {type(value).__name__}, which a bound cannot hold",
        f"bound a statistic of it, such as {p.measure}_p99",
    )


def _passes(value: float, p: Predicate) -> bool:
    if p.minimum is not None and value < p.minimum:
        return False
    return not (p.maximum is not None and value > p.maximum)
