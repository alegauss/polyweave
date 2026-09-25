"""One local page to look at, and one call to answer from it (§PW172).

A verdict is the one step the loop cannot automate, and it was the slowest: the person
saw a render only by opening files by hand, so in practice they saw the agent's
description of it, which is the agent's judgement arriving where theirs was asked for.

`python -m polyweave review` serves one page, bound to 127.0.0.1 and nothing else, from
static files that ship with the plugin, on the standard library's server. No build, no
account, nothing to install.

**The page is a reader.** Everything it shows is already on disk: `loop.pending`, the
sittings `verdict.sitting` laid out, their sheets and the project's files. It keeps no
state of its own, so it cannot disagree with the files, and a second page shows the
same.

**It has one write**: `verdict.judge`, with the members taken from the sitting's own
manifest rather than from the page, and the person's choice and sentence. There is no
second path into a spec or a canon for a bug to live on. That is why this is not the
graphical editor the non-goal excludes: it edits nothing an agent could not.
"""

from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np

from . import loop, verdict
from .config import load
from .errors import PolyweaveError
from .files import read_text_retrying

#: Where the page's own files are, beside this module.
PAGE = Path(__file__).with_name("review_page")

#: The only address the server listens on. A verdict is a person's, and a page anyone
#: on the network could post to would make it anyone's.
HOST = "127.0.0.1"

#: A header a browser will not send across origins without asking first, and this
#: server never answers that question. So another site open in the same browser cannot
#: post a verdict here, which a form or a plain fetch from it otherwise could.
ASKED = "X-Polyweave"

#: What the page may be sent from the project: pictures, and the records beside them.
SERVED = {".png", ".jpg", ".jpeg", ".webp", ".json"}


def sittings(root) -> list[dict]:
    """Every sitting laid out in this project, newest last, as its manifest says."""
    config = load(root)
    index = config.path("paths.work") / "sittings.json"
    found = []
    for listed in json.loads(read_text_retrying(index) or "[]"):
        text = read_text_retrying(config.root / listed)
        if text is None:
            continue  # a sitting folder since deleted is simply not offered
        found.append({"manifest": listed, **json.loads(text)})
    return found


def looked_at(root) -> list[dict]:
    """Every gate run, each candidate with what is left of its service's ceiling.

    The refused beside the kept (§PW175), with the numbers the agent used and what is
    left to spend, read now rather than when the gate ran.
    """
    from . import picture, purchase

    left: dict = {}
    found = picture.gates(root)
    for run in found:
        for one in run["candidates"]:
            service = (one.get("bought") or {}).get("service")
            if service and service not in left:
                try:
                    left[service] = purchase.remaining(str(root), service=service)
                except PolyweaveError:
                    left[service] = None
            one["ceiling"] = left.get(service)
            one["compare"] = _compared_with(root, run, one)
    return found


def _compared_with(root, run: dict, one: dict) -> dict | None:
    """What a candidate is best compared against, and how (§PW176).

    A variation against its parent, as a slider with its mask outlined; anything else
    against its family's first canon picture, as a difference map.
    """
    from . import provenance, style

    config = load(root)
    here = config.root
    try:
        details = provenance.read(one["picture"], root=here).get("details") or {}
    except PolyweaveError:
        details = {}
    if (details.get("parent") or {}).get("path"):
        return {
            "old": details["parent"]["path"],
            "mode": "slider",
            "mask": details.get("mask"),
        }
    try:
        _, declared = config.style(run.get("family"))
    except PolyweaveError:
        return None
    canon = style.admitted(declared)
    if not canon:
        return None
    first = provenance.relative(Path(declared["canon"]) / canon[0]["picture"], here)
    return {"old": first, "mode": "difference", "mask": None}


