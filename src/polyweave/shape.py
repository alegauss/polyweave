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
from typing import Annotated, Any

from . import measure
from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

#: Meshes this can render a silhouette of. Anything else is already a picture.
MESHES = (".glb", ".gltf", ".fbx")

#: Straight on, level: §6 fixes −Z as forward, so azimuth zero is the front of a thing.
FRONT = {"azimuth": 0.0, "elevation": 0.0}


def is_mesh(subject: Any) -> bool:
    return isinstance(subject, str | Path) and Path(subject).suffix.lower() in MESHES


class _Quiet:
    """Nothing to report to: these renders are steps inside one call."""

    def stage(self, stage, *, progress=None, note=None):
        """A bake's stage, which nobody is watching here."""

    def progress(self, value, *, note=None):
        """A bake's progress, which nobody is watching here."""

    def note(self, text):
        """A bake's remark, which nobody is watching here."""


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

    draw = bake or R.bake
    return draw(
        _Quiet(),
        out=str(out),
        model=str(mesh),
        rung=rung,
        root=str(root),
        inline=False,
        **FRONT,
    )


@operation("shape.check", kind="bake")
def check(
    subject: Annotated[Any, Param("the mesh, as a path under the project")],
    *,
    against: Annotated[str, Param("the drawing its silhouette must match")],
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
    threshold: Annotated[
        float, Param("the least IoU that passes; the project's if unset")
    ] = None,
    out: Annotated[str, Param("where the silhouette render is written")] = None,
    rung: Annotated[str, Param("the rung the silhouette is rendered at")] = "preview",
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


#: Frames a turntable takes by default: every 45 degrees round the up axis.
TURNS = 8

#: Where turntables are listed, so the review page can find two of one mesh (§PW176).
TURNTABLES = "turntables.json"


def turntable(
    mesh: str | Path,
    *,
    out: str | Path,
    against: str | Path | None = None,
    root: str | Path = ".",
    rung: str = "preview",
    frames: int = TURNS,
    bake: Any = None,
) -> dict:
    """A mesh turned at the rig's own camera, and its front view, for a person to see.

    Never a camera of the viewer's choosing: a mesh seen through another camera is a
    mesh seen differently. Each frame is the rig's elevation and distance with its
    azimuth stepped round the up axis, and the front view is the one the shape check
    scores, so `against`, the drawing that asked for the shape, can be laid over it.
    The frames and a `turntable.json` go in `out`, which is listed for the review page.
    """
    import json
    from datetime import UTC, datetime

    from . import provenance
    from . import render as R
    from .files import read_text_retrying, write_atomic
    from .render.rig import Rig

    config = load(root)
    here = config.root
    folder = Path(out) if Path(out).is_absolute() else here / out
    folder.mkdir(parents=True, exist_ok=True)
    draw = bake or R.bake
    base = Rig()
    turned = []
    for step in range(max(1, int(frames))):
        azimuth = (base.azimuth + step * 360.0 / max(1, int(frames))) % 360.0
        target = folder / f"turn_{step:02d}.png"
        draw(
            _Quiet(),
            out=str(target),
            model=str(mesh),
            rung=rung,
            root=str(here),
            inline=False,
            azimuth=azimuth,
            elevation=base.elevation,
        )
        turned.append(
            {"azimuth": round(azimuth, 3), "picture": provenance.relative(target, here)}
        )
    front = folder / "front.png"
    draw(
        _Quiet(),
        out=str(front),
        model=str(mesh),
        rung=rung,
        root=str(here),
        inline=False,
        **FRONT,
    )
    manifest = {
        "at": datetime.now(tz=UTC).isoformat(timespec="seconds"),
        "mesh": provenance.relative(here / mesh, here),
        "asset": Path(str(mesh)).stem,
        "rung": rung,
        "elevation": base.elevation,
        "frames": turned,
        "front": provenance.relative(front, here),
        "against": str(against) if against else None,
    }
    write_atomic(folder / "turntable.json", json.dumps(manifest, indent=2) + "\n")
    index = config.path("paths.work") / TURNTABLES
    listed = provenance.relative(folder / "turntable.json", here)
    held = [
        one for one in json.loads(read_text_retrying(index) or "[]") if one != listed
    ]
    write_atomic(index, json.dumps([*held, listed], indent=2) + "\n")
    return manifest


@operation("shape.turntable", kind="bake")
def turned(
    mesh: Annotated[str, Param("the mesh, as a path under the project")],
    *,
    out: Annotated[str, Param("the folder the frames are written into")],
    against: Annotated[str, Param("the drawing to lay over the front view")] = None,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
    rung: Annotated[str, Param("the rung the frames are rendered at")] = "preview",
    frames: Annotated[int, Param("how many frames round the up axis", lo=1)] = TURNS,
) -> dict:
    """A mesh turned at the rig's own camera, for the review page (§PW176)."""
    return turntable(
        mesh, out=out, against=against, root=root, rung=rung, frames=frames
    )


@operation("shape.silhouette", kind="bake")
def outlined(
    mesh: Annotated[str, Param("the mesh, as a path under the project")],
    *,
    out: Annotated[str, Param("where the silhouette is written")],
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
    rung: Annotated[str, Param("the rung it is rendered at")] = "preview",
) -> dict:
    """A mesh's silhouette, rendered and cut to its alpha, from the rig's own camera."""
    return silhouette(mesh, out=out, root=root, rung=rung)
