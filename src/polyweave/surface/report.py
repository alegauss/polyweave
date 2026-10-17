"""What the records say polyweave did here, per asset and in total (§PW444).

The loop's own ledger, what was bought and what each layer reports, read together: it
reads across ledgers, so it is the surface's.
"""

from __future__ import annotations

from typing import Annotated

from polyweave.kernel.config import load
from polyweave.kernel.describe import operation
from polyweave.loop.loop import (
    ROOT,
    WAYS,
    _change,
    _totals,
    _where,
    _with_verdicts,
    read,
    was_made,
)


@operation("loop.report")
def report(root: Annotated[str, ROOT] = ".") -> dict:
    """What the records say polyweave did here, per asset and in total (§PW444).

    A read, never an estimate: every figure is a sum over a file the project already
    keeps, and each section names that file under `from`. Per asset, each way's runs
    that made it (renders, cache hits, calls, credits, seconds, a person's minutes,
    rounds) and the verdicts given on it (accepted, overruled), with `compare` where
    both ways are recorded; then what was bought, per service, and how many candidates
    the picture gate refused before a person saw any. A figure no record holds is
    absent, never zero by assumption, so the report can be quoted as it stands.
    """
    from polyweave.kernel.layer import call, sections
    from polyweave.kernel.provenance import relative
    from polyweave.services import purchase

    config = load(root)
    here = config.root
    runs = read(root)
    ledger = relative(_where(root), here)
    assets = []
    for name in sorted({one["asset"] for one in runs}):
        mine = [one for one in runs if one["asset"] == name]
        ways = {}
        for way in WAYS:
            these = [one for one in mine if one["way"] == way]
            if not these:
                continue
            made = [one for one in these if was_made(one)]
            totals = _with_verdicts(_totals(made), these) if made else None
            verdicts = [v for one in these for v in one.get("verdicts", ())]
            ways[way] = {
                **({"made": {**totals, "rounds": len(made)}} if totals else {}),
                "verdicts": {
                    "given": len(verdicts),
                    "accepted": sum(1 for v in verdicts if v.get("person_accepted")),
                    "overruled": sum(
                        1 for v in verdicts
                        if v.get("person_accepted") != v.get("tool_passed")),
                },
            }
        entry = {"asset": name, "ways": ways, "from": ledger}
        if all(way in ways and "made" in ways[way] for way in WAYS):
            entry["compare"] = {
                key: _change(ways["before"]["made"][key], ways["after"]["made"][key])
                for key in ("renders", "seconds", "credits", "person_minutes", "calls")
            }
        assets.append(entry)
    bought: dict[str, dict] = {}
    # A lock keyed by name reads as entries too; another shape is refused (§PW457).
    for one in purchase.read(root):
        service = one.get("service") or "unnamed"
        row = bought.setdefault(service, {"service": service, "purchases": 0,
                                          "credits": 0.0, "reported": 0.0})
        row["purchases"] += 1
        row["credits"] = round(row["credits"] + float(one.get("credits") or 0.0), 6)
        if one.get("reported") is not None:
            row["reported"] = round(row["reported"] + float(one["reported"]), 6)
    answer = {
        "assets": assets,
        "totals": {**_totals([one for one in runs if was_made(one)]), "from": ledger},
    }
    if bought:
        answer["bought"] = {"services": list(bought.values()),
                            "from": relative(purchase.where(root), here)}
    # A layer's own section, where it has one to report: the picture gate's refusals.
    for key, target in sections("report").items():
        said = call(target, root)
        if said:
            answer[key] = said
    return answer
