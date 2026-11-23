"""A bought photo checked for the faults generated photos have (§PW696).

Every one of Shio's 24 bought photographs answered ok, and the owner found by eye an arm
fused into a therapist's hands and a chef with no thumb; ten more bought after had
uncountable hands and pseudo-lettering. `picture.gate` compares a silhouette, which no
such fault changes. `picture.faults` asks a vision model on this machine, never a paid
service, for the known faults of generated photos, keeps what it found on each
picture's record, and marks a bought one not usable in the ledger, with the prompt
advice that avoids the fault. What it finds is a model's reading, for a person to
confirm: it rejects nothing and buys nothing.
"""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import urlparse

from polyweave.kernel import provenance
from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError
from polyweave.services import client, purchase

#: The faults asked about, each with the advice that avoids it in the next prompt.
FAULTS = {
    "fused-limbs": "keep people apart; avoid hands touching another body",
    "malformed-hand": "frame hands out of the picture, or hold them still and apart",
    "missing-digit": "frame hands out of the picture",
    "extra-limb": "show one person at a time, whole",
    "extra-head": "show one person at a time, whole",
    "pseudo-text": "ask for no lettering, signs or labels",
    "merged-objects": "fewer objects, clear of each other and of the people",
}

#: What the model is asked, in words it answers as JSON.
ASKED = (
    "You inspect an AI-generated photograph for generation faults. Report only faults "
    "you can see. Kinds: " + ", ".join(FAULTS) + ". Answer JSON only, as "
    '{"faults": [{"kind": "<one kind>", "where": "<where in the frame>", '
    '"note": "<what is wrong>"}]}, with an empty list where there is none.'
)

#: Hosts a vision server may be on: this machine, so nothing is spent or sent away.
LOCAL = ("localhost", "127.0.0.1", "::1")


def _server(config) -> tuple[str, str]:
    url = str(config.get("vision.url") or "").rstrip("/")
    model = str(config.get("vision.model") or "")
    if urlparse(url).hostname not in LOCAL:
        raise PolyweaveError(
            "picture.vision-not-local",
            f"[vision] url is {url!r}, which is not this machine",
            "point [vision] url at a model served here, as http://localhost:11434; a "
            "paid service checking a picture is spending on the agent's judgement",
            given=url)
    if not model:
        raise PolyweaveError(
            "picture.no-vision",
            "[vision] names no model to ask",
            "pull one (ollama pull qwen2.5vl:7b) and set [vision] model = "
            '"qwen2.5vl:7b"')
    return url, model


def _asked(url: str, model: str, picture: bytes) -> list[dict]:
    """The faults the model reads off one picture, each kind one it was asked about."""
    body = json.dumps({"model": model, "prompt": ASKED, "stream": False,
                       "format": "json",
                       "images": [base64.b64encode(picture).decode()]}).encode()
    try:
        answer = client.send(f"{url}/api/generate", method="POST", data=body,
                             headers={"Content-Type": "application/json"},
                             timeout=600)
    except client.Unreached as exc:
        raise PolyweaveError(
            "picture.no-vision", f"no vision server answered at {url}",
            "start it (ollama serve) and pull the model [vision] names",
            detail=exc.reason) from exc
    if answer.status >= 400:
        raise PolyweaveError(
            "picture.no-vision", f"the vision server answered {answer.status}",
            "pull the model [vision] names, or name one it serves",
            detail=answer.body[:400].decode("utf-8", "replace"))
    try:
        said = json.loads(json.loads(answer.body)["response"])
    except (ValueError, KeyError, TypeError):
        said = {}
    return [{"kind": one["kind"], "where": str(one.get("where") or ""),
             "note": str(one.get("note") or "")}
            for one in (said.get("faults") or []) if isinstance(one, dict)
            and one.get("kind") in FAULTS]


@operation("picture.faults")
def faults(
    pictures: Annotated[list, Param("the pictures to check, under the project")],
    *,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """The faults generated photos have, read off each picture by a local model.

    Each picture is sent to `[vision] model` at `[vision] url`, which must be this
    machine, and answers the faults it reads (fused or malformed limbs, a missing
    digit, an extra limb or head, pseudo-text, objects merging), each with where in
    the frame and the prompt advice that avoids it. What is found is kept on the
    picture's record; a bought picture with a fault is marked `usable = false` in the
    ledger with the faults, and stays there. A model's reading is for a person to
    confirm: nothing is rejected, deleted or bought again.
    """
    config = load(root)
    here = config.root
    url, model = _server(config)
    checked = []
    for one in pictures:
        path = here / str(one)
        if not path.is_file():
            raise PolyweaveError("picture.no-vision", f"there is no picture at {one}",
                                 "name pictures under the project", given=str(one))
        found = _asked(url, model, path.read_bytes())
        named = provenance.relative(path, here)
        when = datetime.now(tz=UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        try:
            record = provenance.read(named, root=here)
            record["faults"] = {"model": model, "at": when, "found": found}
            provenance.write(record, here)
        except PolyweaveError:
            pass
        marked = purchase.unusable(named, found, root=here) if found else False
        checked.append({"picture": named, "faults": found, "usable": not found,
                        "ledger": marked,
                        "advice": sorted({FAULTS[f["kind"]] for f in found})})
    return {"model": model, "pictures": checked,
            "faulty": [one["picture"] for one in checked if one["faults"]]}
