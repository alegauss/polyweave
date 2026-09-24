"""A voxel model's proportions found against a reference, not guessed (§PW98).

The author declares the parts, what they mean and how far each may move; the search
finds the proportions. The reference is a drawing's alpha, or a mesh — a model bought
from the service, say — projected the way `normalise.project` projects one. So a fetched
ship becomes the target a declared ship is fitted to, not a mesh to chop into cubes.

**Each sample is a voxel build, not a render.** Milliseconds, so the search can afford
hundreds where a render ladder affords dozens. The measure is the overlap of the model's
silhouette with the reference's, per view, both fitted to their own bounds on one grid
the way `normalise.fitted` frames every silhouette — so what is compared is outline and
proportion and never framing.

**The voxel checks are constraints.** A sample that floats cells or breaks the project's
budget scores zero: a fit that only works by leaving a piece hanging in the air is not a
fit.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ..accept import Spec
from ..errors import PolyweaveError
from ..normalise import GRID, drawing, fitted, overlap, project
from .tuning import addressable

__all__ = ["VIEWS", "fit", "silhouettes"]

#: The views a model can be compared in, as the contact sheet draws them (§PW94).
VIEWS = ("front", "side", "top")

#: Findings that make a sample worthless whatever its overlap.
DISQUALIFY = ("floating", "budget")

#: How the reference mesh is turned so `normalise.project`, which looks along +Z with
#: +Y up, sees it from each view: from +X for the side, from +Y for the top.
_TURNED = {
    "front": lambda v: v,
    "side": lambda v: np.stack([-v[:, 2], v[:, 1], v[:, 0]], axis=1),
    "top": lambda v: np.stack([v[:, 0], v[:, 2], -v[:, 1]], axis=1),
}


def silhouettes(model: dict, *, grid: int = GRID) -> dict[str, np.ndarray]:
    """A voxel model's outline in each view, rows top to bottom, fitted to the grid."""
    filled = np.zeros(tuple(model["size"]), dtype=bool)
    cells = model["cells"]
    if len(cells["x"]):
        filled[
            (np.asarray(cells["x"]), np.asarray(cells["y"]), np.asarray(cells["z"]))
        ] = True
    front = filled.any(axis=2).T[::-1, :]  # x across, y up
    side = filled.any(axis=0)[::-1, ::-1]  # -z across, y up
    top = filled.any(axis=1).T[::-1, :]  # x across, the front (-z) at the bottom
    return {
        name: fitted(mask, grid=grid)
        for name, mask in {"front": front, "side": side, "top": top}.items()
    }


def _references(reference: Any, views: tuple, grid: int, root: Path) -> dict:
    """The reference's outline in each view the fit is scored on."""
    from ..config import load

    if isinstance(reference, dict):
        mesh = reference
    else:
        where = Path(reference)
        if not where.is_absolute():
            where = root / where
        if where.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
            if views != ("front",):
                raise PolyweaveError(
                    "geom.bad-fit",
                    f"{where.name} is one drawing, and it can only be the front view",
                    "fit a drawing on views = ['front'], or give a mesh for more",
                )
            floor = float(load(root).get("tolerance.alpha_floor"))
            return {"front": drawing(where, grid=grid, alpha_floor=floor)}
        from ..normalise import read_mesh

        mesh = read_mesh(where)
    points = np.asarray(mesh["vertices"], dtype=float)
    return {
        view: project(
            {"vertices": _TURNED[view](points), "faces": mesh["faces"]}, grid=grid
        )
        for view in views
    }


def _ranges(document: dict, ranges: dict | None) -> dict:
    """What the fit may move: the call's ranges, or the document's own `[search]`."""
    found = dict(ranges or document.get("search") or {})
    if not found:
        raise PolyweaveError(
            "geom.bad-fit",
            f"{document['name']} names no parameter the fit may move",
            "give it ranges, or a [search.<param>] table with min and max in the "
            "document",
        )
    addressable(document, found)
    return found


def fit(
    document: dict,
    reference: Any,
    *,
    ranges: dict | None = None,
    views: Any = ("front",),
    root: str | Path = ".",
    budget: int = 400,
    points: int = 7,
    grid: int = GRID,
    sheet: str | Path | None = None,
) -> dict:
    """Search a voxel model's declared parameters for the best overlap with a reference.

    `reference` is a drawing's path, a mesh's path or a mesh; `views` are the ones the
    score is the mean over. The answer is the best parameters, the score per view, the
    model they build and, with `sheet`, its contact sheet written there.
    """
    from .. import search as S
    from . import voxel_sheet, voxels

    views = tuple(views)
    unknown = [one for one in views if one not in VIEWS]
    if unknown or not views:
        raise PolyweaveError(
            "geom.bad-fit",
            f"{', '.join(unknown) or 'no view'} is not a view a model is compared in",
            f"name some of {', '.join(VIEWS)}",
        )
    here = Path(root).resolve()
    wanted = _references(reference, views, grid, here)
    permitted = _ranges(document, ranges)

    def judge(values: dict) -> dict:
        try:
            made = voxels.voxelize(document, root=here, **values)
        except PolyweaveError as refused:
            return {
                "passed": False,
                "score": 0.0,
                "failed": [refused.code],
                "why": refused.message,
            }
        seen = silhouettes(made, grid=grid)
        per_view = {view: overlap(seen[view], wanted[view]) for view in views}
        broken = [
            one["check"]
            for one in made["checks"]["findings"]
            if one["check"] in DISQUALIFY
        ]
        score = 0.0 if broken else float(np.mean(list(per_view.values())))
        return {
            "passed": False,
            "score": score,
            "views": per_view,
            "failed": broken,
            "predicates": [
                {"id": view, "value": value, "passed": None, "margin": value}
                for view, value in per_view.items()
            ],
        }

    spec = Spec(asset=document["name"], rung=None, predicates=(), search=permitted)
    found = S.search(spec, judge, budget=budget, points=points)
    made = voxels.voxelize(document, root=here, **found["best"])
    answer = {
        "best": found["best"],
        "score": found["score"],
        "views": judge(found["best"]).get("views", {}),
        "spent": found["spent"],
        "stopped": found["stopped"],
        "model": made,
        "says": made["says"],
    }
    if sheet:
        where = Path(sheet)
        if not where.is_absolute():
            where = here / where
        answer["sheet"] = voxel_sheet.sheet(made, where)["sheet"]
    return answer
