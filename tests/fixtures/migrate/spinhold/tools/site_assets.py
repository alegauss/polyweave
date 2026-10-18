"""Write the promo site's images into site/assets/, from the running game and art/brand/.

Every screenshot on the page is a frame of the game itself, captured by
dev/site_shots.gd at 1920 by 1080 and cut down here, so the page can never show a look
the game does not have. The logo files are the vector set make_brand.py draws, copied as
they are; the two raster icons are made from them by dev/svg_png.gd, Godot's own SVG
loader, so this needs no SVG library.

    python tools/site_assets.py              # capture, convert, write site/assets/
    python tools/site_assets.py --shots DIR  # reuse PNGs already captured into DIR
    python tools/site_assets.py --check      # every source still there; writes nothing
    python tools/site_assets.py --locale pt_BR   # the frames with the game's words in them,
                                                 # captured in pt-BR into site/assets/pt-BR/

Spawns are random, so a re-run captures different frames: look at the gallery before
committing what it wrote. The three Foremen are the exception: dev/colossus_stage.gd
frames each from a shot in dev/colossus_shots.json (RK124).

The captures go through polyweave's `capture.run` (RK98): it states the locale and the
resolution from `[capture]`, checks the game applied them, and writes a record beside each
picture of what it was taken in and what build it shows. They land in the project's work
area, and every file written into site/assets/ from one gets a record naming it, so a page
picture says which capture it came from.

The game speaks pt-BR (RK163), and a frame of play shows its words: the HUD, a ring's
name. So the frames in LOCALISED are captured again in each other locale (RK167), stating
that locale to `capture.run`, and written into site/assets/<locale>/ under the same names;
the page's language switch (site/app.js) shows that set. The Lattice's six models, the
Holders and the logos carry no words and stay one set. The store's screenshots (STORE) are
written full size into art/store/screenshots/<locale>/ in the same run.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image
# the paths polyweave's layout split gave these modules (PW499); PW520 is the carry-over
from polyweave.kernel import provenance
from polyweave.kernel.config import load
from polyweave.layers.engine import capture as polyweave_capture

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "art" / "brand"
OUT = ROOT / "site" / "assets"
# the studio section signs with the label's flat mark, copied from the label page
# (games.viglet.com, the viglet/games repository) so all three pages sign alike
LABEL_MARK = ROOT.parent / "games" / "site" / "assets" / "viglet-games.svg"

# name: the arguments dev/site_shots.gd takes for that frame
SHOTS = {
    "swarm": ["--phase=1", "--frames=1000", "--hold=move_left,fire_left"],
    "waist": ["--phase=1", "--frames=900", "--hold=move_left,fire_left,move_up"],
    "bow": ["--frames=700", "--hold=move_right,fire_right"],
    # the Sunline burst through a wave, for the store (RK167)
    "burst": ["--phase=1", "--frames=1000", "--hold=move_left,fire_left", "--charged", "--press=overdrive@970"],
    # the crew draft dealing an evolution's gold card, and an evolution's first act (RK223)
    "draft": ["--mode=run", "--phase=1", "--frames=520", "--hold=move_left,fire_left", "--draft=300"],
    "evolution": ["--mode=run", "--phase=1", "--frames=606", "--hold=move_left,fire_left", "--evolve=600"],
    # the game's own voxel colonists, staged by dev/holders.tscn (RK98)
    "holders": ["--scene=res://dev/holders.tscn", "--frames=90"],
}
# the roster's six machines, each the game's own model on a clear background, staged by
# dev/lattice.tscn the way the codex draws it: they replace the hand-drawn 8x8 sprites
FOES = ["drone", "gunship", "turret", "seeker", "mine_layer", "keeper"]
for _foe in FOES:
    SHOTS[f"foe-{_foe}"] = ["--scene=res://dev/lattice.tscn", "--frames=30", f"--foe={_foe}"]

# name: the shot of dev/colossus_shots.json that dev/colossus_stage.gd frames it from. The
# Foremen are staged, not caught in play (RK124): a fight rarely puts a colossus whole in
# the ship's camera, and a stage frames it the same way every time.
STAGED = {
    "mason": "spire_hero",
    "loom": "leviathan_hero",
    "kiln": "warden_hero",
}

# (source, output, largest side in px or None to keep the size, crop box or None)
IMAGES = [
    ("swarm", "hero.webp", 1400, None),
    ("waist", "gallery-waist.webp", 1600, None),
    ("bow", "gallery-bow.webp", 1600, None),
    ("mason", "gallery-mason.webp", 1600, None),
    ("loom", "gallery-loom.webp", 1600, None),
    ("kiln", "gallery-kiln.webp", 1600, None),
    ("holders", "holders.webp", 900, (0, 110, 1920, 927)),
] + [
    # the middle square of the frame, where the stage fits the model; kept with its alpha
    (f"foe-{foe}", f"foe-{foe}.webp", 360, (420, 0, 1500, 1080)) for foe in FOES
]

# the store's screenshots (art/store/page.md), each the shot it is taken from: written
# full size into art/store/screenshots/<locale>/ for a locale other than [capture]'s
STORE = {"ring_swarm": "swarm", "waist": "waist", "bow": "bow", "bomb": "burst",
         "mason": "mason", "loom": "loom", "kiln": "kiln", "draft": "draft",
         "evolution": "evolution"}
STORE_OUT = ROOT / "art" / "store" / "screenshots"

# the pictures captured again in another locale, since they show the game's words
LOCALISED = {"hero.webp", "gallery-waist.webp", "gallery-bow.webp", "gallery-mason.webp",
             "gallery-loom.webp", "gallery-kiln.webp"}

COPIES = [
    (BRAND / "spinhold-wordmark-clear.svg", "spinhold-wordmark.svg"),
    (BRAND / "spinhold-symbol.svg", "spinhold-symbol.svg"),
    (BRAND / "spinhold-favicon.svg", "favicon.svg"),
    (LABEL_MARK, "viglet-games.svg"),
]

# (svg, png written to the work dir, scale): the symbol is drawn at 512 px
RASTERS = [
    (BRAND / "spinhold-symbol.svg", "apple-touch-icon.png", 180 / 512),
    (BRAND / "spinhold-wordmark-clear.svg", "wordmark.png", 1.0),
]

OG_SIZE = (1200, 630)


def godot() -> str:
    engine = os.environ.get("GODOT") or shutil.which("godot")
    if not engine:
        sys.exit("Set GODOT to the Godot 4.7 executable (see run.cmd).")
    return engine


def run(*args: str) -> None:
    result = subprocess.run([godot(), "--path", str(ROOT), *args], capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"godot {' '.join(args)} failed:\n{result.stdout}\n{result.stderr}")


def capture(into: Path, locale: str | None = None, only: set[str] | None = None) -> None:
    """Every shot, or those `only` names, through polyweave, in the environment [capture]
    states, its locale replaced by `locale` where one is given."""
    environment = polyweave_capture.wanted(ROOT, locale=locale)
    for name, args in SHOTS.items():
        if only is not None and name not in only:
            continue
        print(f"capturing {name}")
        found = polyweave_capture.run(
            "dev/site_shots.gd",
            expect=r"^SHOT (?P<shot>\S+) ",
            produces=("shot",),
            root=ROOT,
            environment=environment,
            args=("--resolution", "1920x1080", "--",
                  f"--out={(into / f'{name}.png').as_posix()}", *args),
        )
        if not found["ok"]:
            sys.exit(f"capturing {name} failed: {found.get('why') or found['environment']}")
    for name, shot in STAGED.items():
        if only is not None and name not in only:
            continue
        print(f"staging {name}")
        found = polyweave_capture.run(
            "dev/colossus_stage.gd",
            expect=r"^SHOT (?P<shot>\S+) ",
            produces=("shot",),
            root=ROOT,
            environment=environment,
            args=("--", f"--shot={shot}", f"--out={(into / f'{name}.png').as_posix()}"),
        )
        if not found["ok"]:
            sys.exit(f"staging {name} failed: {found.get('why') or found['environment']}")


def recorded(target: Path, source: Path) -> None:
    """A record beside a site file, naming the capture or the art it was made from."""
    provenance.write(
        provenance.build(
            "picture", target,
            inputs=[provenance.source("original", source, root=ROOT)],
            root=ROOT,
        ),
        root=ROOT,
    )


def check(shots: Path | None) -> list[str]:
    missing = [str(p) for p, _ in COPIES if not p.exists()]
    missing += [str(s) for s, _, _ in RASTERS if not s.exists()]
    for source, _, _, _ in IMAGES:
        if isinstance(source, Path):
            if not source.exists():
                missing.append(str(source))
        elif source not in SHOTS and source not in STAGED:
            missing.append(f"shot {source}")
        elif shots and not (shots / f"{source}.png").exists():
            missing.append(str(shots / f"{source}.png"))
    return missing


def save(image: Image.Image, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.suffix == ".webp":
        image.save(target, "WEBP", quality=84, method=6)
    elif target.suffix == ".jpg":
        image.convert("RGB").save(target, "JPEG", quality=86, optimize=True, progressive=True)
    else:
        image.save(target, optimize=True)
    print(target.relative_to(ROOT))


def localised(locale: str, shots: Path | None) -> None:
    """The pictures in LOCALISED, captured in `locale` and written into
    site/assets/<locale as a page names it, e.g. pt-BR>/ under the same names, and the
    store's screenshots into art/store/screenshots/<that>/."""
    wanted = [(source, name, largest, box) for source, name, largest, box in IMAGES if name in LOCALISED]
    folder = OUT / locale.replace("_", "-")
    if shots is None:
        shots = load(ROOT).path("paths.work") / f"site-shots-{locale}"
        shots.mkdir(parents=True, exist_ok=True)
        capture(shots, locale, {source for source, _, _, _ in wanted} | set(STORE.values()))
    write_store(locale, shots)
    for source, name, largest, box in wanted:
        path = shots / f"{source}.png"
        image = Image.open(path).convert("RGB")
        if box:
            image = image.crop(box)
        if largest:
            image.thumbnail((largest, largest), Image.LANCZOS)
        save(image, folder / name)
        recorded(folder / name, path)


