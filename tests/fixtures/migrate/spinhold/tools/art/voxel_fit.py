"""Fit a voxel declaration's proportions to its reference mesh, and write them back.

    python tools/art/voxel_fit.py art/voxels/ship.toml assets/models/ship.glb
        [--views front,top] [--budget 400]

polyweave's fit (its PW98) searches the parameters a declaration's `[search.<param>]`
tables permit for the best overlap between the model's silhouettes and the reference's,
each cropped to its own bounds so proportion is compared and framing is not. It has no
operation of its own yet (polyweave PW230), so this is the short script that calls it and
puts the best numbers into the declaration's `[params]`, where the next build reads them.
It writes the model's contact sheet beside the drafts in `.polyweave/voxel-drafts/`.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from polyweave.geometry import read
from polyweave.geometry.voxel_fit import fit

ROOT = Path(__file__).resolve().parents[2]


def write_params(source: Path, best: dict) -> str:
    """The declaration's text with each fitted parameter's value replaced in place."""
    text = source.read_text(encoding="utf-8")
    for name, value in best.items():
        text, count = re.subn(
            rf"(?m)^({re.escape(name)}\s*=\s*)[-+0-9.eE]+",
            lambda found: f"{found.group(1)}{round(float(value), 4)}",
            text,
            count=1,
        )
        if count != 1:
            raise SystemExit(f"voxel_fit: {source} has no line `{name} = <number>` to write")
    return text


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("declaration")
    parser.add_argument("reference")
    parser.add_argument("--views", default="front,top")
    parser.add_argument("--budget", type=int, default=400)
    args = parser.parse_args(argv)

    source = ROOT / args.declaration
    document = read(source, root=ROOT)
    sheet = ROOT / ".polyweave" / "voxel-drafts" / f"{document['name']}.fit.png"
    sheet.parent.mkdir(parents=True, exist_ok=True)
    answer = fit(
        document,
        args.reference,
        views=tuple(args.views.split(",")),
        root=ROOT,
        budget=args.budget,
        sheet=sheet,
    )
    best = answer["best"]
    print("overlap per view:", {k: round(v, 3) for k, v in answer["views"].items()})
    print("best:", {k: round(float(v), 4) for k, v in best.items()})
    source.write_text(write_params(source, best), encoding="utf-8", newline="\n")
    print("wrote the fitted params into", args.declaration, "and the sheet to", sheet.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
