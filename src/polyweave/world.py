"""A game's world as a declaration beside its prose (§PW196).

Starship's `docs/design/world.md` is prose with a glossary table in it. A person reads
it well; a tool can only match strings against it, so nothing can say the world and the
game have drifted apart. The prose stays the source a person writes, and beside it a
`*.world.toml` declares what a check needs:

    [entity.ada]
    code = "ada"              # the name the game's scripts use; the id where unset
    name = "Captain Ada"      # the name a player reads
    kind = "character"        # place, faction, character, enemy or item
    faction = "crew"          # an entity whose kind is faction
    style = "portrait"        # the [style.<family>] its pictures are held to
    first = "act 1"           # where in the run it first appears

    [entity.ada.look]         # what a picture or mesh of it is bought from (§PW198)
    description = "a tall captain in a patched blue greatcoat"
    shows = ["a brass eyepiece"]
    never = ["a weapon"]

    [entity.ada.voice]        # what every line she speaks is spoken in (§PW321)
    id = "JBFqnCBsd6RMkjVDRZzb"   # the service's voice, chosen once by a person
    description = "dry and tired, in her fifties"
    stability = 0.5           # her delivery; a line may override it

    [rules]
    longest_line = 80         # the longest line a player reads, in characters
    silent = ["drone"]        # entities that never speak
    unshown = ["nemesis"]     # entities whose name is never shown
    tone = ["short and warm", "never a heroic speech"]   # what a person judges by

`world.read` returns the declaration or one entity of it, and refuses a file whose
shape is wrong. `world.validate` reports everything wrong with it, each finding against
the source's own line with the remedy. **Nothing here writes the file**: a person
authors the world, and the plugin reads it, for the reason the non-goal on a game's
story gives.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import tomllib
from pathlib import Path
from typing import Annotated

from . import provenance
from .config import load
from .describe import Param, operation
from .errors import PolyweaveError
from .files import read_text_retrying

#: What a world file's name ends in.
SUFFIX = ".world.toml"

#: What an entity may be.
KINDS = ("place", "faction", "character", "enemy", "item")

#: Every key an entity may carry, and whether it must.
ENTITY_KEYS = {
    "code": False,
    "name": True,
    # The name's plural where English does not make it by rule (§PW257).
    "plural": False,
    "kind": True,
    "faction": False,
    "style": False,
    "first": False,
    "look": False,
    # The voice every line of hers is spoken in (§PW321).
    "voice": False,
    # The name in another language, one table per locale (§PW329).
    "names": False,
}

#: What one locale's form of a name may say, and whether it must (§PW329): the name, its
#: plural where the language's rule does not make it, its grammatical gender, and for a
#: role a woman may hold, the feminine form and its plural.
NAME_KEYS = {
    "name": True,
    "plural": False,
    "gender": False,
    "feminine": False,
    "feminine_plural": False,
}

#: What a name's `gender` may be.
GENDERS = ("m", "f")

#: What an entity's `look` may say, and the type of each (§PW198).
LOOK_KEYS = {"description": str, "shows": list, "never": list}

#: What an entity's `voice` may say (§PW321): the service's voice id a person chose,
#: what it should sound like and a line to hear it on, and its delivery.
VOICE_KEYS = {"id": str, "description": str, "sample": str}

#: The delivery a voice may set, each as the range it takes.
DELIVERY = {
    "stability": (0.0, 1.0),
    "similarity": (0.0, 1.0),
    "style": (0.0, 1.0),
    "speed": (0.7, 1.2),
}

#: Every key `[rules]` may carry.
RULE_KEYS = ("longest_line", "silent", "unshown", "tone")

_WORLD = Param("the *.world.toml; needed only where the project holds several")
_ROOT = Param("the project the world belongs to")


def find(world: str | None = None, root: str | Path = ".") -> Path:
    """The world file: the one named, or the only one under the project."""
    here = Path(root)
    if world:
        where = Path(world) if Path(world).is_absolute() else here / world
        if not where.is_file():
            raise PolyweaveError(
                "world.none",
                f"there is no world file at {where}",
                f"name a {SUFFIX} under the project",
                given=str(world),
            )
        return where
    found = sorted(
        source
        for source in here.rglob(f"*{SUFFIX}")
        if not any(p.startswith(".") for p in source.relative_to(here).parts[:-1])
    )
    if not found:
        raise PolyweaveError(
            "world.none",
            f"the project at {here} holds no {SUFFIX}",
            f"write one beside the world's prose, such as docs/design/game{SUFFIX}",
        )
    if len(found) > 1:
        names = [provenance.relative(f, here) for f in found]
        raise PolyweaveError(
            "world.several",
            f"the project holds {len(found)} world files and the call named none",
            f"pass world: one of {', '.join(names)}",
            allowed=names,
        )
    return found[0]


def _line(lines: list[str], table: str, key: str | None = None) -> int | None:
    """The 1-based line a table's header, or a key inside it, is written on."""
    head, _, rest = table.partition(".")
    wanted = re.compile(
        rf"^\s*\[\s*{re.escape(head)}"
        + (rf'\s*\.\s*"?{re.escape(rest)}"?' if rest else "")
        + r"\s*\]"
    )
    inside = False
    for number, text in enumerate(lines, 1):
        if re.match(r"^\s*\[", text):
            if inside and key is not None:
                return None
            inside = bool(wanted.match(text))
            if inside and key is None:
                return number
        elif inside and re.match(rf'^\s*"?{re.escape(key or "")}"?\s*=', text):
            return number
    return None


