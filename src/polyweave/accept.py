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
from typing import Any

from . import measure as M
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
    unknown = sorted(set(declared) - {"asset", "rung", "predicate", "search"})
    if unknown:
        raise PolyweaveError(
            "spec.unknown-field",
            f"an acceptance spec has no {', '.join(unknown)}",
            "it takes asset, rung, [[predicate]] and [search.<param>]",
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
