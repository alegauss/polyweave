"""Buy a model from Meshy, spending only against the ceiling in polyweave.toml.

Run:  python tools/art/meshy.py --list
      python tools/art/meshy.py ship --dry-run
      python tools/art/meshy.py ship
      python tools/art/meshy.py --all

The buying is polyweave's `mesh.buy` (RK95): the price is `[service.meshy] prices` for the
model, `purchase.allow` refuses what `[budget.meshy]` does not cover, the balance is read
either side of the task, and the glb lands with its record before the ledger names it.
Meshy deletes a task's files 72 hours after it finishes, so the glb is committed and a task
id is a receipt, never a way to fetch it again. What stays here is this game's own: which
assets there are, what each is asked for, and the display stand cut off some of them.

The request is a text-to-3d `preview`: geometry and no texture. The neon look is our own
emissive material in Godot, so a painted texture would be paid for and thrown away.

The raw download lands in tools/art/meshy/, which Godot ignores, and
`polyweave.normalise.ingest` writes the copy the game loads into assets/models/, put in the
project's frame once so no scene carries a correction angle.

The key comes from the variable [service.meshy] names, and polyweave never prints it.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from polyweave import mesh_buy, normalise, provenance, purchase, readable
from polyweave.config import load
from polyweave.errors import PolyweaveError

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "tools" / "art" / "meshy"
#: Which of polyweave.toml's paid services this buys from, and whose ceiling it spends.
SERVICE = "meshy"

# every prompt ends in the same words, because the style is one decision and not one per asset
STYLE = "low poly hard-surface game asset, clean simple silhouette, no base, no pedestal"


@dataclass(frozen=True)
class Asset:
    prompt: str
    # pinned, never "latest": a mesh that silently changes with the service records nothing
    ai_model: str = "meshy-5"
    target_polycount: int = 8000
    # the axis the model's nose points along once ingested, where the principal axes cannot say
    # which end is the front; polyweave keeps the frame it arrived in when nothing states it
    rotation: tuple[tuple[float, ...], ...] | None = None
    # the service puts some models on a display stand whatever the prompt says; faces whose
    # centre sits below this share of the height are the stand, measured per asset
    strip_below: float = 0.0

    @property
    def asked(self) -> str:
        return f"{self.prompt}, {STYLE}"

ASSETS = {
    # the hero asset, and the one worth the dearer model (RK7)
    "ship": Asset(
        prompt=(
            "sleek arrow-shaped sci-fi starfighter seen from the side, long pointed nose, two"
            " swept-back wings, twin engine nozzles at the rear, small cockpit canopy"
        ),
        ai_model="meshy-7",
        target_polycount=12000,
    ),
    # one silhouette per role, so a swarm reads apart without colour (RK8)
    "drone": Asset(
        prompt="small alien attack drone, round spherical core ringed with sharp spikes",
        # a loose disc at 0..0.06 of the height; the body starts at 0.11
        strip_below=0.08,
    ),
    "gunship": Asset(
        prompt=(
            "heavy alien gunship, wide blocky armoured hull, two long forward cannons,"
            " angular plating"
        ),
    ),
    "keeper": Asset(
        prompt=(
            "alien abductor pod, rounded dome hull on top, a four-fingered grabbing claw"
            " hanging underneath"
        ),
    ),
    "seeker": Asset(
        prompt="alien dart missile ship, narrow needle body, four small fins at the back, one red eye at the front",
        # a cone and a post up to 0.45 of the height, joined to the body, which starts at 0.5
        strip_below=0.49,
    ),
}


def held(name: str) -> dict | None:
    """The ledger entry for this asset whose file is still on disk, or None."""
    raw = RAW / f"{name}.glb"
    for entry in purchase.read(ROOT):
        if entry.get("artefact") == raw.relative_to(ROOT).as_posix() and raw.exists():
            return entry
    return None


def strip(name: str, asset: Asset) -> Path:
    """The bought mesh without its display stand, recorded as derived from it.

    Cut in the raw file's own frame: the ingest after it only scales and moves, so a share
    of the height means the same thing on either side of it.
    """
    raw = RAW / f"{name}.glb"
    mesh = normalise.read_mesh(raw)
    points = np.asarray(mesh["vertices"], dtype=float)
    faces = normalise.triangles(mesh["faces"])
    low, high = points[:, 1].min(), points[:, 1].max()
    cut = low + asset.strip_below * (high - low)
    kept = faces[points[faces].mean(axis=1)[:, 1] >= cut]
    used, faces_left = np.unique(kept, return_inverse=True)
    out = RAW / f"{name}.stripped.glb"
    normalise.write_mesh(
        {"vertices": points[used], "faces": faces_left.reshape(-1, 3).tolist()}, out
    )
    record = provenance.build(
        "mesh",
        out,
        inputs=[provenance.source("mesh", raw, root=ROOT)],
        params={"strip_below": asset.strip_below},
        measurements={"faces": len(kept), "dropped": len(faces) - len(kept)},
        root=ROOT,
    )
    provenance.write(record, root=ROOT)
    return out


def ingest(name: str, asset: Asset) -> dict:
    rotation = np.array(asset.rotation, dtype=float) if asset.rotation else None
    out = load(ROOT).path("paths.meshes") / f"{name}.glb"
    source = strip(name, asset) if asset.strip_below else RAW / f"{name}.glb"
    return normalise.ingest(source, out=out, rotation=rotation, root=ROOT)


def price(asset: Asset) -> float:
    """What one preview of this asset is quoted at, off polyweave.toml's price table."""
    prices = load(ROOT).services()[SERVICE].get("prices") or {}
    return float(prices.get(asset.ai_model, float("nan")))


