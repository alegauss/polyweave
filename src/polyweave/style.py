"""What a project's pictures look like, declared once, and a canon only a person grows.

§PW166: a generator asked for consistency in prose gives consistency by luck. Two
pictures of one character from one prompt differ in palette, line weight and
proportion, and a refinement drifts further from the picture it refines. So the style
is an **input every call carries**, not an adjective in a prompt:

- `[style]` (or `[style.<family>]`, one per asset family) declares a `palette`, as
  values, and a `skeleton`, the style block every structured prompt starts from;
- `picture.buy` composes each structured prompt over the skeleton, and the skeleton
  wins where the prompt says otherwise, because a style overridden per call is the
  drift it exists to stop;
- `canon` is a directory of pictures a person approved, each with its described prompt
  where there is one, and a `canon.json` naming the verdict that admitted it.

**The canon grows only by a person's verdict.** `admit` is not an operation: the one
caller is `verdict.judge`, carrying what a person said. An agent that could add its own
output to the canon would make its drift the standard.
"""

from __future__ import annotations

import copy
import json
import shutil
from datetime import date as Date
from pathlib import Path
from typing import Annotated

from . import provenance
from .config import Config, load
from .describe import Param, operation
from .errors import PolyweaveError
from .files import read_text_retrying, write_atomic

#: The file in a canon directory that says why each picture is in it.
LEDGER = "canon.json"


def in_force(config: Config, family: str | None) -> tuple[str, dict] | None:
    """The style a picture is held to, or none where the project declares no style."""
    if not config.states("style") and family is None:
        return None
    return config.style(family)


def compose(json_prompt: dict, style: dict) -> dict:
    """A structured prompt over the family's skeleton, with its palette.

    The skeleton's keys win over the prompt's own style keys; the prompt adds what the
    skeleton leaves unsaid. The palette, where declared, is the palette.
    """
    composed = copy.deepcopy(json_prompt)
    own = dict(composed.get("style_description") or {})
    described = {**own, **copy.deepcopy(style.get("skeleton") or {})}
    if style.get("palette"):
        described["color_palette"] = list(style["palette"])
    if described:
        composed["style_description"] = described
    return composed


@operation("style.read")
def read(
    family: Annotated[str, Param("the asset family; needed only among several")] = None,
    root: Annotated[str, Param("the project whose style this is")] = ".",
) -> dict:
    """One family's declared style and the pictures a person admitted to its canon."""
    name, style = load(root).style(family)
    return {"family": name, **style, "admitted": admitted(style)}


def admitted(style: dict) -> list[dict]:
    """What the canon holds, with the verdict each picture came in on."""
    if not style.get("canon"):
        return []
    text = read_text_retrying(Path(style["canon"]) / LEDGER)
    return json.loads(text) if text else []


def admit(
    picture: str,
    *,
    family: str | None,
    why: str,
    choice: str,
    when: str = "",
    root: str | Path = ".",
) -> dict:
    """Copy an approved picture into its family's canon, with the verdict admitting it.

    Called by `verdict.judge` and by nothing else. The described prompt beside the
    picture (`<name>.prompt.json`, from `picture.describe`) goes with it, so a canon
    picture carries its own terms. Admitting one picture twice is a no-op.
    """
    config = load(root)
    here = config.root
    name, style = config.style(family)
    if not style.get("canon"):
        raise PolyweaveError(
            "style.no-canon",
            f"the {name} style declares no canon, so there is nowhere to admit "
            f"{picture} to",
            f"set canon under [style.{name}] to a directory under the project"
            if name != "default"
            else "set canon under [style] to a directory under the project",
        )
    source = here / picture
    digest, _ = provenance.sha256_of(source)
    canon = Path(style["canon"])
    held = admitted(style)
    already = next((e for e in held if e["sha256"] == digest), None)
    if already:
        return already
    canon.mkdir(parents=True, exist_ok=True)
    landed = canon / source.name
    shutil.copy2(source, landed)
    described = source.with_suffix(".prompt.json")
    prompt = None
    if described.is_file():
        shutil.copy2(described, canon / described.name)
        prompt = described.name
    entry = {
        "picture": landed.name,
        "sha256": digest,
        "from": provenance.relative(source, here),
        "prompt": prompt,
        "verdict": {
            "choice": choice,
            "why": why,
            "when": when or Date.today().isoformat(),
        },
    }
    write_atomic(
        canon / LEDGER, json.dumps([*held, entry], indent=2, sort_keys=True) + "\n"
    )
    return entry
