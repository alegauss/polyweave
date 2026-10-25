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

from polyweave.kernel import cache as store
from polyweave.kernel import post, provenance
from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.doors import Blank, door
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.geometry import units
from polyweave.loop import measure
from polyweave.loop.ladder import (
    CARRIES,
    RUNGS,
    check_rung,
    enabled,
    lowest_enabled,
    lowest_rung,
    rung_for,
)

from .rig import WATTS, Rig, as_params

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


@operation("render.plan")
def plan(
    rung: Annotated[str, Param("the rung to render at, if the caller names it")] = None,
    asking: Annotated[
        list, Param("the measures the answer has to carry, if no rung is named")
    ] = None,
    *,
    floor: Annotated[
        str, Param("the lowest rung a verdict on this asset may be taken at")
    ] = None,
    root: Annotated[str, Param("the project to resolve settings against")] = ".",
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
        needed = lowest_rung(asking, floor)
        chosen = lowest_enabled(needed, offered) or needed
        why = f"the lowest rung that carries {', '.join(sorted(set(asking)))}"
        if chosen != needed:
            why += f", {needed} being one this project does not enable"
    elif floor:
        chosen = lowest_enabled(floor, offered) or check_rung(floor)
        why = "the asset's own floor"
    else:
        chosen, why = offered[0], "the cheapest rung enabled"

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
    hit, out_path, where, chosen, started, inline: bool, tolerances=None, frame=None
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
        "size": list(frame or (chosen["size"], chosen["size"])),
        "rung_size": chosen["size"],
        "samples": chosen["samples"],
        "elapsed_s": round(time.monotonic() - started, 3),
        "cached": True,
        "asserted": {},
        "measurements": [],
        "cache_key": hit["key"],
        "recorded": record.get("measurements", {}),
        "stale": provenance.remeasure(record, tolerances) if tolerances else [],
        # The digest the render was recorded with, where it was (§PW141): a hit is the
        # same picture, so it is the same two answers.
        **record.get("digest", {}),
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
    spec: Annotated[str, Param("a spec whose subject's build is the mesh")] = "",
    rung: Annotated[str, Param("which rung to render at", choices=RUNGS)] = "",
    asking: Annotated[
        list, Param("the measures the answer has to carry, if no rung is named")
    ] = (),
    floor: Annotated[
        str,
        Param("the lowest rung a verdict may be taken at", choices=RUNGS),
    ] = "",
    material: Annotated[
        dict, Param("Principled BSDF inputs; with over = true, set on the mesh's own")
    ] = None,
    measures: Annotated[
        list, Param("which measurements to take of the render, in the same call")
    ] = (),
    region: Annotated[
        str, Param("where to measure: frame, subject, a rectangle, or a mask file")
    ] = "",
    inline: Annotated[
        bool, Param("carry the picture back too, base64 encoded")
    ] = True,
    cached: Annotated[
        bool,
        Param("serve an identical render already paid for"),
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
        float, Param("key light power", lo=0.0, hi=10000.0, unit=WATTS)
    ] = 400.0,
    fill: Annotated[
        float, Param("fill light power", lo=0.0, hi=10000.0, unit=WATTS)
    ] = 120.0,
    rim: Annotated[
        float, Param("rim light power", lo=0.0, hi=10000.0, unit=WATTS)
    ] = 200.0,
    light_distance: Annotated[
        float, Param("how far the lights sit, in subject radii", lo=1.0, hi=20.0)
    ] = 3.0,
    ambient: Annotated[float, Param("world lighting", lo=0.0, hi=10.0)] = 0.25,
    ambient_colour: Annotated[
        str, Param("the world light's colour, #RRGGBB; Blender's own if unset")
    ] = "",
    exposure: Annotated[
        float, Param("film exposure", lo=-10.0, hi=10.0, unit="stops")
    ] = 0.0,
    transparent: Annotated[bool, Param("leave the background empty")] = True,
    allow_uniform: Annotated[
        bool, Param("one flat colour is what was wanted, not a failure")
    ] = False,
    scrub: Annotated[
        bool,
        Param("undo shading a service painted into the mesh's texture"),
    ] = False,
    prepare: Annotated[
        list,
        Param("steps on the mesh: dedust, settle or custom"),
    ] = (),
    after: Annotated[
        list,
        Param("project passes over the picture: file.py:fn or {pass, args}"),
    ] = (),
    covers: Annotated[
        list,
        Param(
            "the world rectangle it stands for: [width, height] centred, or "
            "[x0, y0, x1, y1] seen from the front"
        ),
    ] = (),
    pixels_per_unit: Annotated[
        float,
        Param("the scale it is baked at; the project's if unset"),
    ] = 0.0,
    on_grid: Annotated[
        bool,
        Param("false for a logo or HUD piece, at its own pixels_per_unit"),
    ] = True,
    seed: Annotated[
        int, Param("the path tracer's seed; the project's if negative")
    ] = -1,
    samples: Annotated[
        int, Param("samples per pixel; the rung's if zero", lo=0)
    ] = 0,
    size: Annotated[
        int,
        Param("the square's side; the rung's if zero", lo=0, unit="px"),
    ] = 0,
    masks: Annotated[
        list, Param("materials masked, as <out>.<name>.mask.png")
    ] = (),
    root: Annotated[str, Param("the project to resolve settings against")] = ".",
) -> dict:
    """Render one subject at the cheapest rung that can answer the question.

    The rig is the same at every rung; only what stands in front of it changes.

    `seed`, `samples` and `size` are the changes that should not change the look, which
    is what calibrating a bound re-renders under (§PW107). They default to the
    project's, and a search is refused them as axes: one that picks a lucky seed has
    fitted the noise, not the asset.

    `spec` renders the build its `subject` names, at its rung (§PW298).

    `prepare` runs steps on the loaded mesh, each in the key and the record (§PW582).

    `masks` names materials whose pixels are written beside the picture, white where
    each shows, so a pocket carved in its own material is cut out by its own coverage
    and not by an outline recomputed by hand (§PW630). A bake asking for them is never
    served from the cache, which keeps the picture alone.
    """
    # What a project did to a mesh in its own Blender code before handing it over: a
    # custom step is recorded with its source's digest, and what each step did comes
    # back as `prepared`. The mesh is one object by then, joined as it loads.
    from . import blender

    if spec:
        from polyweave.loop import accept

        held = accept.read(spec, root)
        model = model or accept._subject_model(held, root)
        floor = floor or held.needs_rung()
    started = time.monotonic()
    chosen = plan(rung or None, list(asking) or None, floor=floor or None, root=root)
    if seed >= 0:
        chosen["seed"] = int(seed)
    if samples:
        chosen["samples"] = int(samples)
    if size and len(covers):
        raise PolyweaveError(
            "render.size-with-covers",
            f"a size of {size} px was asked for and a world rectangle decides the size",
            "leave size out, or change pixels_per_unit, which is what a rectangle's "
            "size follows from",
        )
    if size:
        chosen["size"] = int(size)
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
        ambient_colour=ambient_colour,
        exposure=exposure,
        transparent=transparent,
    )
    params = {**as_params(rig), **({"material": material} if material else {})}
    # In the key, and before it is computed: a scrubbed render and an unscrubbed one are
    # different pictures, and the key is what stops one being served for the other
    # (§PW49). What the scrub then measured goes in the answer, not here — those are its
    # outputs and the request is what a key is over.
    if scrub:
        # The scrub's own source too: the rule changed under an unchanged `scrub: true`
        # and the cache served the wand star's dashes back after they were gone (§PW80).
        import hashlib

        from polyweave.layers.geometry import texture

        params["scrub"] = {
            "sha256": hashlib.sha256(
                Path(texture.__file__).read_bytes()
            ).hexdigest()[:16]
        }
    if size:
        # A size asked for is a different picture from the rung's, so it is in the key.
        params["size"] = int(size)
    # A project's own passes are part of the picture (§PW439): each one's source digest
    # and arguments are in the key and the record, so a changed pass renders again and
    # reads outdated.
    passes = _passes(after, where=Path(root).resolve())
    if passes:
        params["after"] = [one["said"] for one in passes]
    # The same for a mesh's preparation: a different crumb floor is a different subject.
    steps = _steps(prepare, where=Path(root).resolve())
    if steps:
        params["prepare"] = [one["said"] for one in steps]
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
        if on_grid:
            scale = units.require(declared, root=root)
        else:
            # A mark drawn on the screen at its own size is on no grid (§PW79): the
            # engine's scale says nothing about it, so its own is required instead of
            # compared, and a rectangle between two pixels is still refused.
            if not pixels_per_unit:
                raise PolyweaveError(
                    "render.no-scale",
                    "a picture off the game's grid has no engine scale to fall back on",
                    "pass pixels_per_unit, the pixels one unit of the model spans in "
                    "the picture",
                )
            scale = {
                "covers": [float(v) for v in covers],
                "pixels_per_unit": float(pixels_per_unit),
                "size": list(units.for_size(list(covers), float(pixels_per_unit))),
            }
            params["on_grid"] = False
        if units.placed(covers) is not None and (azimuth or elevation):
            # A rectangle with a place is a place in the picture plane, which is only
            # the world's X and Y looking straight on (§PW78). Turned, its corners
            # would land wherever the turn put them, which is the drift it exists to
            # stop, so it is refused before anything is built.
            raise PolyweaveError(
                "render.placed-off-front",
                f"a rectangle placed at {[float(v) for v in covers]} is a place seen "
                f"from the front, and the camera is at azimuth {azimuth:g}, elevation "
                f"{elevation:g}",
                "pass azimuth=0 and elevation=0, or give covers as [width, height] "
                "to centre it on the subject from wherever the camera stands",
            )
        frame = (int(scale["size"][0]), int(scale["size"][1]))
        params["covers"] = [float(v) for v in covers]
        params["pixels_per_unit"] = scale["pixels_per_unit"]
    # The frame actually drawn is in the key for every bake (§PW145). A rung's size is
    # read from the project file, so changing `preview_size` changed the picture and not
    # the key, and the old size was served as a hit.
    params["frame"] = [int(frame[0]), int(frame[1])]
    if chosen["decimate"] < 1.0:
        # How a preview reduces the mesh is in its key (§PW420): one cached under the
        # collapse that shattered voxel builds is never served for the planar-first one.
        params["decimate"] = {
            "ratio": chosen["decimate"],
            "floor": blender.DECIMATE_FLOOR,
            "planar": True,
        }
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
    if cached and not masks:
        hit = store.look(signature, work=work)
        if hit is not None:
            report.stage("rendering", progress=1.0, note="cached")
            served = _from_cache(
                hit, out_path, where, chosen, started, inline, tolerances, frame
            )
            _counted(served)
            return served

    scrubbed: dict = {}
    prepared: list[dict] = []
    if chosen["subject"] == "primitive":
        subject = blender.primitive("sphere")
    else:
        if not model:
            raise PolyweaveError(
                "render.no-mesh",
                f"the {chosen['rung']} rung renders the real mesh and none was named",
                "pass `model`, or ask a question the sphere rung can carry",
                call=door(
                    "render.bake",
                    out=str(out),
                    model=Blank("the mesh"),
                    rung=chosen["rung"],
                ),
            )
        subject = blender.load_mesh(
            where / model if not Path(model).is_absolute() else model
        )
        # Before the decimation, which would count a crumb's faces as the body's.
        for one in steps:
            subject, did = _prepared(one, subject)
            prepared.append({"step": one["said"]["step"], **did})
        subject = blender.decimate(subject, chosen["decimate"])
        if scrub:
            # Opt-in, and Cottony's own pass was per model for the same reason: a dark
            # line a person drew deliberately and a shadow the service painted look
            # identical to anything measuring darkness, and removing the first is a
            # judgement about what somebody wanted (§PW49).
            scrubbed = blender.scrub_textures(subject)
    # In the declaration's words as well as the shader's, so `colour = "#FFC43F"` means
    # here what it means in a geometry file (§PW83). The key above is over the request.
    # `over = true` lays the inputs on the mesh's own materials, keeping its textures
    # (§PW440); the sphere has none of its own, so there it is the plain form.
    laid = bool(material and material.get("over"))
    inputs = {k: v for k, v in (material or {}).items() if k != "over"}
    if laid and chosen["subject"] != "primitive":
        blender.lay_over(subject, blender.as_inputs(inputs))
    else:
        blender.apply_material(subject, blender.as_inputs(inputs) if inputs else None)
    if masks:
        # Refused before the path trace is paid for, with the materials it does wear.
        worn = [s.material.name for s in subject.material_slots if s.material]
        unknown = [str(one) for one in masks if str(one) not in worn]
        if unknown:
            raise PolyweaveError(
                "render.unknown-mask",
                f"{', '.join(unknown)} is no material the subject wears",
                "name materials from the mesh's own: " + (", ".join(worn) or "none"),
                given=unknown[0], allowed=worn,
            )
        if len(worn) > len(blender.SLOT_COLOURS):
            raise PolyweaveError(
                "render.unknown-mask",
                f"the subject wears {len(worn)} materials, more than the flat pass "
                f"tells apart ({len(blender.SLOT_COLOURS)})",
                "bake a mesh in fewer materials to mask one of them",
                given=str(masks[0]), allowed=worn,
            )
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
    for one in passes:
        _painted(one, out_path)

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

    # Two short answers a later session compares without the pictures: did the outline
    # move, and did the look (§PW141). Quantised at this rung's noise floor.
    # A palette per material slot, off one flat pass at the same rig (§PW161): the
    # blended picture alone cannot say which pixels wear which slot.
    slotted = blender.slot_masks(
        scene, subject, work / "slots" / f"{signature}.png", size=frame
    )
    digested = measure.digests(
        measure.load(out_path),
        alpha_floor=floor_alpha,
        noise=tolerances.render_noise,
        triangles=blender.triangles(subject),
        slots=slotted,
    )
    digest = {k: digested[k] for k in ("shape_digest", "look_digest", "quantum")}
    # The palette the look digest is over, so a moved digest says which slot moved.
    digest["palette"] = digested["figures"]["look"]["palette"]
    written = (_masks_written([str(one) for one in masks], slotted, out_path,
                              floor_alpha, where) if masks else {})

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
        extra={"digest": digest},
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
        # What was drawn, as every other `size` here is (§PW85). The rung's square is a
        # different number wherever a declared rectangle decided the frame, and a 96 px
        # star used to be reported as 1024.
        "size": list(frame),
        "rung_size": chosen["size"],
        "samples": chosen["samples"],
        "elapsed_s": elapsed,
        "cached": False,
        "asserted": asserted,
        "measurements": taken,
        "cache_key": signature,
        **digest,
    }
    if scale is not None:
        answer["covers"] = scale["covers"]
        answer["pixels_per_unit"] = scale["pixels_per_unit"]
    if scrubbed:
        # What the threshold came out at and how much it caught, so a scrub that took
        # a tenth of the texture is visible as that rather than as a darker render.
        answer["scrubbed"] = scrubbed
    if prepared:
        answer["prepared"] = prepared
    if written:
        answer["masks"] = written
    if inline:
        answer["image"] = measure.inline_image(out_path)
    _counted(answer)
    return answer


