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
- **Outside the mask, nothing should have changed.** `picture.against_parent` compares
  the unmasked region pixel for pixel, pooled, against `[tolerance] delta_e`, and
  measures the variation against its family's canon where a style is declared.

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
OPERATIONS = {"remix": "ideogram-v3/remix", "edit": "ideogram-v3/inpaint"}


@operation("picture.vary")
def vary(
    parent: Annotated[str, Param("the approved picture, under the project")],
    out: Annotated[str, Param("where the variation is written, under the project")],
    prompt: Annotated[str, Param("what the variation should show")],
    *,
    change: Annotated[
        str, Param("remix the whole, or edit inside a mask", choices=tuple(OPERATIONS))
    ] = "edit",
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
    at `strength` (the service's `image_weight`). Both are priced by the `remix` or
    `edit` row of `prices`. Both endpoints take a text prompt only, so a family's style
    is not carried into the request; `picture.against_parent` measures it afterwards.
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
    name = config.service(service)
    about = config.services()[name]
    base, key = picture._reached(name, about)
    price = picture._price(name, about.get("prices") or {}, change, rendering_speed)

    files = {"image": (source.name, source.read_bytes(), picture._mime(source))}
    payload: dict = {"prompt": prompt}
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

    Outside the mask, every pooled patch must sit within `[tolerance] delta_e` of the
    parent: a change there is the edit redrawing what it was not asked to. The
    silhouette outside the mask is held to `[tolerance] silhouette_iou`. A remix has no
    mask, so it is measured against the canon alone, where a style is declared.
    """
    from . import measure
    from .image import load as load_image

    config = load(root)
    here = config.root
    record = provenance.read(variation, root=here)
    lineage = (record.get("details") or {}).get("parent")
    if not lineage:
        raise PolyweaveError(
            "fetch.no-parent",
            f"{variation} records no parent, so there is nothing to hold it against",
            "measure it against its canon with style.drift instead",
        )
    tolerances = config.tolerances()
    parent = load_image(here / lineage["path"])
    child = load_image(here / variation)
    if child.size != parent.size:
        child = _resized(child, parent.size)
    details = record["details"]
    kept = np.ones(parent.rgba.shape[:2], dtype=bool)
    if details.get("mask"):
        kept = load_image(here / details["mask"]).rgba[..., 0] > 127
    failed = []
    found: dict = {"variation": variation, "parent": lineage["path"]}
    if details.get("mask"):
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
    if style.in_force(config, family) is not None:
        drifted = style.drift(variation, family, root=here)
        found["canon"] = {"judged": drifted["judged"], "drifted": drifted["drifted"]}
        failed.extend(
            f"{key} drifted from the canon: "
            f"{drifted['measures'][key].get('which_way', 'off')}"
            for key in drifted["drifted"]
        )
    found["failed"] = failed
    found["passed"] = not failed
    found["not_checked"] = ["whether it shows what was asked for"]
    return found


def _resized(image, size):
    """The variation at its parent's size, so a pixel is compared with its own."""
    from PIL import Image as PILImage

    from .image import Image

    scaled = PILImage.fromarray(image.rgba).resize(size, PILImage.Resampling.LANCZOS)
    return Image(path=image.path, rgba=np.asarray(scaled), had_alpha=image.had_alpha)
