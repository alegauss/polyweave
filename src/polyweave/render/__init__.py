"""Rendering, from the cheapest rung that can answer the question.

    bake(report, model="mascot.glb", rung="sphere")     # three seconds
    bake(report, model="mascot.glb", asking=["silhouette_iou"])   # picks `preview`

A caller names what it wants to know and the ladder picks the rung; a caller that names
a rung gets that one. Either way the answer **says which rung it came from**, in the
result and in the record beside the picture, so a verdict taken at the sphere is never
mistaken for one taken at the top.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Annotated

from .. import cache as store
from .. import measure, post, provenance
from ..config import load
from ..describe import Param, operation
from ..errors import PolyweaveError
from .ladder import CARRIES, RUNGS, check_rung, enabled, lowest_rung, rung_for
from .rig import Rig, as_params

#: How much of the real mesh a preview keeps. Enough face count for a silhouette, far
#: less than a final render pays for.
PREVIEW_RATIO = 0.25

__all__ = [
    "CARRIES",
    "PREVIEW_RATIO",
    "RUNGS",
    "Rig",
    "bake",
    "check_rung",
    "enabled",
    "lowest_rung",
    "plan",
    "rung_for",
]


def plan(
    rung: str | None = None,
    asking: list[str] | None = None,
    *,
    floor: str | None = None,
    root: str | Path = ".",
) -> dict:
    """Which rung will answer, how big it will be, and why that one.

    Read-only, and the call to make before spending anything: it says what a render
    would cost before the render happens.
    """
    config = load(root)
    offered = enabled(config.get("render.rungs"))
    if rung is not None:
        chosen = check_rung(rung)
        why = "named by the caller"
    elif asking:
        chosen = lowest_rung(asking, floor)
        why = f"the lowest rung that carries {', '.join(sorted(set(asking)))}"
    else:
        chosen = check_rung(floor) if floor else offered[0]
        why = "the asset's own floor" if floor else "the cheapest rung enabled"

    if chosen not in offered:
        raise PolyweaveError(
            "render.rung-disabled",
            f"this project does not enable the {chosen!r} rung, and the question "
            f"needs it",
            f"add {chosen!r} to `[render] rungs`, which holds {', '.join(offered)}",
        )
    samples = config.get("render.samples")
    if chosen not in samples:
        raise PolyweaveError(
            "render.no-samples",
            f"`[render] samples` says nothing for the {chosen!r} rung",
            f"set samples.{chosen}, beside {', '.join(sorted(samples)) or 'nothing'}",
        )
    return {
        "rung": chosen,
        "why": why,
        "carries": CARRIES[chosen],
        "size": _size_for(config, chosen),
        "samples": int(samples[chosen]),
        "seed": int(config.get("render.seed")),
        "subject": "primitive" if chosen == "sphere" else "mesh",
        "decimate": PREVIEW_RATIO if chosen == "preview" else 1.0,
        "enabled": list(offered),
    }


def _from_cache(hit, out_path, where, chosen, started, inline: bool) -> dict:
    """A hit, **reported as a hit**.

    A caller timing a sweep needs to know what it actually measured; a cache that
    silently answers in four milliseconds makes a benchmark meaningless.
    """
    store.take(hit, out_path)
    record = hit["record"]
    landed = {**record["artefact"], "path": provenance.relative(out_path, where)}
    provenance.write({**record, "artefact": landed}, root=where)
    answer = {
        "artefact": provenance.relative(out_path, where),
        "rung": record.get("rung", chosen["rung"]),
        "why": chosen["why"],
        "size": chosen["size"],
        "samples": chosen["samples"],
        "elapsed_s": round(time.monotonic() - started, 3),
        "cached": True,
        "asserted": {},
        "measurements": [],
        "cache_key": hit["key"],
        "recorded": record.get("measurements", {}),
    }
    if inline:
        answer["image"] = measure.inline_image(out_path)
    return answer


def _size_for(config, rung: str) -> int:
    if rung == "final":
        return int(config.get("render.final_size"))
    return int(config.get("render.preview_size"))


@operation(
    "render.bake",
    produces="render",
    kind="bake",
    injects=("report",),
)
def bake(
    report,
    out: Annotated[str, Param("where to write the picture, under the project")],
    model: Annotated[
        str, Param("the mesh to render; not read at the sphere rung")
    ] = "",
    rung: Annotated[str, Param("which rung to render at", choices=RUNGS)] = "",
    asking: Annotated[
        list, Param("the measures the answer has to carry, if no rung is named")
    ] = (),
    floor: Annotated[
        str,
        Param("the lowest rung a verdict on this asset may be taken at", choices=RUNGS),
    ] = "",
    material: Annotated[
        dict, Param("Principled BSDF inputs to put on the subject")
    ] = None,
    measures: Annotated[
        list, Param("which measurements to take of the render, in the same call")
    ] = (),
    region: Annotated[
        str, Param("where to measure: frame, subject, a rectangle, or a mask file")
    ] = "",
    inline: Annotated[
        bool, Param("carry the picture back with the numbers, base64 encoded")
    ] = True,
    cached: Annotated[
        bool,
        Param("return an identical render already paid for rather than repeat it"),
    ] = True,
    azimuth: Annotated[
        float,
        Param("where the camera sits around the subject", lo=-360, hi=360, unit="deg"),
    ] = 35.0,
    elevation: Annotated[
        float, Param("how far above the subject", lo=-89, hi=89, unit="deg")
    ] = 20.0,
    margin: Annotated[
        float, Param("how much room around the subject", lo=1.0, hi=4.0)
    ] = 1.15,
    focal_mm: Annotated[
        float, Param("camera focal length", lo=8.0, hi=400.0, unit="mm")
    ] = 50.0,
    key: Annotated[
        float, Param("key light power", lo=0.0, hi=10000.0, unit="W")
    ] = 400.0,
    fill: Annotated[
        float, Param("fill light power", lo=0.0, hi=10000.0, unit="W")
    ] = 120.0,
    rim: Annotated[
        float, Param("rim light power", lo=0.0, hi=10000.0, unit="W")
    ] = 200.0,
    light_distance: Annotated[
        float, Param("how far the lights sit, in subject radii", lo=1.0, hi=20.0)
    ] = 3.0,
    ambient: Annotated[float, Param("world lighting", lo=0.0, hi=10.0)] = 0.25,
    exposure: Annotated[
        float, Param("film exposure", lo=-10.0, hi=10.0, unit="stops")
    ] = 0.0,
    transparent: Annotated[bool, Param("leave the background empty")] = True,
    root: Annotated[str, Param("the project to resolve settings against")] = ".",
) -> dict:
    """Render one subject at the cheapest rung that can answer the question.

    The rig is the same at every rung; only what stands in front of it changes.
    """
    from . import blender

    started = time.monotonic()
    chosen = plan(rung or None, list(asking) or None, floor=floor or None, root=root)
    config = load(root)
    where = Path(root).resolve()
    out_path = where / out if not Path(out).is_absolute() else Path(out)

    rig = Rig().with_(
        azimuth=azimuth,
        elevation=elevation,
        margin=margin,
        focal_mm=focal_mm,
        key=key,
        fill=fill,
        rim=rim,
        light_distance=light_distance,
        ambient=ambient,
        exposure=exposure,
        transparent=transparent,
    )
    params = {**as_params(rig), **({"material": material} if material else {})}
    if model:
        mesh = Path(model) if Path(model).is_absolute() else where / model
        if not mesh.is_file():
            raise PolyweaveError(
                "render.no-mesh",
                f"there is no mesh at {mesh}",
                "check the path, or build the mesh before rendering it",
            )
        sources = [provenance.source("mesh", mesh, root=where)]
    else:
        sources = []

    report.stage("building", note=f"{chosen['rung']}: {chosen['carries']}")
    # The engine and the colour pipeline are fixed before anything is built, because the
    # key depends on both and on nothing the scene holds — so a hit costs a reset rather
    # than an import, a decimation and a path trace.
    scene = blender.prepare(blender.reset())
    signature = provenance.cache_key(
        provenance.planned(
            "render",
            engine=blender.engine_record(scene),
            inputs=sources,
            params=params,
            rung=chosen["rung"],
            seed=chosen["seed"],
            samples=chosen["samples"],
        )
    )
    work = config.path("paths.work")
    if cached:
        hit = store.look(signature, work=work)
        if hit is not None:
            report.stage("rendering", progress=1.0, note="cached")
            return _from_cache(hit, out_path, where, chosen, started, inline)

    if chosen["subject"] == "primitive":
        subject = blender.primitive("sphere")
    else:
        if not model:
            raise PolyweaveError(
                "render.no-mesh",
                f"the {chosen['rung']} rung renders the real mesh and none was named",
                "pass `model`, or ask a question the sphere rung can carry",
            )
        subject = blender.load_mesh(
            where / model if not Path(model).is_absolute() else model
        )
        subject = blender.decimate(subject, chosen["decimate"])
    blender.apply_material(subject, material)
    blender.place(scene, rig, subject)

    report.stage(
        "rendering",
        note=f"{chosen['size']}px at {chosen['samples']} samples",
    )
    blender.render_to(
        scene,
        out_path,
        size=chosen["size"],
        samples=chosen["samples"],
        seed=chosen["seed"],
    )

    floor_alpha = float(config.get("tolerance.alpha_floor"))
    asserted = post.check(
        "render",
        out_path,
        size=(chosen["size"], chosen["size"]),
        alpha_floor=floor_alpha,
    )
    # The verdict and the picture are one answer to one question, so the measuring
    # happens here rather than in a call the caller has to make next.
    report.stage("rendering", progress=1.0, note="measuring")
    taken = measure.measure(
        out_path,
        list(measures) or measure.DEFAULT,
        region=region or None,
        alpha_floor=floor_alpha,
        rung=chosen["rung"],
    )

    elapsed = round(time.monotonic() - started, 3)
    record = provenance.build(
        "render",
        out_path,
        engine=blender.engine_record(scene),
        inputs=sources,
        params=params,
        measurements={**asserted, **measure.summarise(taken)},
        rung=chosen["rung"],
        seed=chosen["seed"],
        samples=chosen["samples"],
        elapsed_s=elapsed,
        root=where,
    )
    provenance.write(record, root=where)
    if cached:
        store.put(signature, out_path, record, work=work)
        store.evict(work=work, max_bytes=int(config.get("cache.max_bytes")))

    answer = {
        "artefact": record["artefact"]["path"],
        "rung": chosen["rung"],
        "why": chosen["why"],
        "size": chosen["size"],
        "samples": chosen["samples"],
        "elapsed_s": elapsed,
        "cached": False,
        "asserted": asserted,
        "measurements": taken,
        "cache_key": signature,
    }
    if inline:
        answer["image"] = measure.inline_image(out_path)
    return answer
