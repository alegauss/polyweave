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


def answer(root, body: dict) -> dict:
    """The page's one write: a person's verdict on one family of one sitting."""
    config = load(root)
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
                    }
                )
            if asked.path == "/file":
                wanted = (parse_qs(asked.query).get("path") or [""])[0]
                target = (here / wanted).resolve()
                if target.is_relative_to(here) and target.suffix.lower() in SERVED:
                    return self._file(target)
            return self._json({"code": "not-found"}, HTTPStatus.NOT_FOUND)

        def do_POST(self):  # noqa: N802
            if (
                urlparse(self.path).path != "/api/judge"
                or self.headers.get(ASKED) != "1"
            ):
                return self._json({"code": "refused"}, HTTPStatus.FORBIDDEN)
            length = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
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
