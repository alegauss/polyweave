"""Checking a generated shape against the drawing that asked for it.

The evidence is §PW16: Cottony sent a wide low cap on a short stem and got back a tall
dome on a long stem. Thirty credits to learn the shape was not respected, discovered
only once the money was gone.

The check that would have caught it is cheap — render the front silhouette and compare
it against the drawing by intersection over union — and **nothing about it has to happen
after payment**:

    check("preview.png", against="concept/cap.png", root=".")   # the service's preview
    check("paid.glb", against="concept/cap.png", root=".")      # or the mesh itself

Either way this becomes part of a fetch rather than something a person remembers to do
afterwards, and a fetch that fails it is a failure **with a picture attached**, never
accepted in silence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import measure
from .config import load
from .errors import PolyweaveError

#: Meshes this can render a silhouette of. Anything else is already a picture.
MESHES = (".glb", ".gltf", ".fbx")

#: Straight on, level: §6 fixes −Z as forward, so azimuth zero is the front of a thing.
FRONT = {"azimuth": 0.0, "elevation": 0.0}


def is_mesh(subject: Any) -> bool:
    return isinstance(subject, str | Path) and Path(subject).suffix.lower() in MESHES


def silhouette(
    mesh: str | Path,
    *,
    out: str | Path,
    root: str | Path = ".",
    rung: str = "preview",
    bake: Any = None,
) -> dict:
    """Render the front view of a mesh, for its outline and nothing else.

    The project's own rig, straight on. Only the alpha is read, so the lighting does not
    matter — but it is the same rig regardless, because a silhouette taken through a
    different camera is a silhouette of something else.
    """
    from . import render as R

    class Quiet:
        """Nothing to report to: this is one render inside a check."""

        def stage(self, stage, *, progress=None, note=None):
            pass

        def progress(self, value, *, note=None):
            pass

        def note(self, text):
            pass

    draw = bake or R.bake
    return draw(
        Quiet(),
        out=str(out),
        model=str(mesh),
        rung=rung,
        root=str(root),
        inline=False,
        **FRONT,
    )


def check(
    subject: Any,
    *,
    against: str | Path,
    root: str | Path = ".",
    threshold: float | None = None,
    out: str | Path | None = None,
    rung: str = "preview",
) -> dict:
    """Does this shape hold against the drawing that asked for it.

    `subject` is a mesh, which gets rendered, or a picture the service already gave —
    a preview, however low its resolution, is the cheapest place to find this out.
    """
    where = Path(root).resolve()
    reference = Path(against)
    if not reference.is_absolute():
        reference = where / reference
    if not reference.is_file():
        raise PolyweaveError(
            "fetch.no-reference",
            f"there is no drawing at {reference} to check the shape against",
            "point `against` at the drawing that asked for this shape",
        )

    bar = float(load(root).get("tolerance.silhouette_iou", threshold))
    rendered = None
    if is_mesh(subject):
        picture = Path(out) if out else where / ".polyweave" / "shape" / "front.png"
        if not picture.is_absolute():
            picture = where / picture
        rendered = silhouette(subject, out=picture, root=where, rung=rung)
    else:
        picture = Path(subject)
        if not picture.is_absolute():
            picture = where / picture

    taken = measure.measure(
        picture,
        ["silhouette_iou", "silhouette_centroid_offset", "silhouette_bbox_delta"],
        against=reference,
        region="frame",
    )
    found = measure.summarise(taken)
    iou = found["silhouette_iou"]
    return {
        "holds": iou >= bar,
        "silhouette_iou": iou,
        "threshold": bar,
        "centroid_offset": found["silhouette_centroid_offset"],
        "bbox_delta": found["silhouette_bbox_delta"],
        "picture": str(picture),
        "against": str(reference),
        "rendered": rendered is not None,
        "cached": bool(rendered and rendered.get("cached")),
        "why": ""
        if iou >= bar
        else f"the silhouette overlaps the drawing by {iou}, under a bar of {bar}",
    }


def require(subject: Any, **how: Any) -> dict:
    """The same check, as a gate: a shape that does not hold stops the fetch.

    Never accepted in silence, and the refusal carries the picture: "it came back
    wrong" is not actionable and a file somebody can open is.
    """
    found = check(subject, **how)
    if not found["holds"]:
        raise PolyweaveError(
            "fetch.shape-rejected",
            f"the shape does not match the drawing: {found['why']}",
            f"look at {found['picture']} beside {found['against']}, then ask again "
            f"with a clearer reference — the centroid is "
            f"{found['centroid_offset']}px out and the box differs by "
            f"{found['bbox_delta']}px",
        )
    return found