class _Findings:
    """What is wrong with one world file, each against the line that says it."""

    def __init__(self, source: Path, lines: list[str]) -> None:
        self.source = source
        self.lines = lines
        self.found: list[tuple[PolyweaveError, int | None]] = []

    def add(self, error: PolyweaveError, table: str, key: str | None = None) -> None:
        tried = [(table, key), (table, None)]
        parent, _, last = table.rpartition(".")
        if parent:
            # A sub-table may be written inline, as `look = {...}` in its parent.
            tried += [(parent, last), (parent, None)]
        line = next(
            (n for t, k in tried if (n := _line(self.lines, t, k)) is not None), None
        )
        error.at = f"{self.source.name}:{line}" if line else self.source.name
        self.found.append((error, line))

    def as_list(self) -> list[dict]:
        return [{**e.as_dict(), "line": line} for e, line in self.found]


def _parse(source: Path) -> tuple[dict, dict, _Findings]:
    """The entities and rules as declared, and every fault in their shape."""
    text = read_text_retrying(source) or ""
    faults = _Findings(source, text.splitlines())
    try:
        declared = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise PolyweaveError(
            "world.malformed",
            f"{source.name} is not readable as TOML",
            "fix the syntax the detail points at",
            detail=str(exc),
        ) from exc
    for table in sorted(set(declared) - {"entity", "rules"}):
        faults.add(
            PolyweaveError(
                "world.unknown-key",
                f"{source.name} declares [{table}], which a world does not have",
                "declare entities as [entity.<id>] and rules under [rules]",
                given=table,
                allowed=["entity", "rules"],
            ),
            table,
        )
    entities: dict = {}
    for ident, own in (declared.get("entity") or {}).items():
        table = f"entity.{ident}"
        if not isinstance(own, dict):
            faults.add(
                PolyweaveError(
                    "world.bad-value",
                    f"entity.{ident} is a value, and an entity is a table",
                    f"write it as [entity.{ident}] with name and kind under it",
                ),
                "entity",
                ident,
            )
            continue
        for key in sorted(set(own) - set(ENTITY_KEYS)):
            faults.add(
                PolyweaveError(
                    "world.unknown-key",
                    f"[{table}] declares {key}, which an entity does not have",
                    f"use one of {', '.join(ENTITY_KEYS)}",
                    given=key,
                    allowed=list(ENTITY_KEYS),
                ),
                table,
                key,
            )
        for key in (k for k, needed in ENTITY_KEYS.items() if needed and k not in own):
            faults.add(
                PolyweaveError(
                    "world.missing-field",
                    f"[{table}] has no {key}",
                    f"write {key} under [{table}]",
                ),
                table,
            )
        tables = ("look", "names", "voice")
        for key in (k for k in ENTITY_KEYS if k in own and k not in tables):
            if not isinstance(own[key], str) or not own[key].strip():
                faults.add(
                    PolyweaveError(
                        "world.bad-value",
                        f"[{table}] {key} is {own[key]!r}, and it is a non-empty text",
                        f'write it in quotes, such as {key} = "..."',
                    ),
                    table,
                    key,
                )
        if isinstance(own.get("kind"), str) and own["kind"] not in KINDS:
            faults.add(
                PolyweaveError(
                    "world.bad-kind",
                    f"[{table}] is a {own['kind']!r}, which is not a kind",
                    f"make it one of {', '.join(KINDS)}",
                    given=own["kind"],
                    allowed=KINDS,
                ),
                table,
                "kind",
            )
        if "look" in own:
            _look(own["look"], table, faults)
        if "names" in own:
            _names(own["names"], table, faults)
        if "voice" in own:
            _voice(own["voice"], table, faults)
        entities[ident] = {"id": ident, "code": ident, **own}
    rules = declared.get("rules") or {}
    if not isinstance(rules, dict):
        rules = {}
    for key in sorted(set(rules) - set(RULE_KEYS)):
        faults.add(
            PolyweaveError(
                "world.unknown-key",
                f"[rules] declares {key}, which is not a rule",
                f"use one of {', '.join(RULE_KEYS)}",
                given=key,
                allowed=RULE_KEYS,
            ),
            "rules",
            key,
        )
    longest = rules.get("longest_line")
    if longest is not None and (
        isinstance(longest, bool) or not isinstance(longest, int) or longest < 1
    ):
        faults.add(
            PolyweaveError(
                "world.bad-value",
                f"[rules] longest_line is {longest!r}, and it is a count of characters",
                "write a whole number above zero, such as longest_line = 80",
            ),
            "rules",
            "longest_line",
        )
    for key in ("silent", "unshown"):
        named = rules.get(key)
        if named is not None and (
            not isinstance(named, list) or not all(isinstance(n, str) for n in named)
        ):
            faults.add(
                PolyweaveError(
                    "world.bad-value",
                    f"[rules] {key} is {named!r}, and it is a list of entity ids",
                    f'write it as {key} = ["<id>", ...]',
                ),
                "rules",
                key,
            )
    tone = rules.get("tone")
    if tone is not None and not _shaped(tone, list):
        faults.add(
            PolyweaveError(
                "world.bad-value",
                f"[rules] tone is {tone!r}, and it is a list of sentences",
                'write it as tone = ["short and warm", "never a heroic speech"]',
            ),
            "rules",
            "tone",
        )
    return entities, rules, faults


