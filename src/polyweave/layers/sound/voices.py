"""A narrator found in the service's shared library, and heard against others (§PW719).

viglet/marketing wanted a narrator of its audience's own age for one Short, and found
candidates with raw calls to `GET /v1/shared-voices`, then wrote one lines file per
candidate to hear the same sentence in each, because a lines file holds one voice.
`voice.find` searches the library and keeps the answer a day, as `stock.find` keeps a
search; `voice.compare` speaks one line in several voices, priced before it spends, and
lays the takes as one sitting a person picks from. Which voice narrates stays theirs.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
from typing import Annotated

from polyweave.kernel import provenance
from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation
from polyweave.kernel.errors import PolyweaveError
from polyweave.kernel.files import write_atomic
from polyweave.services import client, purchase
from polyweave.services.elevenlabs import FORMAT, SPEAK

#: Where the shared library is searched, under the service's base.
LIBRARY = "/v1/shared-voices"

#: How long a search is kept before it is asked again.
KEPT = 24 * 3600

#: What the library answers about a voice, kept as it spells it.
_SHOWN = ("voice_id", "public_owner_id", "name", "accent", "age", "gender",
          "use_case", "descriptive", "description", "language", "locale",
          "usage_character_count_1y", "cloned_by_count", "preview_url")


@operation("voice.find", kind="fetch")
def find(
    *,
    language: Annotated[str, Param("the language, as pt or en")] = None,
    locale: Annotated[str, Param("the accent's locale, as pt-BR")] = None,
    age: Annotated[str, Param("young, middle_aged or old")] = None,
    gender: Annotated[str, Param("male, female or neutral")] = None,
    use: Annotated[str, Param("what it is for, as narrative_story")] = None,
    words: Annotated[str, Param("words its name or description holds")] = None,
    count: Annotated[int, Param("how many, at most", lo=1, hi=100)] = 20,
    service: Annotated[str, Param("the [service] table it is asked through")] = None,
    root: Annotated[str, Param("the project the search is kept in")] = ".",
) -> dict:
    """Search the service's shared voice library, spending nothing (§PW719).

    Each match answers its `voice_id` with the name, accent, age, gender, use,
    description, language, how much it is used and its preview link. The answer is kept
    in the work area for a day and asked again only after. Speak one line in several
    with voice.compare before anything is chosen.
    """
    config = load(root)
    name = config.service(service, model="eleven_multilingual_v2")
    base, key = client.reached(name, config.services()[name])
    pairs = (("language", language), ("locale", locale), ("age", age),
             ("gender", gender), ("use_cases", use), ("search", words),
             ("page_size", count))
    asked = {k: v for k, v in pairs if v}
    kept = config.path("paths.work") / "voices" / (hashlib.sha256(json.dumps(
        sorted((k, str(v)) for k, v in asked.items())).encode()).hexdigest()[:20]
        + ".json")
    if kept.is_file() and time.time() - kept.stat().st_mtime < KEPT:
        found = json.loads(kept.read_text(encoding="utf-8"))
    else:
        answer = client.send(f"{base}{LIBRARY}?{urllib.parse.urlencode(asked)}",
                             headers={"xi-api-key": key, "Accept": "application/json"},
                             timeout=client.TIMEOUT)
        if answer.status >= 400:
            said = answer.body[:400].decode("utf-8", "replace")
            raise client.unpaid(answer.status, said) or PolyweaveError(
                "fetch.service-error", f"{name} answered {answer.status}",
                "read the detail; a 400 names a filter it does not take", detail=said)
        found = json.loads(answer.body or b"{}")
        kept.parent.mkdir(parents=True, exist_ok=True)
        write_atomic(kept, json.dumps(found))
    voices = [{k: one[k] for k in _SHOWN if one.get(k) not in (None, "")}
              for one in found.get("voices") or ()][:count]
    return {"voices": voices, "asked": asked,
            "says": f"{len(voices)} voice(s); hear one line in several with "
            "voice.compare text=<line> voices=<ids>"}


@operation("voice.compare", kind="fetch", injects=("report",), spends=True)
def compare(
    report=None,
    text: Annotated[str, Param("the line each voice speaks, word for word")] = None,
    *,
    voices: Annotated[list, Param("the service's voice ids, two or more")] = None,
    out: Annotated[str, Param("the folder the takes and the sitting go in")] = None,
    spend: Annotated[bool, Param("buy the takes; a priced plan otherwise")] = False,
    model: Annotated[str, Param("the service's model, priced in [service]")] = (
        "eleven_multilingual_v2"),
    service: Annotated[str, Param("the [service] table it is bought through")] = None,
    root: Annotated[str, Param("the project whose ledger this is")] = ".",
) -> dict:
    """Speak one line in several voices and lay the takes for a person to pick one
    (§PW719).

    Without `spend`, answers what each take and all of them cost and what is left, and
    buys nothing. With it, each voice speaks the line as sound.speak would, against the
    ceiling, landing as `<out>/<voice id>.mp3` with its record, and a sitting lays them
    as one choice: the person picks the narrator, never the agent.
    """
    from polyweave.layers.sound import sound
    from polyweave.layers.sound.sound_buy import _bought, _laid

    ids = [str(one).strip() for one in voices or () if str(one).strip()]
    if not text or not text.strip() or len(set(ids)) < 2:
        raise PolyweaveError(
            "fetch.missing-field", "a comparison needs a line and two voices or more",
            "pass text, the line, and voices, two or more voice ids voice.find "
            "answered", given="voices" if text else "text")
    ids = list(dict.fromkeys(ids))
    config = load(root)
    here = config.root
    name = config.service(service, model=model)
    prices = config.services()[name].get("prices") or {}
    each = client.priced(name, prices, model, None, len(text.strip()),
                         bought="spoken line")["price"]
    left = purchase.remaining(str(here), service=name)
    folder = _laid(config, out, "compare")
    plan = {"voices": ids, "characters": len(text.strip()), "each": each,
            "price": round(each * len(ids), 6), "left": left["left"],
            "unit": left["unit"], "spent": False}
    if not spend:
        return {**plan, "says": f"{len(ids)} takes at {each:g} {left['unit']} each; "
                "spend=true buys them and lays them for a person to pick one"}
    heard = []
    for voice in ids:
        took = _bought(
            report, f"{SPEAK.format(voice=urllib.parse.quote(voice, safe=''))}"
            f"?output_format={FORMAT}", {"text": text.strip(), "model_id": model},
            words=text.strip(), cue=None,
            out=provenance.relative(folder / f"{voice}.mp3", here), model=model,
            service=name, root=str(here),
            details={"voice": voice, "delivery": {}, "spoken": True,
                     "compared": ids})
        heard.append({"name": voice, "new": took["file"], "line": text.strip()})
    laid = sound.sitting(heard, out=provenance.relative(folder, here), root=str(here),
                         pick="voice")
    return {**plan, "spent": True, "takes": [one["new"] for one in heard],
            "sitting": laid["sitting"],
            "says": f"{len(heard)} takes of one line laid for a person to pick the "
            "voice; nothing is chosen for them"}