def _masks_written(names: list[str], slotted: dict | None, out_path: Path,
                   floor: float, where: Path) -> dict[str, str]:
    """Each named material's pixels as a mask beside the picture, by name (§PW630).

    White where the material shows in the picture and black elsewhere, off the flat
    pass the look digest already reads; a subject in one material is its own coverage.
    """
    from PIL import Image as PILImage

    # Refused before the render where the pass could not tell them apart, so no slots
    # here means one material, whose coverage is the subject's own.
    covered = measure.load(out_path).subject(floor)
    out = {}
    for name in names:
        shown = covered & slotted[name] if slotted else covered
        target = out_path.with_name(f"{out_path.stem}.{name}.mask.png")
        PILImage.fromarray((shown * 255).astype("uint8"), "L").save(target)
        out[name] = provenance.relative(target, where)
    return out


def _passes(after, *, where: Path) -> list[dict]:
    """Each pass `after` names, resolved to its function, digest and arguments.

    A pass is the project's code, never the plugin's (its look is the project's own), so
    it is a file under the project and a function in it, called with the written
    picture's path and its arguments.
    """
    resolved = []
    for index, given in enumerate(after or ()):
        named = given if isinstance(given, str) else (given or {}).get("pass", "")
        arguments = {} if isinstance(given, str) else {
            k: v for k, v in given.items() if k != "pass"}
        fn, name, digest = _project_fn(
            named, where=where, at=f"after[{index}]", code="render.no-pass",
            failed=_pass_failed,
        )
        resolved.append({
            "fn": fn,
            "arguments": arguments,
            "said": {"pass": name, "sha256": digest, **arguments},
        })
    return resolved