def difference(root, old: str, new: str) -> dict:
    """Where two pictures differ above the noise floor, as a picture (§PW176).

    The floor is the one `measure.same` resolves, and the map lights a patch only where
    its pooled difference is past it, so what shows is what is above noise and not every
    resampled pixel. The map is derived output, written under `[paths] work`.
    """
    import hashlib

    from PIL import Image as PILImage

    from . import measure
    from .image import Image
    from .image import load as load_image

    config = load(root)
    here = config.root
    before, after = load_image(here / old), load_image(here / new)
    if after.size == before.size:
        said = measure.same(str(here / new), str(here / old), root=str(here))
    else:
        # Scaled to the old one's size, so a pixel is compared with its own; the floor
        # is then the strictest rung's, since no one render's record applies.
        scaled = PILImage.fromarray(after.rgba).resize(
            before.size, PILImage.Resampling.LANCZOS
        )
        after = Image(
            path=after.path, rgba=np.asarray(scaled), had_alpha=after.had_alpha
        )
        said = {
            "tolerance": config.tolerances().render_noise,
            "tolerance_from": "[tolerance] render_noise, the new picture scaled to the "
            "old one's size",
        }
    bar = float(said["tolerance"]) * measure.DELTA_E_FULL
    field = measure._delta_field(after, before)
    block = measure.POOL
    every = np.ones(field.shape, dtype=bool)
    patches = measure.pooled(field, every, block) > bar
    lit = np.kron(patches, np.ones((block, block), dtype=bool))[
        : field.shape[0], : field.shape[1]
    ]
    grey = after.rgba[..., :3].mean(axis=2, keepdims=True).repeat(3, axis=2) * 0.45
    shown = np.where(lit[..., None], np.array([255.0, 59.0, 48.0]), grey).astype(
        np.uint8
    )
    digest = hashlib.sha256(f"{old}\0{new}".encode()).hexdigest()[:16]
    target = config.path("paths.work") / "compare" / f"{digest}.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    PILImage.fromarray(shown).save(target)
    from .provenance import relative

    return {
        "map": relative(target, here),
        "changed_patches": int(patches.sum()),
        "patches": int(patches.size),
        "tolerance": said["tolerance"],
        "same": said.get("same"),
        "distance": said.get("distance"),
        "tolerance_from": said.get("tolerance_from"),
    }


def _overruled(root, body: dict) -> tuple[list[dict], str, str]:
    """A refused picture promoted by a person: the members, the sitting and family."""
    from . import picture

    ran = {one["id"]: one for one in picture.gates(root)}
    run = ran.get(str(body.get("gate") or ""))
    held = {one["picture"]: one for one in (run or {}).get("candidates", ())}
    chosen = held.get(str(body.get("picture") or ""))
    if chosen is None:
        raise PolyweaveError(
            "loop.unknown-sitting",
            "the page named a gate run or a picture this project has no record of",
            "overrule a picture the page lists under a gate",
            given=str(body.get("picture")),
            allowed=sorted(held),
        )
    name = Path(chosen["picture"]).stem
    member = {"name": name, "new": chosen["picture"], "passed": chosen["passed"]}
    return [member], f"gate:{run['id']}", name


def turntables(root) -> list[dict]:
    """Every turntable laid out in this project, newest last (§PW176)."""
    from .shape import TURNTABLES

    config = load(root)
    index = config.path("paths.work") / TURNTABLES
    found = []
    for listed in json.loads(read_text_retrying(index) or "[]"):
        text = read_text_retrying(config.root / listed)
        if text is not None:
            found.append({"manifest": listed, **json.loads(text)})
    return found