def _look(look, table: str, faults: _Findings) -> None:
    """An entity's look: a table of a description and two lists of traits."""
    where = f"{table}.look"
    if not isinstance(look, dict):
        faults.add(
            PolyweaveError(
                "world.bad-value",
                f"[{table}] look is {look!r}, and a look is a table",
                f"write it as [{where}] with description, shows and never under it",
            ),
            where,
        )
        return
    for key in sorted(set(look) - set(LOOK_KEYS)):
        faults.add(
            PolyweaveError(
                "world.unknown-key",
                f"[{where}] declares {key}, which a look does not have",
                f"use one of {', '.join(LOOK_KEYS)}",
                given=key,
                allowed=list(LOOK_KEYS),
            ),
            where,
            key,
        )
    for key, kind in LOOK_KEYS.items():
        value = look.get(key)
        if value is None or _shaped(value, kind):
            continue
        faults.add(
            PolyweaveError(
                "world.bad-value",
                f"[{where}] {key} is {value!r}, and it is "
                + ("a non-empty text" if kind is str else "a list of texts"),
                f'write it as {key} = "..."'
                if kind is str
                else f'write it as {key} = ["...", "..."]',
            ),
            where,
            key,
        )


def _voice(voice, table: str, faults: _Findings) -> None:
    """An entity's voice: the service's id, words about it, and its delivery."""
    where = f"{table}.voice"
    if not isinstance(voice, dict):
        faults.add(
            PolyweaveError(
                "world.bad-value",
                f"[{table}] voice is {voice!r}, and a voice is a table",
                f'write it as [{where}] with id = "..." under it',
            ),
            where,
        )
        return
    known = [*VOICE_KEYS, *DELIVERY]
    for key in sorted(set(voice) - set(known)):
        faults.add(
            PolyweaveError(
                "world.unknown-key",
                f"[{where}] declares {key}, which a voice does not have",
                f"use one of {', '.join(known)}",
                given=key,
                allowed=known,
            ),
            where,
            key,
        )
    for key in (k for k in VOICE_KEYS if k in voice):
        if not _shaped(voice[key], str):
            faults.add(
                PolyweaveError(
                    "world.bad-value",
                    f"[{where}] {key} is {voice[key]!r}, and it is a non-empty text",
                    f'write it in quotes, such as {key} = "..."',
                ),
                where,
                key,
            )
    for key, (low, high) in DELIVERY.items():
        value = voice.get(key)
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int | float) or not (
            low <= value <= high
        ):
            faults.add(
                PolyweaveError(
                    "world.bad-value",
                    f"[{where}] {key} is {value!r}, and it is a number from {low:g} "
                    f"to {high:g}",
                    f"write {key} = <{low:g} to {high:g}>, or leave it out for the "
                    "voice's own",
                ),
                where,
                key,
            )


