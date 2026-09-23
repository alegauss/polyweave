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
from .. import measure, post, provenance, units
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


def _from_cache(
    hit, out_path, where, chosen, started, inline: bool, tolerances=None
) -> dict:
    """A hit, **reported as a hit**, and told which of its bars have since moved.

    A caller timing a sweep needs to know what it actually measured; a cache that
    silently answers in four milliseconds makes a benchmark meaningless.

    The picture is still the picture: a tolerance is read after the pixels exist, so it
    cannot have changed them, and the hit is returned (§PW51). What can be stale is the
    **verdict** beside it, so `stale` names every bar the recorded measurements were
    taken against and that the project has since changed. It is named rather than
    re-taken here, because re-taking the measures without re-taking the assertions would
    write a record whose tolerances contradict half its own numbers, and an assertion
    that refuses on a cache read is a behaviour a caller has to be able to see coming.
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
        "stale": provenance.remeasure(record, tolerances) if tolerances else [],
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
    allow_uniform: Annotated[
        bool, Param("a render of one flat colour is what was wanted, not a failure")
    ] = False,
    scrub: Annotated[
        bool,
        Param("take the shading a service painted into the mesh's texture back out"),
    ] = False,
    covers: Annotated[
        list,
        Param("the world rectangle this picture stands for, as [width, height]"),
    ] = (),
    pixels_per_unit: Annotated[
        float,
        Param("the scale it is baked at; the project's own where this is left out"),
    ] = 0.0,
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
    # In the key, and before it is computed: a scrubbed render and an unscrubbed one are
    # different pictures, and the key is what stops one being served for the other
    # (§PW49). What the scrub then measured goes in the answer, not here — those are its
    # outputs and the request is what a key is over.
    if scrub:
        params["scrub"] = True
    scale = None
    # The size the picture comes out at: the rung's square, unless a world rectangle was
    # declared, in which case the declaration decides both axes (§PW47). Before this, a
    # 4x2 rectangle at 64 px/unit could only ever be refused, because the renderer made
    # squares at whichever size the rung named and the contract asked for 256x128.
    frame: tuple[int, int] = (chosen["size"], chosen["size"])
    if len(covers):
        # The scale is resolved the one way §PW24 resolves it — the asset's own where it
        # states one, and the engine's where it does not — and the size follows from it
        # rather than from the rung. No `size=` here: there is no rendered picture to
        # check yet, and this is what decides the size the picture will be.
        declared = {"covers": list(covers)}
        if pixels_per_unit:
            declared["pixels_per_unit"] = float(pixels_per_unit)
        scale = units.require(declared, root=root)
        frame = (int(scale["size"][0]), int(scale["size"][1]))
        params["covers"] = [float(v) for v in covers]
        params["pixels_per_unit"] = scale["pixels_per_unit"]
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
    # Resolved once, at the operation, and passed down: the checks and the measures
    # below take the numbers and default none of them (§PW40). It is read here rather
    # than after the render because a hit has to be able to say which of these bars the
    # verdict it carries predates (§PW51).
    #
    # **With the rung**, which is the half that was missing (§PW62). `render_noise` is
    # keyed by rung because the floor at four samples is not the floor at five hundred,
    # and naming none took the strictest of the table — so every render was checked
    # against final's 0.013, the sphere rung at four samples included. For this bar the
    # strictest is the wrong direction: a lower floor refuses less, so the noisiest rung
    # got the bar that lets a flat render through.
    tolerances = config.tolerances(chosen["rung"])
    if cached:
        hit = store.look(signature, work=work)
        if hit is not None:
            report.stage("rendering", progress=1.0, note="cached")
            return _from_cache(
                hit, out_path, where, chosen, started, inline, tolerances
            )

    scrubbed: dict = {}
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
        if scrub:
            # Opt-in, and Cottony's own pass was per model for the same reason: a dark
            # line a person drew deliberately and a shadow the service painted look
            # identical to anything measuring darkness, and removing the first is a
            # judgement about what somebody wanted (§PW49).
            scrubbed = blender.scrub_textures(subject)
    blender.apply_material(subject, material)
    blender.place(scene, rig, subject, covers=list(covers) or None)

    report.stage(
        "rendering",
        note=f"{frame[0]}x{frame[1]}px at {chosen['samples']} samples",
    )
    blender.render_to(
        scene,
        out_path,
        size=frame,
        samples=chosen["samples"],
        seed=chosen["seed"],
    )

    floor_alpha = tolerances.alpha_floor
    asserted = post.check(
        "render",
        out_path,
        size=frame,
        alpha_floor=floor_alpha,
        render_noise=tolerances.render_noise,
        subject_extent=tolerances.subject_extent,
        allow_uniform=allow_uniform,
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
        tolerances=tolerances.as_dict(),
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
    if scale is not None:
        answer["covers"] = scale["covers"]
        answer["pixels_per_unit"] = scale["pixels_per_unit"]
    if scrubbed:
        # What the threshold came out at and how much it caught, so a scrub that took
        # a tenth of the texture is visible as that rather than as a darker render.
        answer["scrubbed"] = scrubbed
    if inline:
        answer["image"] = measure.inline_image(out_path)
    return answer