def answer(root, body: dict) -> dict:
    """The page's one write: a person's verdict on one family of one sitting.

    A refused picture promoted from a gate's lane is the same write: a verdict through
    `judge`, whose record says the tool refused what the person accepted, which is the
    evidence a tolerance is loosened from (§PW175).
    """
    config = load(root)
    if body.get("withdraw"):
        from . import style

        # Out of the canon by a person's click and sentence, and by nothing else.
        return {
            "withdrawn": style.withdraw(
                str(body["withdraw"]),
                family=body.get("canon") or None,
                why=str(body.get("why") or ""),
                root=config.root,
            )
        }
    if body.get("gate"):
        members, listed, family = _overruled(root, body)
        if body.get("canon"):
            # Into the canon the same way: a verdict accepting the look, whose record
            # the canon's own entry names (§PW177).
            members = [{**one, "canon": str(body["canon"])} for one in members]
        said = verdict.judge(
            members,
            str(body.get("choice") or ""),
            str(body.get("why") or ""),
            root=str(config.root),
        )
        said["answer"] = verdict.record_answer(
            said, sitting=listed, family=family, root=config.root
        )
        return said
    listed = str(body.get("sitting") or "")
    offered = {one["manifest"]: one for one in sittings(root)}
    if listed not in offered:
        raise PolyweaveError(
            "loop.unknown-sitting",
            f"{listed!r} is not a sitting this project laid out",
            "answer a sitting the page lists; verdict.sitting lays one out",
            given=listed,
            allowed=sorted(offered),
        )
    families = offered[listed]["families"]
    family = str(body.get("family") or "")
    if family not in families:
        raise PolyweaveError(
            "loop.unknown-sitting",
            f"the sitting has no family {family!r}",
            f"answer one of {', '.join(sorted(families))}",
            given=family,
            allowed=sorted(families),
        )
    members = families[family]["members"]
    # Checked before the verdict, so a mark that cannot be kept never leaves a verdict
    # recorded without the place it was about.
    shapes = _shapes(members, body.get("marks") or [])
    said = verdict.judge(
        members,
        str(body.get("choice") or ""),
        str(body.get("why") or ""),
        root=str(config.root),
        named=list(body.get("named") or ()),
    )
    marks = [_mark(member, drawn, config) for member, drawn in shapes]
    # An event on disk, so the agent that offered the sitting resumes on it without
    # the person saying so again in chat (§PW173).
    said["answer"] = verdict.record_answer(
        said, sitting=listed, family=family, root=config.root, marks=marks
    )
    return said


def _shapes(members: list[dict], marks: list) -> list[tuple[dict, list]]:
    """Each mark matched to the member it was drawn on, its shapes checked (§PW174)."""
    named = {m["name"]: m for m in members}
    found = []
    for mark in marks:
        member = named.get(str(mark.get("member")))
        if member is None:
            raise PolyweaveError(
                "loop.unknown-sitting",
                f"a mark names {mark.get('member')!r}, which is not in this family",
                f"mark one of {', '.join(sorted(named))}",
                given=str(mark.get("member")),
                allowed=sorted(named),
            )
        shapes = [
            s for s in mark.get("shapes") or [] if s.get("box") or s.get("outline")
        ]
        if shapes:
            found.append((member, shapes))
    return found


def _mark(member: dict, shapes: list, config) -> dict:
    """A person's mark as a mask the size of the picture it was drawn on.

    Black where they marked, white elsewhere, which is the edit call's own convention,
    kept with the digest of the picture, so it can never bound an edit of another.
    """
    from datetime import UTC, datetime

    from PIL import Image, ImageDraw

    from . import provenance

    here = config.root
    picture = here / member["new"]
    with Image.open(picture) as opened:
        size = opened.size
    mask = Image.new("L", size, 255)
    pen = ImageDraw.Draw(mask)
    for shape in shapes:
        if shape.get("box"):
            left, top, right, bottom = (float(v) for v in shape["box"])
            pen.rectangle(
                (
                    min(left, right),
                    min(top, bottom),
                    max(left, right),
                    max(top, bottom),
                ),
                fill=0,
            )
        else:
            pen.polygon(
                [tuple(float(v) for v in point) for point in shape["outline"]], fill=0
            )
    stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%S%f")
    target = config.path("paths.work") / "marks" / f"{stamp}-{member['name']}.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    mask.save(target)
    try:
        record = provenance.read(picture, root=here)
    except PolyweaveError:
        record = {}
    return {
        "member": member["name"],
        "picture": member["new"],
        "sha256": provenance.sha256_of(picture)[0],
        "mask": provenance.relative(target, here),
        "shapes": shapes,
        # For a render, the camera the mark was drawn from, so the region can be
        # traced back onto the surface rather than applied to pixels.
        "camera": record.get("camera"),
    }


