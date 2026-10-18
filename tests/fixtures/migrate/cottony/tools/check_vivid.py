"""Fail when the board stops being as vivid as the art it was cut from.

Run:  python tools/check_vivid.py

RK99's finding was that "washed out" is true but not where it sounds. Averaged over the
board the two screens already matched - mean saturation 0.31 against 0.32 - and the whole
difference sat at the top end: the 99th percentile was 0.68 here against 0.88 in
`screen1.png`. So the number this guards is a percentile, never a mean.

The bar is no longer here. It is docs/design/accept/board_drawn.accept.toml and
board_mesh.accept.toml, one per board (RK121: the mesh board sat at 0.776 for as long as only
the drawn one was read), and this runs polyweave's check of each against the committed shot.
The specs say where the bound came from and when to re-measure it; a search or
`python -m polyweave accept.verify` reads the same two files.
"""

from __future__ import annotations

import sys
from pathlib import Path

from polyweave import accept

ROOT = Path(__file__).resolve().parents[1]
ACCEPT = Path("docs/design/accept")

## the boards held to the concept art, and the spec each one is held by
BOARDS = (
    ("the drawn board", "board_drawn.accept.toml"),
    ("the mesh board", "board_mesh.accept.toml"),
)


def main() -> int:
    failed = False
    for named, filename in BOARDS:
        spec = accept.read(ACCEPT / filename, ROOT)
        found = accept.check(spec, ROOT / spec.artefact, root=ROOT)
        for one in found["predicates"]:
            line = f"{named}: {one['measure']} {one['value']:.3f} against a floor of {one['min']}"
            if one["passed"]:
                print(f"{line} - inside it")
                continue
            failed = True
            print(f"{line} - losing its vivid core ({spec.artefact})")
            print("  a mean will not show this - check what lightens a body where the light falls")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