def _names(names, table: str, faults: _Findings) -> None:
    """An entity's names in other languages, a table of locales (§PW329)."""
    where = f"{table}.names"
    if not isinstance(names, dict):
        faults.add(
            PolyweaveError(
                "world.bad-value",
                f"[{table}] names is {names!r}, and it is a table of locales",
                f'write it as [{where}.pt_BR] with name = "..." under it',
            ),
            where,
        )
        return
    for locale, form in names.items():
        at = f"{where}.{locale}"
        if not isinstance(form, dict):
            faults.add(
                PolyweaveError(
                    "world.bad-value",
                    f"[{where}] {locale} is {form!r}, and a locale's form is a table",
                    f'write it as [{at}] with name = "..." under it',
                ),
                where,
                locale,
            )
            continue
        for key in sorted(set(form) - set(NAME_KEYS)):
            faults.add(
                PolyweaveError(
                    "world.unknown-key",
                    f"[{at}] declares {key}, which a name's form does not have",
                    f"use one of {', '.join(NAME_KEYS)}",
                    given=key,
                    allowed=list(NAME_KEYS),
                ),
                at,
                key,
            )
        if "name" not in form:
            faults.add(
                PolyweaveError(
                    "world.missing-field",
                    f"[{at}] has no name",
                    f'write name = "..." under [{at}]',
                ),
                at,
            )
        for key in (k for k in NAME_KEYS if k in form and k != "gender"):
            if not _shaped(form[key], str):
                faults.add(
                    PolyweaveError(
                        "world.bad-value",
                        f"[{at}] {key} is {form[key]!r}, and it is a non-empty text",
                        f'write it in quotes, such as {key} = "..."',
                    ),
                    at,
                    key,
                )
        if "gender" in form and form["gender"] not in GENDERS:
            faults.add(
                PolyweaveError(
                    "world.bad-value",
                    f"[{at}] gender is {form['gender']!r}, and it is one of "
                    + ", ".join(GENDERS),
                    'write gender = "m" or gender = "f"',
                    given=str(form["gender"]),
                    allowed=GENDERS,
                ),
                at,
                "gender",
            )


def _shaped(value, kind: type) -> bool:
    if kind is str:
        return isinstance(value, str) and bool(value.strip())
    return isinstance(value, list) and all(
        isinstance(v, str) and v.strip() for v in value
    )