def store_folder(locale: str) -> Path:
    """Where the store's screenshots in `locale` go: art/store/screenshots/ for [capture]'s
    own locale, a folder named as a page names the locale (pt-BR) for any other."""
    if locale == polyweave_capture.wanted(ROOT)["locale"]:
        return STORE_OUT
    return STORE_OUT / locale.replace("_", "-")


def write_store(locale: str, shots: Path) -> None:
    """The store's screenshots from the captures in `shots`, full size, each recorded."""
    for name, source in STORE.items():
        path = shots / f"{source}.png"
        target = store_folder(locale) / f"{name}.png"
        save(Image.open(path).convert("RGB"), target)
        recorded(target, path)


def store(locale: str, shots: Path | None) -> None:
    """Only the store's screenshots (RK223), captured in `locale` unless `shots` has them."""
    if shots is None:
        shots = load(ROOT).path("paths.work") / f"store-shots-{locale}"
        shots.mkdir(parents=True, exist_ok=True)
        capture(shots, locale, set(STORE.values()))
    write_store(locale, shots)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="check the sources, write nothing")
    parser.add_argument("--shots", type=Path, help="a directory of PNGs already captured")
    parser.add_argument("--locale", help="capture the frames with words in them in this locale, e.g. pt_BR")
    parser.add_argument("--store", action="store_true",
                        help="only the store's screenshots, in --locale or [capture]'s own")
    args = parser.parse_args()
    if args.store:
        store(args.locale or polyweave_capture.wanted(ROOT)["locale"], args.shots)
        return

    # a locale's run needs only its own frames, which `localised` opens
    missing = check(None if args.locale else args.shots)
    if missing:
        sys.exit("missing sources:\n  " + "\n  ".join(missing))
    if args.check:
        print("every source is there")
        return
    if args.locale and args.locale != polyweave_capture.wanted(ROOT)["locale"]:
        localised(args.locale, args.shots)
        return

    with tempfile.TemporaryDirectory(prefix="spinhold-site-") as temp:
        work = Path(temp)
        shots = args.shots or load(ROOT).path("paths.work") / "site-shots"
        if not args.shots:
            shots.mkdir(parents=True, exist_ok=True)
            capture(shots)

        raster_args = []
        for svg, png, scale in RASTERS:
            raster_args += [svg.as_posix(), (work / png).as_posix(), f"{scale:g}"]
        run("--headless", "-s", "res://dev/svg_png.gd", "--", *raster_args)

        for source, name, largest, box in IMAGES:
            path = source if isinstance(source, Path) else shots / f"{source}.png"
            image = Image.open(path).convert("RGBA" if name.startswith("foe-") else "RGB")
            if box:
                image = image.crop(box)
            if largest:
                image.thumbnail((largest, largest), Image.LANCZOS)
            save(image, OUT / name)
            recorded(OUT / name, path)

        for source, name in COPIES:
            shutil.copyfile(source, OUT / name)
            print((OUT / name).relative_to(ROOT))

        save(Image.open(work / "apple-touch-icon.png"), OUT / "apple-touch-icon.png")

        # the link preview: the swarm frame cut to 1.91:1, darkened low down, the name over it
        frame = Image.open(shots / "swarm.png").convert("RGBA")
        frame = frame.resize((OG_SIZE[0], round(frame.height * OG_SIZE[0] / frame.width)), Image.LANCZOS)
        top = (frame.height - OG_SIZE[1]) // 2
        og = frame.crop((0, top, OG_SIZE[0], top + OG_SIZE[1]))
        shade = Image.linear_gradient("L").resize(OG_SIZE)
        og = Image.composite(Image.new("RGBA", OG_SIZE, (11, 11, 26, 255)), og, shade.point(lambda v: v * 0.8))
        mark = Image.open(work / "wordmark.png")
        mark.thumbnail((760, 400), Image.LANCZOS)
        og.alpha_composite(mark, ((OG_SIZE[0] - mark.width) // 2, OG_SIZE[1] - mark.height - 16))
        save(og, OUT / "og.jpg")
        recorded(OUT / "og.jpg", shots / "swarm.png")


if __name__ == "__main__":
    main()
