"""A verdict only a person can give (§PW443).

"An agent accepting or rejecting its own look" is the non-goal this project is sharpest
about, and until this it was a convention: `verdict.judge` recorded whatever sentence it
was handed as the person's. So an accept now lands from one of two places, as the owner
chose on 2026-10-15, and from nothing else:

- **the review page**, which a person operates. Its write goes straight to the answer
  and never through an operation, so nothing here stands in its way;
- **a conversation**, where the person says the short code the page shows for the
  sitting, and the agent passes it as `code`. The page is the only thing that shows it.

The code is issued by the page's server when it shows a sitting, kept in that process's
memory, and written to the work area only as its SHA-256. So no file, and no operation's
answer (`review.state` included), carries a code an agent could read and repeat. A
desktop window that started its own server for a person says so in that process's
environment (`POLYWEAVE_PERSON`), which the agents it runs never inherit.

The check is a guard on the operation (`describe.operation(guard=)`), run by the MCP
server and the command line before the call, so it holds for any MCP client and needs no
hook. A Python caller in process is the plugin's own code and is not asked.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from pathlib import Path

from polyweave.kernel.errors import PolyweaveError

#: What a code is spelled from: no 0/O, no 1/I/L, so it survives being read aloud.
ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
LENGTH = 5

#: Where the digests are kept, under the work area.
DIGESTS = "person-codes.json"

#: The key the page's own lanes are answered under: the gate's refused pictures and the
#: canon, which belong to no sitting.
PAGE = "page"

#: The environment a person's own server runs in, set by the window that started it.
SURFACE = "POLYWEAVE_PERSON"

#: The choices that accept a look. A rejection sends a render back and accepts nothing.
ACCEPTS = ("accept", "number")


def _digest(code: str) -> str:
    return hashlib.sha256(str(code).strip().upper().encode("utf-8")).hexdigest()


def _where(root) -> Path:
    from polyweave.kernel.config import load

    return load(root).path("paths.work") / DIGESTS


def _kept(root) -> dict:
    from polyweave.kernel.files import read_text_retrying

    try:
        return json.loads(read_text_retrying(_where(root)) or "{}")
    except json.JSONDecodeError:
        return {}


def issue(root, key: str) -> str:
    """A new code for one sitting or the page's lanes, kept as a digest and returned.

    Only the page's server calls this, and only it holds what comes back.
    """
    from polyweave.kernel.files import write_atomic

    code = "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))
    kept = _kept(root)
    kept[key] = _digest(code)
    where = _where(root)
    where.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(where, json.dumps(kept, indent=1, sort_keys=True) + "\n")
    return code


def at_the_surface() -> bool:
    """Whether this process is a server a person's own window started for them."""
    return os.environ.get(SURFACE) == "window"


def require(root, keys: list[str], code: str, *, what: str,
            does: str = "accepts a look") -> None:
    """Refuse an accept unless `code` is the one the page shows for one of `keys`."""
    if at_the_surface():
        return
    kept = _kept(root)
    if code and any(kept.get(key) == _digest(code) for key in keys):
        return
    where = (
        "the code the review page shows for that sitting"
        if keys != [PAGE] else "the code the review page shows above its lanes"
    )
    raise PolyweaveError(
        "verdict.not-the-person",
        f"{what} {does}, and only a person can: no {where} came with it"
        if not code
        else f"{what} {does}, and {code!r} is not {where}",
        "ask the person to answer on the review page (python -m polyweave review), or "
        f"to say {where} and pass it as code",
        given=code or None,
    )


def sittings_holding(root, names: list[str]) -> list[str]:
    """The sittings that lay out every one of `names`, by manifest."""
    from .review import sittings

    wanted = set(names)
    found = []
    for one in sittings(root):
        laid = {
            member.get("name")
            for family in (one.get("families") or {}).values()
            for member in family.get("members") or ()
        }
        if wanted <= laid:
            found.append(one["manifest"])
    return found


def manifest_of(sitting: str) -> str:
    from .verdict import MANIFEST

    listed = str(sitting).replace("\\", "/").rstrip("/")
    return listed if listed.endswith(MANIFEST) else f"{listed}/{MANIFEST}"


# -- the guards, one per door ---------------------------------------------------------


def judging(args: dict) -> None:
    """verdict.judge: an accept needs the code of a sitting laying out its members."""
    if args.get("choice") not in ACCEPTS:
        return
    from .verdict import members_of

    root = args.get("root") or "."
    names = [member["name"] for member in members_of(args.get("members") or [])]
    require(root, sittings_holding(root, names), args.get("code") or "",
            what="verdict.judge")


def targeting(args: dict) -> None:
    """verdict.target always sets a person's bar: the code of a sitting laying out its
    members, whatever the target (§PW620)."""
    from .verdict import members_of

    root = args.get("root") or "."
    names = [member["name"] for member in members_of(args.get("members") or [])]
    require(root, sittings_holding(root, names), args.get("code") or "",
            what="verdict.target", does="sets the bar a look must reach")


def answering(args: dict) -> None:
    """verdict.answer: an accept needs the code of the sitting it names."""
    if args.get("choice") not in ACCEPTS:
        return
    require(args.get("root") or ".", [manifest_of(args.get("sitting") or "")],
            args.get("code") or "", what="verdict.answer")


def promoting(args: dict) -> None:
    """verdict.promote always accepts a picture a gate refused: the page's code."""
    require(args.get("root") or ".", [PAGE], args.get("code") or "",
            what="verdict.promote")


def page_answer(args: dict) -> None:
    """review.answer, called as an operation: the page's body, carrying its code."""
    body = args.get("body") or {}
    root = args.get("root") or "."
    if body.get("withdraw"):
        return
    if body.get("admit") or body.get("gate"):
        if body.get("admit") or body.get("choice") in ACCEPTS:
            require(root, [PAGE], body.get("code") or "", what="review.answer")
        return
    if body.get("choice") in ACCEPTS:
        require(root, [manifest_of(body.get("sitting") or "")], body.get("code") or "",
                what="review.answer")