def look_digest(entity: dict) -> str:
    """What a bought picture or mesh of an entity was drawn from, as one hash.

    The name, kind, style and look: what a prompt is composed of, and nothing else, so
    an edit elsewhere in the world, or to this entity's faction, does not call it stale.
    """
    drawn = {k: entity.get(k) for k in ("name", "kind", "style", "look")}
    text = json.dumps(drawn, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def voice_digest(entity: dict) -> str:
    """What a spoken line of an entity was spoken in, as one hash (§PW321).

    The voice table alone: an edit to the entity's look does not call its lines stale,
    and a new voice or delivery does.
    """
    text = json.dumps(entity.get("voice") or {}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def still_drawn(world: str | Path, ident: str, digest: str, of: str = "look") -> bool:
    """Whether the world file still describes this entity as the digest recorded it.

    `of` is what was drawn from it: its look, or for a spoken line its voice. A world
    that no longer parses, or no longer holds the entity, does not.
    """
    try:
        entities, _, faults = _parse(Path(world))
    except PolyweaveError:
        return False
    if faults.found or ident not in entities:
        return False
    digested = voice_digest if of == "voice" else look_digest
    return digested(entities[ident]) == digest


def voiced(
    entity: str, world: str | None = None, root: str | Path = "."
) -> tuple[dict, dict]:
    """What a line of an entity is spoken in, and the record of where it came from.

    Refused where the entity has no voice id, rather than spoken in some other voice:
    a character is known by the voice of every line (§PW321).
    """
    source, found = brief(entity, world, root)
    voice = found.get("voice") or {}
    if not voice.get("id"):
        raise PolyweaveError(
            "world.no-voice",
            f"{entity} has no voice in the world"
            + (", only words about one" if voice.get("description") else ""),
            f'have a person choose one and write it as [entity.{entity}.voice] '
            'id = "<the service\'s voice id>"',
            given=entity,
        )
    record = {
        "id": entity,
        "world": provenance.relative(source, Path(root).resolve()),
        "sha256": voice_digest(found),
        "of": "voice",
    }
    return record, voice


def brief(
    entity: str, world: str | None = None, root: str | Path = "."
) -> tuple[Path, dict]:
    """One entity a purchase is made from, refused where the world lacks it."""
    source, entities, _ = declared(world, root)
    if entity not in entities:
        near = difflib.get_close_matches(entity, entities, n=1)
        raise PolyweaveError(
            "world.unknown-entity",
            f"the world declares no entity {entity!r} to buy a picture, mesh or "
            "line of",
            f"did you mean {near[0]!r}?"
            if near
            else f"name one it declares, or write [entity.{entity}] in the world",
            given=entity,
            allowed=list(entities),
        )
    return source, entities[entity]


def described(entity: dict, detail: str | None = None) -> str:
    """An entity's look as one description: the world's words first, then the call's.

    The world's traits close it, so where the call's detail disagrees with them the
    last word a service reads is the world's.
    """
    look = entity.get("look") or {}
    said = [str(look.get("description") or entity["name"]).rstrip(". ")]
    if detail:
        said.append(str(detail).strip().rstrip("."))
    if look.get("shows"):
        said.append("It shows " + ", ".join(look["shows"]))
    if look.get("never"):
        said.append("It never shows " + ", ".join(look["never"]))
    return ". ".join(said) + "."


def declared(
    world: str | None = None, root: str | Path = "."
) -> tuple[Path, dict, dict]:
    """The world file, its entities and its rules, refused where its shape is wrong."""
    source = find(world, root)
    entities, rules, faults = _parse(source)
    if faults.found:
        raise faults.found[0][0]
    return source, entities, rules


@operation("world.read")
def read(
    entity: Annotated[str, Param("one entity's id; every entity where unset")] = None,
    world: Annotated[str, _WORLD] = None,
    root: Annotated[str, _ROOT] = ".",
) -> dict:
    """The world's entities and rules as the project declares them, or one entity.

    One entity comes with `lines`: what a person approved of its speech (§PW199), the
    examples a new line for it starts from.
    """
    source, entities, rules = declared(world, root)
    here = provenance.relative(source, Path(root))
    if entity is None:
        return {"world": here, "entities": entities, "rules": rules}
    if entity not in entities:
        near = difflib.get_close_matches(entity, entities, n=1)
        raise PolyweaveError(
            "world.unknown-entity",
            f"{here} declares no entity {entity!r}",
            f"did you mean {near[0]!r}?"
            if near
            else f"name one it declares, or write [entity.{entity}] in {here}",
            given=entity,
            allowed=list(entities),
        )
    from .words import approved

    return {"world": here, "entity": entities[entity], "lines": approved(entity, root)}


@operation("world.validate")
def validate(
    world: Annotated[str, _WORLD] = None,
    root: Annotated[str, _ROOT] = ".",
) -> dict:
    """Everything wrong with the world file, each finding on its own line with a remedy.

    A name two entities share, a faction nobody declared, a style family the project's
    polyweave.toml lacks and a rule naming an entity that does not exist, beside every
    fault in the file's shape.
    """
    source = find(world, root)
    entities, rules, faults = _parse(source)
    _duplicates(entities, faults)
    _factions(entities, faults)
    _families(entities, faults, root)
    for key in ("silent", "unshown"):
        named = rules.get(key)
        if not isinstance(named, list):
            continue
        for ident in named:
            if isinstance(ident, str) and ident not in entities:
                near = difflib.get_close_matches(ident, entities, n=1)
                faults.add(
                    PolyweaveError(
                        "world.unknown-entity",
                        f"[rules] {key} names {ident!r}, which no entity is",
                        f"did you mean {near[0]!r}?"
                        if near
                        else f"declare [entity.{ident}], or take it out of {key}",
                        given=ident,
                        allowed=list(entities),
                    ),
                    "rules",
                    key,
                )
    findings = faults.as_list()
    return {
        "world": provenance.relative(source, Path(root)),
        "valid": not findings,
        "entities": len(entities),
        "findings": findings,
    }


def _duplicates(entities: dict, faults: _Findings) -> None:
    """Two entities a player, or a script, could not tell apart."""
    for key, who in (("name", "a player reads"), ("code", "the scripts use")):
        seen: dict[str, str] = {}
        for ident, own in entities.items():
            value = own.get(key)
            if not isinstance(value, str):
                continue
            folded = value.strip().casefold()
            if folded in seen:
                faults.add(
                    PolyweaveError(
                        "world.duplicate-name",
                        f"[entity.{ident}] and [entity.{seen[folded]}] share the "
                        f"{key} {value!r}, which {who}",
                        f"give one of them another {key}",
                    ),
                    f"entity.{ident}",
                    key,
                )
            else:
                seen[folded] = ident


def _factions(entities: dict, faults: _Findings) -> None:
    factions = sorted(i for i, e in entities.items() if e.get("kind") == "faction")
    for ident, own in entities.items():
        named = own.get("faction")
        if not isinstance(named, str) or named in factions:
            continue
        other = entities.get(named)
        near = difflib.get_close_matches(named, factions, n=1)
        faults.add(
            PolyweaveError(
                "world.unknown-faction",
                f"[entity.{ident}] belongs to {named!r}, which is a "
                f"{other.get('kind')}, not a faction"
                if other
                else f"[entity.{ident}] belongs to {named!r}, which no entity declares",
                f"did you mean {near[0]!r}?"
                if near
                else f'declare [entity.{named}] with kind = "faction"',
                given=named,
                allowed=factions,
            ),
            f"entity.{ident}",
            "faction",
        )


def _families(entities: dict, faults: _Findings, root: str | Path) -> None:
    config = load(root)
    families = sorted(config.styles()) if config.states("style") else []
    for ident, own in entities.items():
        family = own.get("style")
        if not isinstance(family, str) or family in families:
            continue
        near = difflib.get_close_matches(family, families, n=1)
        faults.add(
            PolyweaveError(
                "world.unknown-family",
                f"[entity.{ident}] is held to the {family!r} style, which "
                "polyweave.toml does not declare",
                f"did you mean {near[0]!r}?"
                if near
                else f"declare [style.{family}] in polyweave.toml",
                given=family,
                allowed=families,
            ),
            f"entity.{ident}",
            "style",
        )