def _project_fn(named, *, where: Path, at: str, code: str, failed) -> tuple:
    """A `path/to/file.py:function` under the project: the function, its name as the
    record spells it, and its source's digest, so a changed function renders again."""
    import hashlib
    import importlib.util

    file, _, function = str(named).rpartition(":")
    source = (where / file).resolve() if file else None
    if source is None or not source.is_relative_to(where) or not source.is_file():
        raise PolyweaveError(
            code,
            f"{at} names {named!r}, which is not a file under the project and a "
            "function in it",
            "name it as path/to/file.py:function, under the project",
            given=str(named),
        )
    loaded = importlib.util.spec_from_file_location(
        f"polyweave_pass_{hashlib.sha256(str(source).encode()).hexdigest()[:12]}",
        source,
    )
    module = importlib.util.module_from_spec(loaded)
    try:
        loaded.loader.exec_module(module)
    except Exception as broken:  # noqa: BLE001 - the project's code, said as its own
        raise failed(named, broken) from broken
    fn = getattr(module, function, None)
    if not callable(fn):
        raise PolyweaveError(
            code,
            f"{at}: {file} has no function {function!r}",
            "name a function the file defines, as path/to/file.py:function",
            given=str(named),
        )
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    return fn, f"{source.relative_to(where).as_posix()}:{function}", digest