def _served(here: Path, wanted: str) -> bool:
    """Whether a path is one the page may be sent: inside the project, a picture or a
    record."""
    target = (here / wanted).resolve()
    return (
        bool(wanted)
        and target.is_relative_to(here)
        and target.suffix.lower() in SERVED
        and target.is_file()
    )


def server(root=".", port: int = 0) -> ThreadingHTTPServer:
    """The page's server for one project, bound and not yet serving."""
    here = load(root).root

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):  # the terminal is the agent's, not a request log
            return

        def do_GET(self):  # noqa: N802 - the name the standard library calls
            asked = urlparse(self.path)
            if asked.path in ("/", "/index.html"):
                return self._file(PAGE / "index.html")
            if asked.path == "/page.js":
                return self._file(PAGE / "page.js")
            if asked.path == "/api/state":
                return self._json(
                    {
                        "pending": loop.pending(str(here)),
                        "sittings": sittings(here),
                        "answers": verdict.answers(root=str(here))["answers"],
                        "gates": looked_at(here),
                        "turntables": turntables(here),
                    }
                )
            if asked.path == "/api/canon":
                from . import style

                try:
                    families = load(here).styles() if load(here).states("style") else {}
                    return self._json([style.board(name, here) for name in families])
                except PolyweaveError as refused:
                    return self._json(refused.as_dict(), HTTPStatus.BAD_REQUEST)
            if asked.path == "/api/compare":
                query = parse_qs(asked.query)
                old, new = (query.get(k, [""])[0] for k in ("old", "new"))
                if all(_served(here, one) for one in (old, new)):
                    try:
                        return self._json(difference(here, old, new))
                    except PolyweaveError as refused:
                        return self._json(refused.as_dict(), HTTPStatus.BAD_REQUEST)
            if asked.path == "/file":
                wanted = (parse_qs(asked.query).get("path") or [""])[0]
                target = (here / wanted).resolve()
                if target.is_relative_to(here) and target.suffix.lower() in SERVED:
                    return self._file(target)
            return self._json({"code": "not-found"}, HTTPStatus.NOT_FOUND)

        def do_POST(self):  # noqa: N802
            # Read before answering, refusals included: a reply sent while the client
            # is still writing its body gets the connection reset under it.
            length = int(self.headers.get("Content-Length") or 0)
            sent = self.rfile.read(length) if length else b""
            if (
                urlparse(self.path).path != "/api/judge"
                or self.headers.get(ASKED) != "1"
            ):
                return self._json({"code": "refused"}, HTTPStatus.FORBIDDEN)
            try:
                body = json.loads(sent or b"{}")
                return self._json(answer(here, body))
            except PolyweaveError as refused:
                return self._json(refused.as_dict(), HTTPStatus.BAD_REQUEST)
            except json.JSONDecodeError:
                return self._json({"code": "not-json"}, HTTPStatus.BAD_REQUEST)

        def _file(self, path: Path):
            if not path.is_file():
                return self._json({"code": "not-found"}, HTTPStatus.NOT_FOUND)
            kind = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            self._send(path.read_bytes(), kind)

        def _json(self, value, status=HTTPStatus.OK):
            self._send(json.dumps(value).encode("utf-8"), "application/json", status)

        def _send(self, body: bytes, kind: str, status=HTTPStatus.OK):
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    return ThreadingHTTPServer((HOST, int(port)), Handler)


def run(root=".", port: int = 0) -> int:
    """Serve the page until interrupted, having said where it is."""
    serving = server(root, port)
    host, bound = serving.server_address[:2]
    print(f"polyweave review: http://{host}:{bound}/  (Ctrl+C stops it)", flush=True)
    try:
        serving.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serving.server_close()
    return 0
