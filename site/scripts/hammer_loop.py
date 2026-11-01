"""The home page's loop: one real part going from refused to accepted (§PW663).

    python site/scripts/hammer_loop.py D:/Git/viglet/cottony

Cottony's pink hammer booster, in three of its own renders: the shape alone, the
textured one its owner refused on 2026-10-15 ("the pink hammer's edge has flaws"), and
the one accepted on 2026-10-23. Each is checked here, now, against Cottony's
`booster_hammer.accept.toml`, so the numbers under it are measured and never typed.
Writes `site/public/demo/hammer-loop.webm`, a still poster beside it, and
`hammer-loop.json`, the numbers the page's caption reads.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from polyweave.loop import accept

OUT = Path(__file__).resolve().parents[1] / "public" / "demo"
SPEC = "docs/design/accept/booster_hammer.accept.toml"
#: The three renders, in the order the search made them, with what a person said: a
#: person's verdict is the last word, so it is drawn as a reason like the measures.
STEPS = (
    (".polyweave/boosters/flat-hammer.png", "Attempt 1", None),
    (".polyweave/boosters/cv-hammer.png", "Attempt 2",
     (False, "a person: \u201cthe edge has flaws\u201d")),
    (".polyweave/boosters/booster_hammer.port.png", "Final",
     (True, "a person: accepted")),
)
#: The two predicates the refused render failed, shown under every step in plain words
#: (the owner, 2026-10-31: understood at a glance, numbers only as the proof).
SHOWN = (("head-reads-pink", "colour off by", "{:.2f}",
          ("right pink", "wrong pink", "wrong pink")),
         ("fills-its-well", "fills", "{:.3f}",
          ("right size", "too small", "too big")))

W, H, FPS = 1280, 720, 30
SECONDS = 9.0
#: When each column appears, and how long it takes to.
ENTERS, FADE = (0.3, 2.0, 4.6), 0.5
INK, DIM, PASS, FAIL, GROUND = "#ECECF1", "#8A8A96", "#5BD08A", "#FF6B6B", "#121216"


def _font(size: int):
    return ImageFont.load_default(size=size)


def _bound(found: dict) -> str:
    low, high = found.get("min"), found.get("max")
    if low is not None and high is not None:
        return f"{low:g} to {high:g}"
    return f"at most {high:g}" if high is not None else f"at least {low:g}"


def measured(cottony: Path) -> list[dict]:
    """Each step's render checked against the hammer's spec, as accept.check answers."""
    steps = []
    for picture, title, said in STEPS:
        checked = accept.checked(SPEC, picture, root=str(cottony))
        by_id = {one["id"]: one for one in checked["predicates"]}
        steps.append({
            "render": picture, "title": title, "said": said,
            "passed": checked["passed"], "failed": checked["failed"],
            "shown": [{"id": key, "label": label, "value": by_id[key]["value"],
                       "text": shape.format(by_id[key]["value"]),
                       "bound": _bound(by_id[key]), "passed": by_id[key]["passed"],
                       "says": _plain(by_id[key], words)}
                      for key, label, shape, words in SHOWN],
        })
    return steps


def _plain(found: dict, words: tuple[str, str, str]) -> str:
    """A measure's verdict in words: right, or which side of its bound it fell."""
    if found["passed"]:
        return words[0]
    low = found.get("min")
    return words[1] if low is not None and found["value"] < low else words[2]