def fetch(name: str, asset: Asset) -> None:
    if entry := held(name):
        print(f"  {name}: already held (task {entry['task_id']}); nothing to spend")
        return
    entry = mesh_buy.buy(
        out=str((RAW / f"{name}.glb").relative_to(ROOT)),
        prompt=asset.asked,
        model=asset.ai_model,
        polycount=asset.target_polycount,
        service=SERVICE,
        root=ROOT,
    )
    flag = "  (not what was expected)" if entry["surprised"] else ""
    print(f"  {name}: task {entry['task_id']}, spent {entry['credits']:g}{flag}")


def show_list() -> None:
    left = purchase.remaining(ROOT, service=SERVICE)
    print(f"budget: {left['left']:g} of {left['declared']:g} left, until {left['expires']}")
    for name, asset in ASSETS.items():
        entry = held(name)
        state = f"held, cost {entry['credits']:g}" if entry else f"not fetched, ~{price(asset):g}"
        print(f"  {name:8} {asset.ai_model:8} {state}")


def main() -> int:
    readable()
    if os.environ.get("CI"):
        raise SystemExit("meshy.py does not run in CI: it spends credits and needs a secret")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("asset", nargs="*", help="which assets: " + ", ".join(ASSETS))
    parser.add_argument("--all", action="store_true", help="every asset not yet held")
    parser.add_argument("--list", action="store_true", help="what is defined, held and left")
    parser.add_argument("--dry-run", action="store_true", help="print the request, send nothing")
    parser.add_argument("--ingest-only", action="store_true", help="re-normalise what is held")
    args = parser.parse_args()

    names = list(ASSETS) if args.all else args.asset
    if args.list or not names:
        show_list()
        return 0
    unknown = [n for n in names if n not in ASSETS]
    if unknown:
        raise SystemExit(f"unknown asset(s) {unknown}; pick from {', '.join(ASSETS)}")

    try:
        for name in names:
            asset = ASSETS[name]
            if args.dry_run:
                left = purchase.remaining(ROOT, service=SERVICE)
                print(f"{name}: {asset.ai_model}, {asset.target_polycount} triangles, "
                      f"~{price(asset):g} of {left['left']:g} credits left")
                print(f"  prompt: {asset.asked}")
                continue
            if not args.ingest_only:
                fetch(name, asset)
            if (RAW / f"{name}.glb").exists():
                found = ingest(name, asset)
                size = ", ".join(f"{v:.2f}" for v in found["size"])
                print(f"  {name}: ingested, {found['faces']} faces, size ({size})")
    except PolyweaveError as refused:
        print(refused, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
