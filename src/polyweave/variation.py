"""A variation of an approved picture, measured against the one it came from (§PW170).

Refinement is where consistency is lost: a character is approved, asked for holding a
lantern, and comes back with longer legs and a warmer coat. Nothing compared the new
picture to the one it came from, because nothing recorded that it came from one.

- **A variation has a parent.** `picture.vary` sends an approved picture to the
  service's remix or edit (inpaint) call, and the record carries the parent's path and
  digest, the operation, its strength and the mask, with the parent as an input, so
  `provenance.dependents` of a replaced parent names every variation made from it.
- **The mask comes from the request, not from a person drawing one.** An edit named by
  region takes it from the parent's described element boxes (`picture.describe`), so an
  edit an agent asks for is bounded where the approved picture said that element was.
- **Outside the mask, nothing should have changed.** `picture.against_parent` measures
  what was to be kept as a person means kept, because the services redraw the whole
  picture (§PW209): the outline framed alike and the look's drift measures, against the
  spread of variations a person accepted. Pixel for pixel, against `[tolerance]
  delta_e`, only for a service that says it `preserves` them. It also measures the
  variation against its family's canon where a style is declared.

What a variation should look like stays the person's verdict; what it must not have
changed is a number.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Annotated

import numpy as np

from . import picture, provenance, purchase, style
from .config import load
from .describe import Param, operation
from .errors import PolyweaveError

#: What a variation can be, and the service call each is.
OPERATIONS = {
    "remix": "ideogram-v3/remix",
    "edit": "ideogram-v3/inpaint",
    # The same picture in another frame, the new area drawn in (§PW181). It takes no
    # prompt: what may change is only the border the new shape adds.
    "reframe": "ideogram-v3/reframe",
}


@operation("picture.vary")
def vary(
    parent: Annotated[str, Param("the approved picture, under the project")],
    out: Annotated[str, Param("where the variation is written, under the project")],
    prompt: Annotated[
        str, Param("what the variation should show; a reframe takes none")
    ] = None,
    *,
    change: Annotated[
        str,
        Param("remix the whole, edit in a mask, or reframe", choices=tuple(OPERATIONS)),
    ] = "edit",
    resolution: Annotated[
        str, Param("for a reframe: the new frame, as WIDTHxHEIGHT the service offers")
    ] = None,
    region: Annotated[
        str, Param("for an edit: the described element to change, by its words")
    ] = None,
    mask: Annotated[
        str, Param("for an edit: a mask file, black where it may change")
    ] = (None),
    strength: Annotated[
        int, Param("for a remix: how much of the parent is kept")
    ] = None,
    rendering_speed: Annotated[str, Param("as the service spells it")] = None,
    service: Annotated[str, purchase.SERVICE] = None,
    root: Annotated[str, Param("the project whose ledger this is")] = ".",
) -> dict:
    """Buy a variation of an approved picture, with its parent on the record.

    An edit changes only what its mask allows, and the mask is `mask`, or the box of the
    parent's described element whose words contain `region`. A remix redraws the whole
    at `strength` (the service's `image_weight`). A reframe puts the whole parent in a
    new `resolution` and draws only the border it adds. Each is priced by its row of
    `prices`. The endpoints take a text prompt at most, so a family's style is not
    carried into the request; `picture.against_parent` measures it afterwards.
    """
    if change not in OPERATIONS:
        raise PolyweaveError(
            "fetch.bad-choice",
            f"there is no variation {change!r}",
            f"pass one of {', '.join(OPERATIONS)}",
            given=change,
            allowed=OPERATIONS,
        )
    config = load(root)
    here = config.root
    source = here / parent
    if not source.is_file():
        raise PolyweaveError(
            "fetch.no-reference",
            f"there is no picture at {source} to vary",
            "name the approved picture, as a path under the project",
        )
    if change == "reframe" and not resolution:
        raise PolyweaveError(
            "fetch.missing-field",
            "a reframe needs the frame it puts the picture in",
            "pass resolution, as WIDTHxHEIGHT from the sizes the service offers",
        )
    if change != "reframe" and not prompt:
        raise PolyweaveError(
            "fetch.missing-field",
            f"a{'n' if change == 'edit' else ''} {change} needs a prompt saying what "
            f"the variation should show",
            "pass prompt",
        )
    name = config.service(service)
    about = config.services()[name]
    base, key = picture._reached(name, about)
    price = picture._price(name, about.get("prices") or {}, change, rendering_speed)

    files = {"image": (source.name, picture.sent_bytes(source), picture._mime(source))}
    payload: dict = (
        {"resolution": resolution} if change == "reframe" else {"prompt": prompt}
    )
    mask_path = mask_from = None
    if change == "edit":
        mask_path, mask_from = _mask_for(source, region, mask, here, out)
        files["mask"] = ("mask.png", mask_path.read_bytes(), "image/png")
    elif strength is not None:
        payload["image_weight"] = int(strength)
    if rendering_speed is not None:
        payload["rendering_speed"] = rendering_speed

    purchase.allow(price, root=here, service=name)
    answer = picture._answered(
        f"{base.rstrip('/')}/v1/{OPERATIONS[change]}", key, payload, files=files
    )
    drawn = (answer.get("data") or [{}])[0]
    if not drawn.get("url"):
        raise PolyweaveError(
            "fetch.prompt-refused"
            if drawn.get("is_image_safe") is False
            else "fetch.nothing-arrived",
            "the service answered with no variation to take delivery of",
            "reword the prompt; nothing was ledgered",
            detail=json.dumps(answer)[:400],
        )
    body = picture._download(drawn["url"])
    returned = max(1, len(answer.get("data") or ()))
    return purchase.capture(
        body,
        out=out,
        task_id=f"{name}:{change}:{answer.get('created')}:{drawn.get('seed')}",
        credits=round(price * returned, 4),
        outputs=returned,
        prompt=prompt,
        reference=parent,
        bought="image",
        engine={"name": name, "model": "3.0"},
        service=name,
        details={
            "parent": {
                "path": parent,
                "sha256": provenance.sha256_of(source)[0],
            },
            "change": change,
            "frame": resolution,
            "region": region,
            "strength": strength,
            "mask": provenance.relative(mask_path, here) if mask_path else None,
            # Whose the region was: a person's mark outranks the described boxes.
            "mask_from": mask_from,
            "resolution": drawn.get("resolution"),
            "seed": drawn.get("seed"),
            "returned_prompt": drawn.get("prompt"),
        },
        root=here,
    )


def _mask_for(source: Path, region, mask, here: Path, out: str) -> tuple[Path, str]:
    """The edit's mask: the file given, then the person's mark, then a described box.

    A person's mark outranks the agent's reading of the picture (§PW174): where they
    drew on this very picture on the review page, that is where the edit may change,
    whatever `region` says. The mark is matched by the picture's digest, so a mark
    drawn on another picture, or on an earlier version of this one, never applies.
    """
    if mask:
        given = here / mask
        if not given.is_file():
            raise PolyweaveError(
                "fetch.no-reference",
                f"there is no mask at {given}",
                "name a black-and-white picture the parent's size, black where it may "
                "change",
            )
        return given, "given"
    marked = person_marked(source, here)
    if marked is not None:
        return marked, "person"
    if not region:
        raise PolyweaveError(
            "fetch.missing-field",
            "an edit needs to know where it may change, and names neither region nor "
            "mask",
            "pass region, the words of a described element, or mask",
        )
    described = source.with_suffix(".prompt.json")
    if not described.is_file():
        raise PolyweaveError(
            "fetch.no-region",
            f"{source.name} has no described prompt, so {region!r} has no box",
            "describe it first with picture.describe, or pass mask",
        )
    elements = (
        json.loads(described.read_text(encoding="utf-8")).get(
            "compositional_deconstruction", {}
        )
    ).get("elements") or []
    wanted = str(region).casefold()
    boxed = [
        e
        for e in elements
        if e.get("bbox") and wanted in str(e.get("desc", "")).casefold()
    ]
    if len(boxed) != 1:
        raise PolyweaveError(
            "fetch.no-region",
            f"{len(boxed)} described elements of {source.name} match {region!r}, "
            f"and an edit is bounded by exactly one",
            "name one of the described elements by more of its words",
            given=region,
            allowed=[str(e.get("desc", "")) for e in elements if e.get("bbox")],
        )
    from PIL import Image

    with Image.open(source) as opened:
        width, height = opened.size
    top, left, bottom, right = (int(v) for v in boxed[0]["bbox"])
    drawn = Image.new("L", (width, height), 255)
    drawn.paste(
        0,
        (
            left * width // 1000,
            top * height // 1000,
            right * width // 1000,
            bottom * height // 1000,
        ),
    )
    target = (here / out).with_suffix(".mask.png")
    target.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    drawn.save(buffer, format="PNG")
    target.write_bytes(buffer.getvalue())
    return target, "described"


def person_marked(source: Path, here: Path) -> Path | None:
    """The newest mask a person drew on exactly this picture, or none."""
    from . import verdict

    digest = provenance.sha256_of(source)[0]
    marks = [
        mark
        for one in verdict.answers(root=str(here))["answers"]
        for mark in one.get("marks") or ()
        if mark.get("sha256") == digest and (here / mark["mask"]).is_file()
    ]
    return here / marks[-1]["mask"] if marks else None


@operation("picture.against_parent")
def against_parent(
    variation: Annotated[
        str, Param("a picture picture.vary bought, under the project")
    ],
    *,
    family: Annotated[str, Param("the asset family, needed only among several")] = None,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """What a variation changed that it was not asked to, against its parent.

    What it was asked to keep is outside an edit's mask, or the parent's placed frame
    in a reframe. A service that redraws the whole picture never keeps it pixel for
    pixel, so it is measured as a person means kept (§PW209): the silhouette framed
    alike, and the look's drift measures beside the parent's, each against the spread of
    variations a person accepted, and `judged` is false until two have been. Where
    `[service] preserves` says the service leaves those pixels alone, they are held to
    `[tolerance] delta_e` instead. `instrument` says which. A remix has no mask, so it
    is measured against the canon alone, where a style is declared.
    """
    config = load(root)
    tolerances = config.tolerances()
    cut = _kept_region(variation, config)
    record = cut["record"]
    found: dict = {"variation": variation, "parent": cut["parent_path"]}
    failed: list[str] = []
    preserves = bool(
        (config.services().get(record.get("service")) or {}).get("preserves")
    )
    if cut["change"] == "remix":
        found["instrument"] = "canon"
    elif preserves:
        found["instrument"] = "pixels"
        failed += _pixels(cut, found, tolerances)
    else:
        found["instrument"] = "kept"
        failed += _judged_kept(cut, found, config, family)
    if cut["change"] == "reframe":
        found["placed"] = cut["placed"]
    if style.in_force(config, family) is not None:
        drifted = style.drift(variation, family, root=config.root)
        found["canon"] = {"judged": drifted["judged"], "drifted": drifted["drifted"]}
        failed.extend(
            f"{key} drifted from the canon: "
            f"{drifted['measures'][key].get('which_way', 'off')}"
            for key in drifted["drifted"]
        )
    found.update(
        failed=failed,
        passed=not failed,
        not_checked=[
            "whether the drawn-in border belongs with the picture"
            if cut["change"] == "reframe"
            else "whether it shows what was asked for"
        ],
    )
    return found


def _kept_region(variation: str, config) -> dict:
    """The variation and its parent, each cut to what it was asked to keep."""
    from .image import load as load_image

    here = config.root
    record = provenance.read(variation, root=here)
    lineage = (record.get("details") or {}).get("parent")
    if not lineage:
        raise PolyweaveError(
            "fetch.no-parent",
            f"{variation} records no parent, so there is nothing to hold it against",
            "measure it against its canon with style.drift instead",
        )
    parent = load_image(here / lineage["path"])
    child = load_image(here / variation)
    details = record["details"]
    cut = {"record": record, "parent_path": lineage["path"]}
    if details.get("change") == "reframe":
        placed, held = _placed(variation, lineage["path"], parent, child)
        size = (placed["width"], placed["height"])
        box = (placed["x"], placed["y"], placed["x"] + size[0], placed["y"] + size[1])
        return {
            **cut,
            "change": "reframe",
            "placed": placed,
            "held_delta_e": held,
            "parent": _scaled(parent, size),
            "child": _cropped(child, box),
            "kept": None,
        }
    if child.size != parent.size:
        child = _resized(child, parent.size)
    if not details.get("mask"):
        return {**cut, "change": "remix", "parent": parent, "child": child}
    kept = load_image(here / details["mask"]).rgba[..., 0] > 127
    return {
        **cut,
        "change": "edit",
        "parent": _only(parent, kept),
        "child": _only(child, kept),
        "whole_parent": parent,
        "whole_child": child,
        "kept": kept,
    }


def _pixels(cut: dict, found: dict, tolerances) -> list[str]:
    """The kept region pixel for pixel, for a service stated to leave it alone."""
    from . import measure

    failed = []
    if cut["change"] == "reframe":
        worst = cut["held_delta_e"]
        found["held_delta_e"] = round(worst, 4)
        if worst > tolerances.delta_e:
            failed.append(
                f"where the parent sits in the reframe a patch moved by delta E "
                f"{worst:.1f}, over {tolerances.delta_e}: the reframe redrew what it "
                f"was asked to keep"
            )
        return failed
    kept, child, parent = cut["kept"], cut["whole_child"], cut["whole_parent"]
    field = measure._delta_field(child, parent)
    worst = float(measure.pooled(field, kept).max()) if kept.any() else 0.0
    found["unmasked_delta_e"] = round(worst, 4)
    if worst > tolerances.delta_e:
        failed.append(
            f"outside the mask a patch moved by delta E {worst:.1f}, over "
            f"{tolerances.delta_e}: the edit redrew what it was not asked to"
        )
    mine = child.subject(tolerances.alpha_floor) & kept
    theirs = parent.subject(tolerances.alpha_floor) & kept
    union = int((mine | theirs).sum())
    iou = round(float((mine & theirs).sum()) / union, 6) if union else 1.0
    found["unmasked_silhouette_iou"] = iou
    if iou < tolerances.silhouette_iou:
        failed.append(
            f"outside the mask the outline overlaps the parent's by {iou}, under "
            f"{tolerances.silhouette_iou}"
        )
    return failed


#: The drift measures a kept region is compared on: the look, not the pixels (§PW209).
LOOK = (
    "palette_delta_e_p95",
    "value_p5",
    "value_p95",
    "saturation_p5",
    "saturation_p95",
    "line_weight",
)


def _kept(cut: dict, config, family) -> dict:
    """What a person means by kept, in numbers: the outline, and the look's drift."""
    floor = config.tolerances().alpha_floor
    held = style.in_force(config, family)
    palette = list((held[1] if held else {}).get("palette") or [])
    mine = style.features(cut["child"], palette, floor)
    theirs = style.features(cut["parent"], palette, floor)
    return {
        "silhouette_iou": _framed_iou(
            cut["child"].subject(floor), cut["parent"].subject(floor)
        ),
        "look": {
            key: {
                "value": mine[key],
                "parent": theirs[key],
                "off": round(mine[key] - theirs[key], 4),
            }
            for key in LOOK
            if mine.get(key) is not None and theirs.get(key) is not None
        },
    }


def _judged_kept(cut: dict, found: dict, config, family) -> list[str]:
    """The kept measures against the spread of variations a person accepted."""
    mine = _kept(cut, config, family)
    variation = found["variation"]
    accepted = [
        _kept(_kept_region(path, config), config, family)
        for path in _accepted(config)
        if path != variation
    ]
    judged = len(accepted) >= 2
    failed = []
    outline_floor = min(a["silhouette_iou"] for a in accepted) if judged else None
    if judged and mine["silhouette_iou"] < outline_floor - 1e-6:
        failed.append(
            f"framed alike, the kept outline overlaps the parent's by "
            f"{mine['silhouette_iou']}, under the {outline_floor} of the least-kept "
            f"variation a person accepted"
        )
    for key, one in mine["look"].items():
        offs = [abs(a["look"][key]["off"]) for a in accepted if key in a["look"]]
        one["floor"] = round(max(offs), 4) if judged and len(offs) >= 2 else None
        one["drifted"] = one["floor"] is not None and abs(one["off"]) > one["floor"]
        if one["drifted"]:
            failed.append(
                f"{key} moved {one['off']:+g} from the parent's, past the "
                f"{one['floor']} the accepted variations moved"
            )
    plural = "" if len(accepted) == 1 else "s"
    found["kept"] = {
        **mine,
        "judged": judged,
        "accepted": len(accepted),
        "floor": f"the spread of {len(accepted)} variations a person accepted"
        if judged
        else f"none: {len(accepted)} accepted variation{plural} measured, and a "
        f"floor is the spread of at least two",
    }
    return failed


def _accepted(config) -> list[str]:
    """Every variation a person accepted on the review page, by path."""
    from . import review, verdict

    here = config.root
    offered = {one["manifest"]: one["families"] for one in review.sittings(here)}
    found: list[str] = []
    for answer in verdict.answers(root=str(here))["answers"]:
        members = (
            (offered.get(answer.get("sitting")) or {}).get(answer.get("family")) or {}
        ).get("members") or []
        named = {m.get("name"): m.get("new") for m in members}
        for said in answer.get("members") or ():
            path = named.get(said.get("name"))
            if not said.get("person_accepted") or not path or path in found:
                continue
            try:
                record = provenance.read(path, root=here)
            except PolyweaveError:
                continue
            details = record.get("details") or {}
            if details.get("parent") and (
                details.get("mask") or details.get("change") == "reframe"
            ):
                found.append(path)
    return found


#: The square both outlines are fitted into before they are compared.
FRAMED = 128


def _framed_iou(mine, theirs) -> float:
    """Two outlines trimmed to their own box and fitted alike, then overlapped.

    Where a service redrew the picture it may move or rescale the subject by a few
    pixels, and a raw overlap measures that placement rather than the shape (§PW194).
    """
    a, b = _fitted(mine), _fitted(theirs)
    union = int((a | b).sum())
    return round(float((a & b).sum()) / union, 6) if union else 1.0


def _fitted(mask):
    from PIL import Image as PILImage

    rows, columns = mask.nonzero()
    canvas = np.zeros((FRAMED, FRAMED), dtype=bool)
    if not len(rows):
        return canvas
    trimmed = mask[rows.min() : rows.max() + 1, columns.min() : columns.max() + 1]
    height, width = trimmed.shape
    scale = FRAMED / max(height, width)
    size = (max(1, round(width * scale)), max(1, round(height * scale)))
    drawn = PILImage.fromarray(trimmed.astype(np.uint8) * 255).resize(
        size, PILImage.Resampling.NEAREST
    )
    top, left = (FRAMED - size[1]) // 2, (FRAMED - size[0]) // 2
    canvas[top : top + size[1], left : left + size[0]] = np.asarray(drawn) > 127
    return canvas


def _only(image, kept):
    """The image with everything outside the kept region made transparent."""
    from .image import Image

    rgba = image.rgba.copy()
    rgba[..., 3] = np.where(kept, rgba[..., 3], 0)
    return Image(path=image.path, rgba=rgba, had_alpha=True)


def _cropped(image, box):
    from .image import Image

    left, top, right, bottom = box
    return Image(
        path=image.path,
        rgba=image.rgba[top:bottom, left:right].copy(),
        had_alpha=image.had_alpha,
    )


#: The side, in pixels, both pictures are brought down to before the placement search:
#: enough to see where the parent landed, and cheap enough to try every offset.
SEARCH_SIDE = 96


def _placed(variation: str, parent_path: str, parent, child) -> tuple[dict, float]:
    """Where the whole parent sits in the reframe, and how far that region moved.

    The service may place the parent at its own size or fit it to the new frame, so
    both scales are tried at every offset, on small copies, and the best placement is
    refined at full size (§PW181).
    """
    from . import measure

    before = measure._composited(parent)
    after = measure._composited(child)
    ph, pw = before.shape[:2]
    ch, cw = after.shape[:2]
    scales = sorted({1.0, round(min(cw / pw, ch / ph), 6)})
    best = None
    for scale in scales:
        sw, sh = max(1, round(pw * scale)), max(1, round(ph * scale))
        if sw > cw or sh > ch:
            continue
        placed = _scaled(parent, (sw, sh))
        field_of = measure._composited(placed)
        shrink = max(1, max(cw, ch) // SEARCH_SIDE)
        small_child = after[::shrink, ::shrink]
        small_parent = field_of[::shrink, ::shrink]
        h, w = small_parent.shape[:2]
        for y in range(0, small_child.shape[0] - h + 1):
            for x in range(0, small_child.shape[1] - w + 1):
                gap = float(
                    np.linalg.norm(
                        small_child[y : y + h, x : x + w] - small_parent, axis=-1
                    ).mean()
                )
                if best is None or gap < best[0]:
                    best = (gap, scale, x * shrink, y * shrink, field_of)
    if best is None:
        raise PolyweaveError(
            "fetch.no-parent",
            f"{parent_path} does not fit inside {variation} at any scale tried",
            "a reframe grows the frame; check it is the reframe of this parent",
        )
    _, scale, x0, y0, field_of = best
    h, w = field_of.shape[:2]
    _, x, y = min(
        (
            float(
                np.linalg.norm(after[y : y + h, x : x + w] - field_of, axis=-1).mean()
            ),
            x,
            y,
        )
        for y in range(max(0, y0 - 4), min(ch - h, y0 + 4) + 1)
        for x in range(max(0, x0 - 4), min(cw - w, x0 + 4) + 1)
    )
    region = np.linalg.norm(after[y : y + h, x : x + w] - field_of, axis=-1)
    worst = float(measure.pooled(region, np.ones(region.shape, dtype=bool)).max())
    return {"scale": scale, "x": x, "y": y, "width": w, "height": h}, worst


def _scaled(image, size):
    from PIL import Image as PILImage

    from .image import Image

    if image.size == size:
        return image
    scaled = PILImage.fromarray(image.rgba).resize(size, PILImage.Resampling.LANCZOS)
    return Image(path=image.path, rgba=np.asarray(scaled), had_alpha=image.had_alpha)


def _resized(image, size):
    """The variation at its parent's size, so a pixel is compared with its own."""
    from PIL import Image as PILImage

    from .image import Image

    scaled = PILImage.fromarray(image.rgba).resize(size, PILImage.Resampling.LANCZOS)
    return Image(path=image.path, rgba=np.asarray(scaled), had_alpha=image.had_alpha)