#: The preparation steps `render.bake` knows, each with the arguments it takes.
STEPS = {"dedust": ("below",), "settle": ("squash",), "custom": None}


def _steps(prepare, *, where: Path) -> list[dict]:
    """Each step `prepare` names, checked before anything is built (§PW582)."""
    resolved = []
    for index, given in enumerate(prepare or ()):
        step = (given or {}).get("step") if isinstance(given, dict) else None
        if step not in STEPS:
            raise PolyweaveError(
                "render.bad-prepare",
                f"prepare[{index}] is {given!r}, and a step is one of "
                f"{', '.join(STEPS)}",
                "give each step as {step = dedust, below = 0.01}, {step = settle, "
                "squash = 0.93} or {step = custom, fn = \"file.py:fn\"}",
                given=str(given),
            )
        arguments = {k: v for k, v in given.items() if k not in ("step", "fn")}
        if step == "custom":
            fn, name, digest = _project_fn(
                given.get("fn", ""), where=where, at=f"prepare[{index}]",
                code="render.bad-prepare", failed=_step_failed,
            )
            resolved.append({"fn": fn, "arguments": arguments, "said": {
                "step": step, "fn": name, "sha256": digest, **arguments}})
            continue
        wanted = STEPS[step]
        if sorted(arguments) != sorted(wanted):
            raise PolyweaveError(
                "render.bad-prepare",
                f"prepare[{index}], {step}, takes {', '.join(wanted)} and was given "
                f"{', '.join(sorted(arguments)) or 'nothing'}",
                f"give {step} exactly {', '.join(wanted)}",
                given=str(given),
            )
        resolved.append({"fn": None, "arguments": arguments,
                         "said": {"step": step, **arguments}})
    return resolved