def _mark(draw: ImageDraw.ImageDraw, x: int, y: int, size: int, passed: bool) -> None:
    """A tick or a cross, drawn: the default font holds neither."""
    colour, w = (PASS if passed else FAIL), max(3, size // 6)
    if passed:
        draw.line([(x, y + size * 0.55), (x + size * 0.38, y + size * 0.9),
                   (x + size, y + size * 0.1)], fill=colour, width=w, joint="curve")
    else:
        draw.line([(x, y), (x + size, y + size)], fill=colour, width=w)
        draw.line([(x, y + size), (x + size, y)], fill=colour, width=w)


def _arrow(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.line([(x - 26, y), (x + 18, y)], fill=DIM, width=5)
    draw.polygon([(x + 30, y), (x + 14, y - 13), (x + 14, y + 13)], fill=DIM)


def _frame(t: float, renders: list[Image.Image], steps: list[dict]) -> Image.Image:
    frame = Image.new("RGB", (W, H), GROUND)
    draw = ImageDraw.Draw(frame)
    draw.text((W // 2, 40), "You say what it must be. It retries until it is.",
              fill=INK, font=_font(36), anchor="mm")
    draw.text((W // 2, 80),
              "a real game asset, checked against its spec at every attempt",
              fill=DIM, font=_font(20), anchor="mm")
    for column, (render, step, entered) in enumerate(zip(renders, steps, ENTERS,
                                                         strict=True)):
        shown = min(max((t - entered) / FADE, 0.0), 1.0)
        if not shown:
            continue
        x = (column * 2 + 1) * W // 6
        passed = step["passed"]
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ink = ImageDraw.Draw(layer)
        if column:
            _arrow(ink, column * W // 3, 260)
        ink.text((x, 122), step["title"], fill=DIM, font=_font(24), anchor="mm")
        layer.alpha_composite(render, (x - render.width // 2, 140))
        # The verdict as a badge, the one thing read at a glance.
        colour = PASS if passed else FAIL
        ink.rounded_rectangle([x - 112, 418, x + 112, 470], radius=26,
                              fill=colour + "26", outline=colour, width=3)
        _mark(ink, x - 92, 432, 24, passed)
        ink.text((x + 14, 444), "PASSES" if passed else "FAILS", fill=colour,
                 font=_font(30), anchor="mm")
        reasons = [(one["passed"], one["says"]) for one in step["shown"]]
        if step["said"]:
            reasons.append(step["said"])
        for row, (good, words) in enumerate(reasons):
            y = 500 + row * 40
            _mark(ink, x - 130, y - 10, 20, good)
            ink.text((x - 98, y), words, fill=INK, font=_font(24), anchor="lm")
        proof = "   ".join(f"{one['label']} {one['text']} ({one['bound']})"
                           for one in step["shown"])
        ink.text((x, 676), proof, fill=DIM, font=_font(14), anchor="mm")
        alpha = layer.getchannel("A").point(lambda v, s=shown: int(v * s))
        layer.putalpha(alpha)
        frame.paste(layer, (0, 0), layer)
    # The loop fades out at its end, so it starts again from the dark it began in.
    if t > SECONDS - 0.5:
        frame = Image.blend(frame, Image.new("RGB", (W, H), GROUND),
                            (t - (SECONDS - 0.5)) / 0.5)
    return frame


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: hammer_loop.py <cottony root>", file=sys.stderr)
        return 2
    cottony = Path(argv[0]).resolve()
    steps = measured(cottony)
    renders = [Image.open(cottony / step["render"]).convert("RGBA").resize(
        (270, 270), Image.Resampling.LANCZOS) for step in steps]
    OUT.mkdir(parents=True, exist_ok=True)
    encoder = subprocess.Popen(
        [shutil.which("ffmpeg"), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt",
         "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libvpx-vp9",
         "-b:v", "0", "-crf", "38", "-row-mt", "1", "-an",
         str(OUT / "hammer-loop.webm")],
        stdin=subprocess.PIPE)
    for n in range(int(SECONDS * FPS)):
        encoder.stdin.write(_frame(n / FPS, renders, steps).tobytes())
    encoder.stdin.close()
    if encoder.wait():
        print("hammer_loop: ffmpeg did not write the loop", file=sys.stderr)
        return 1
    _frame(SECONDS - 1.0, renders, steps).save(OUT / "hammer-loop-poster.webp",
                                               quality=82)
    (OUT / "hammer-loop.json").write_text(
        json.dumps({"spec": SPEC, "steps": steps}, indent=1) + "\n", encoding="utf-8")
    size = (OUT / "hammer-loop.webm").stat().st_size
    print(f"hammer_loop: {size / 1024:.0f} KB, {SECONDS:g}s at {W}x{H}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