def _prepared(one: dict, subject):
    """Run one step on the loaded mesh; the subject after it, and what it did."""
    from . import blender

    step = one["said"]["step"]
    if step == "dedust":
        return subject, blender.dedust(subject, float(one["arguments"]["below"]))
    if step == "settle":
        return subject, blender.settle(subject, float(one["arguments"]["squash"]))
    try:
        given = one["fn"](subject, **one["arguments"])
    except Exception as broken:  # noqa: BLE001 - the project's code, said as its own
        raise _step_failed(one["said"]["fn"], broken) from broken
    # A custom step may hand back a new object, or change the one it was given.
    return (subject if given is None else given), {"fn": one["said"]["fn"]}


def _step_failed(named, broken: BaseException) -> PolyweaveError:
    import traceback

    where = traceback.extract_tb(broken.__traceback__)[-1]
    return PolyweaveError(
        "render.prepare-failed",
        f"the step {named} raised {type(broken).__name__}: {broken}",
        "fix the step, or drop it from prepare to see the render without it",
        detail=f"{Path(where.filename).name}:{where.lineno} in {where.name}",
    )


def _painted(one: dict, out_path: Path) -> None:
    """Run one pass over the written picture, its failure said as the project's."""
    try:
        one["fn"](out_path, **one["arguments"])
    except Exception as broken:  # noqa: BLE001 - the project's code, said as its own
        raise _pass_failed(one["said"]["pass"], broken) from broken


def _pass_failed(named, broken: BaseException) -> PolyweaveError:
    import traceback

    where = traceback.extract_tb(broken.__traceback__)[-1]
    return PolyweaveError(
        "render.pass-failed",
        f"the pass {named} raised {type(broken).__name__}: {broken}",
        "fix the pass, or drop it from after to see the render without it",
        detail=f"{Path(where.filename).name}:{where.lineno} in {where.name}",
    )


def _counted(answer: dict) -> None:
    """Tell an open loop run what this bake was: a render, or a hit (§PW115)."""
    from polyweave.loop import loop

    loop.bake_seen(answer)
