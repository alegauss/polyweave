"""What a project declares, and how a value is resolved.

`docs/specs/project-config.md` is the contract. `polyweave.toml` at the project root,
and the plugin ships a default for all of it — **a default that cannot be overridden is
a defect**, and so is a value that can only be set by editing the plugin.

Resolution is explicit argument, then `polyweave.toml`, then the default, evaluated on
every call. The file is therefore read on every `load` rather than held from startup, so
correcting it does not need a session restart. It is a few hundred bytes of TOML; the
read is cheaper than the round trip it saves.

The evidence is §PW5: Cottony's art tools resolve their own repository root from their
own file path and import a palette module that lives beside them, so nothing in them
runs from another repository.
"""

from __future__ import annotations

import difflib
import functools
import importlib
import os
import re
import tomllib
from dataclasses import dataclass, fields
from datetime import date
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from .errors import PolyweaveError

FILENAME = "polyweave.toml"

#: `${NAME}`, an environment variable named in the file and resolved per call — which is
#: how a machine-specific path stays out of a file a colleague also reads.
_ENV_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

#: Tables whose keys a project names itself, so an unknown key in them is not a typo.
#: `render.samples` is keyed by the rung names `render.rungs` declares.
#: `extend.measures` and `extend.operations` are keyed by the project's own measures and
#: operations, each checked where it is read (§PW517, §PW518).
_KERNEL_OPEN: tuple[str, ...] = ("extend.measures", "extend.operations")

#: Tables a project may add keys to while keeping the ones declared here. `[capture]`
#: is one because the settings a picture depends on are per project and short, and a
#: project that cannot name its own has to leave them to the machine (§PW25).
#: `[licence]` is keyed by the file names of the libraries a render plays (§PW191).
_KERNEL_FREE: tuple[str, ...] = ()

#: Only a binary may sit outside the tree. Everything else resolves under
#: `project.root`, because a path elsewhere is state a colleague cannot reproduce.
#: A render's engines and instrument libraries are installed per machine, like Blender.
_BINARIES = (
    "paths.blender",
    "paths.godot",
    "paths.tesseract",
    "paths.fluidsynth",
    "paths.soundfont",
    "paths.surge",
)

#: Settings that name a file inside the tree although they do not live under `[paths]`.
_INSIDE = ("service.schema",)

#: Tables that hold either one paid service or several named ones (§PW162). A bare
#: `[service]` is the one service it always was; `[service.meshy]` beside
#: `[service.ideogram]` is two, each with its own `[budget.<name>]`.
_KERNEL_NAMED = ("service", "budget")

#: What a bare `[style]` is called: a project with one look has one family (§PW166).
DEFAULT_FAMILY = "default"

#: What the bare `[service]` is called wherever a service has to be named: in the
#: ledger, in `remaining`, in `capabilities`.
DEFAULT_SERVICE = "default"

#: What one named ceiling takes. `credits` is the bare table's word and not this one's:
#: a named ceiling always says its unit, because two services never share one.
_NAMED_BUDGET = {"amount": 0, "unit": "credits", "expires": ""}

#: Every key, with the value used where the project declares none. The shape is the
#: schema: a key absent from here is refused rather than ignored.
KERNEL_DEFAULTS: dict[str, Any] = {
    # The layers this project uses (§PW509); empty is every one, so a project
    # that never says is served the whole surface.
    "layers": {"on": []},
    # What a project adds to polyweave's own vocabulary: a measure only its game needs,
    # declared and run apart, as `x.<project>.<name>` (§PW517).
    "extend": {"measures": {}, "operations": {}},
    "project": {
        "name": "",  # the root directory's name, filled in on load
        "root": ".",
        # Whether the game is sold: game.release_check then refuses a part a service's
        # plan licensed for non-commercial use only (§PW448).
        "sells": False,
    },
    "paths": {
        "blender": "blender",  # found on PATH unless the project says where
        "godot": "godot",
        # What reads lettering back off a picture (§PW169). Optional: without it a
        # picture's declared text is reported unchecked, never passed.
        "tesseract": "tesseract",
        "meshes": "assets/3d",
        # Prepared references, committed with the tree: the input that actually made a
        # mesh is the one on file, not whichever original a person had open (§PW21).
        "references": "assets/references",
        "renders": "docs/renders",
        "specs": "docs/accept",
        "work": ".polyweave",
        # The ledger of what was paid for. Inside the tree and committed with it: a
        # purchase and its record are one artefact (§PW17).
        "purchases": "polyweave.purchases.json",
        # What one asset cost, made each way. Committed with the tree, because a
        # baseline that can be rewritten is not a baseline (§PW35).
        "loop": "polyweave.loop.json",
        # Where a game's audio lands (§PW185). One folder by default, because Cottony
        # keeps its music and its effects side by side; a family may name its own.
        "audio": "assets/audio",
        # Where vfx.build writes its scenes where a call names no out (§PW374). Empty
        # is beside each declaration, which is refused where the export leaves the
        # declaration out: a scene the shipped game cannot load passes every editor
        # check.
        "vfx": "",
        # What a score renders through (§PW187). Engines and instrument libraries are
        # configuration and never bundled: FluidSynth plays a General MIDI SoundFont,
        # and Surge XT is a VST3, found in the usual plug-in folders where it is empty.
        "fluidsynth": "fluidsynth",
        "soundfont": "",
        "surge": "",
    },
    "tolerance": {
        "alpha_floor": 0.02,
        # Keyed by rung, because the noise floor is not one number: two seeds of one
        # unchanged sphere measured 0.0234 apart at the sphere rung, 0.0195 at preview
        # and 0.0122 at final on Blender 5.2.1, against the 0.004 that used to be the
        # single default — so every preview comparison read as a change (§PW44). These
        # are what one machine measured, which is still a guess about another: a floor
        # measured from a twin render beats all of them, and `measure.same` takes one.
        "render_noise": {"sphere": 0.025, "preview": 0.020, "final": 0.013},
        "silhouette_iou": 0.97,
        "delta_e": 2.0,
        # How far from the colour at the frame's edge still counts as background when a
        # photograph is cut out. Perceptual, so it is the same number on any hue.
        "background_delta_e": 12.0,
        # The least of the frame a subject may fill and still be worth spending on.
        "subject_coverage": 0.12,
        # How far a rendered subject must reach across the frame along its longer axis
        # to be worth judging at all (§PW52). **Extent, not area**, and that is the
        # whole of why there is a second key rather than a reuse of the one above: a
        # rope framed exactly right covers 1.6% of the frame, so any area floor that
        # catches a two-pixel render refuses the rope too. Measured through the project
        # rig on the two real meshes the suite has — the booster hammer spans 0.578 and
        # the plush body 0.539 — against 0.016 for two stray pixels. 0.05 sits an order
        # of magnitude clear of both, which is the margin a number nobody can re-measure
        # on their own assets needs.
        "subject_extent": 0.05,
    },
    "cache": {"max_bytes": 8_000_000_000},
    "provenance": {
        # Files under a produced directory that a person made rather than the plugin, as
        # glob patterns relative to the root. §PW41: checking that every produced file
        # carries a record is only useful if a project can say which of them are not
        # produced — a report nobody can quieten is a report nobody reads, and this one
        # has to stay worth reading for the one week in a year when a mesh goes missing.
        "handmade": [],
    },
    "adoption": {
        # The project's own files that do what a polyweave call does, kept on purpose,
        # each with the reason (§PW59): `"tools/art/make_assets.py" = "drawn 2D art"`.
        # project.adoption reports them and project.check fails on the rest.
        "own": {},
    },
    "review": {
        # The language a sitting and the review page are read in (§PW287): en, pt-BR.
        "language": "en",
    },
    "service": {
        "base": "",  # naming no service is how a project that buys nothing says so
        "key_env": "",
        # What the service was proved to accept, learned by probing (§PW19).
        "schema": "polyweave.service.toml",
        # A price per output, keyed `<model>:<speed>` or `<model>`, for a service with
        # no balance to read: what it charges is then quoted, and says so (§PW164).
        "prices": {},
        # Whether the service's edit and reframe leave what they were asked to keep
        # untouched, pixel for pixel (§PW209). Ideogram's redraw the whole picture, so
        # a variation is held to its parent pixel for pixel only where this is stated.
        "preserves": False,
        # The plan the key belongs to, where the service does not say it (§PW448):
        # "free" licenses for non-commercial use only, any other name commercially, and
        # empty is unstated. Every bought file's record keeps it.
        "plan": "",
    },
    "budget": {
        # No budget is no spend, never an unlimited one: the absence of a ceiling is
        # not read as permission.
        # A ceiling in another unit is a named one, `[budget.<name>]` (§PW162).
        "credits": 0,
        "expires": "",
    },
}


@dataclass(frozen=True)
class Schema:
    """Every table polyweave.toml may hold: the kernel's and each layer's (§PW508)."""

    tables: dict[str, Any]
    free: tuple[str, ...]
    open: tuple[str, ...]
    named: tuple[str, ...]
    settings: tuple[str, ...]
    choices: dict[str, tuple[str, ...]]
    #: The layer that declares each table; a kernel table is absent.
    owner: dict[str, str]


@functools.cache
def _schema() -> Schema:
    """The kernel's tables and each layer's, read on first use: the layers are found
    by a walk that imports this module's own refusals. A table, a choice or a setting
    two layers declare is refused, naming both."""
    from .layer import layers

    tables, owner = dict(KERNEL_DEFAULTS), {}
    free, opened = list(_KERNEL_FREE), list(_KERNEL_OPEN)
    named, settings = list(_KERNEL_NAMED), list(_KERNEL_SETTINGS)
    choices = dict(_KERNEL_CHOICES)
    for name, declared in layers().items():
        if not declared.config:
            continue
        module = importlib.import_module(declared.config)
        for table, keys in module.TABLES.items():
            if table in tables:
                raise PolyweaveError(
                    "layer.declared-twice",
                    f"layer {name} declares the table [{table}], which "
                    f"{owner.get(table, 'the kernel')} already does",
                    "keep the table in the layer that owns it and drop it elsewhere",
                    given=table,
                )
            tables[table], owner[table] = keys, name
        for key, words in getattr(module, "CHOICES", {}).items():
            if key in choices:
                raise PolyweaveError(
                    "layer.declared-twice",
                    f"layer {name} declares the choice {key!r}, which is declared",
                    "give the setting a name of its own",
                    given=key,
                )
            choices[key] = tuple(words)
        free += getattr(module, "FREE", ())
        opened += getattr(module, "OPEN", ())
        named += getattr(module, "NAMED", ())
        settings += getattr(module, "SETTINGS", ())
    return Schema(tables, tuple(free), tuple(opened), tuple(named), tuple(settings),
                  choices, owner)


def __getattr__(name: str):
    # `DEFAULTS` and `_FREE_TABLES` read as they always did, as the union (§PW508).
    if name == "DEFAULTS":
        return _schema().tables
    if name == "_FREE_TABLES":
        return _schema().free
    raise AttributeError(name)


@dataclass(frozen=True)
class Tolerances:
    """The numbers that decide what counts as the same, resolved once.

    §PW40: `[tolerance] alpha_floor` was 0.02 in this file's defaults and 0.0 in the
    signature of every function that used it, and the two disagreed. An operation that
    resolved the setting measured the subject the project asked for; one that forgot
    measured every pixel in the frame, background included, and nothing reported that a
    choice had been made.

    The fix is that a tolerance has one home, and this is it. The library functions stay
    pure — they take numbers, read no files, and so can run inside Blender — and none of
    them invents a fallback any more. Resolving happens at the operation, once, and this
    is what it resolves to: all six together, so an operation that needs one cannot pick
    up a stale sibling, and so a provenance record can carry the values actually in
    force rather than whatever the file holds when it is read back.
    """

    alpha_floor: float
    render_noise: float
    silhouette_iou: float
    delta_e: float
    background_delta_e: float
    subject_coverage: float
    subject_extent: float

    def as_dict(self) -> dict[str, float]:
        """What was in force, for the record written beside the artefact."""
        return {f.name: getattr(self, f.name) for f in fields(self)}


class Config:
    """One project's settings, resolved against the plugin's defaults."""

    def __init__(self, root: Path, declared: dict[str, Any], source: Path | None):
        self.root = root
        self.source = source
        self._declared = declared
        self._merged = _merge(_schema().tables, declared)
        if not self._merged["project"]["name"]:
            self._merged["project"]["name"] = root.name

    # -- reading ----------------------------------------------------------------

    def get(self, address: str, explicit: Any = None) -> Any:
        """Resolve one value: the explicit argument, then the file, then the default."""
        if explicit is not None:
            return explicit
        table, _, key = address.partition(".")
        if not key or table not in _schema().tables:
            raise PolyweaveError(
                "config.unknown-address",
                f"{address!r} is not a setting",
                f"name one of {', '.join(self.addresses()[:6])}, and so on",
                given=address,
                allowed=self.addresses(),
            )
        value = self._merged
        for part in address.split("."):
            if not isinstance(value, dict) or part not in value:
                raise PolyweaveError(
                    "config.unknown-address",
                    f"{address!r} is not a setting",
                    f"read {table} to see what it holds",
                    given=address,
                    allowed=self.addresses(),
                )
            value = value[part]
        return _expand(value, address)

    def path(self, address: str, explicit: str | Path | None = None) -> Path:
        """Resolve a path setting to somewhere inside the tree, absolute.

        Only a binary may be absolute. Everything else is refused where it points out of
        the project, because nothing is written outside it and nothing read from outside
        it is reproducible.
        """
        raw = self.get(address, str(explicit) if explicit is not None else None)
        candidate = Path(str(raw)).expanduser()
        if address in _BINARIES:
            return candidate
        # Absolute on either kind of desk: the file is shared, and `C:/art` read on
        # Linux would otherwise be a folder named `C:` inside the project.
        if candidate.is_absolute() or any(
            kind(str(raw)).is_absolute() for kind in (PurePosixPath, PureWindowsPath)
        ):
            raise PolyweaveError(
                "config.path-outside",
                f"{address} is {candidate}, which is not inside {self.root}",
                f"write it relative to the project root; only "
                f"{' and '.join(_BINARIES)} may be absolute",
            )
        resolved = (self.root / candidate).resolve()
        if not resolved.is_relative_to(self.root):
            raise PolyweaveError(
                "config.path-outside",
                f"{address} climbs out of {self.root} to {resolved}",
                "write a path that stays inside the project",
            )
        return resolved

    def table(self, name: str) -> dict:
        """One whole table, with every value resolved."""
        if name not in _schema().tables:
            raise PolyweaveError(
                "config.unknown-address",
                f"there is no [{name}] table",
                f"name one of {', '.join(sorted(_schema().tables))}",
                given=name,
                allowed=_schema().tables,
            )
        return {k: _expand(v, f"{name}.{k}") for k, v in self._merged[name].items()}

    def addresses(self) -> list[str]:
        """Every setting a project may declare, as `table.key`."""
        tables = _schema().tables
        return [f"{t}.{k}" for t in sorted(tables) for k in sorted(tables[t])]

    def states(self, table: str) -> bool:
        """Whether the project wrote this table at all, rather than take the default."""
        return bool(self._declared.get(table))

    def declared(self, address: str) -> bool:
        """Whether the project stated this itself, rather than taking the default."""
        table, _, key = address.partition(".")
        return key in self._declared.get(table, {})

    def tolerances(self, rung: str | None = None) -> Tolerances:
        """Every tolerance in force, resolved together (§PW40).

        An operation reads this once and passes the numbers down. The functions below it
        take them and have no fallback of their own, so there is nowhere for a second
        value of one number to live.

        `render_noise` is keyed by rung in the file and a single number here, because
        the floor at four samples is not the floor at five hundred (§PW44) and yet the
        code comparing two pictures wants one bar. Naming no rung takes the strictest of
        them, which is the safe way to be wrong: too tight calls an unchanged render
        changed, and too loose calls a changed one unchanged.
        """
        table = self.table("tolerance")
        noise = table["render_noise"]
        if isinstance(noise, dict):
            noise = noise.get(rung, min(noise.values())) if noise else 0.0
        values = {
            f.name: float(table[f.name])
            for f in fields(Tolerances)
            if f.name != "render_noise"
        }
        return Tolerances(render_noise=float(noise), **values)

    # -- the paid services ------------------------------------------------------

    def services(self) -> dict[str, dict]:
        """Every paid service the project declares, by name (§PW162).

        A bare `[service]` is one service, called `default`. Named tables are as many
        as the project writes, and a named one's learned schema defaults to a file of
        its own, so two services never overwrite what the other was proved to accept.
        """
        named = _named(self._declared.get("service", {}))
        if not named:
            bare = self.table("service")
            return {DEFAULT_SERVICE: {k: bare[k] for k in _schema().tables["service"]}}
        return {
            name: {
                **_schema().tables["service"],
                "schema": f"polyweave.service.{name}.toml",
                **{k: _expand(v, f"service.{name}.{k}") for k, v in stated.items()},
            }
            for name, stated in named.items()
        }

    def service(self, name: str | None = None, *, model: str | None = None) -> str:
        """The one service a call means, resolved and never guessed.

        Naming none is right where the project declares one, or where exactly one of
        several has a `prices` row for the `model` the call buys (§PW264): the project
        has then said which service sells it. Otherwise the call is refused: which
        balance to draw on is the one choice a ceiling exists to take away from whoever
        is spending.
        """
        declared = self.services()
        if name is None:
            if len(declared) == 1:
                return next(iter(declared))
            selling = sorted(
                one for one, about in declared.items()
                if model is not None and _sells(about, model)
            )
            if len(selling) == 1:
                return selling[0]
            priced = ""
            if model is not None:
                priced = (f"; {' and '.join(selling)} all price {model!r}" if selling
                          else f"; none prices {model!r}")
            raise PolyweaveError(
                "fetch.service-unnamed",
                f"the project declares {len(declared)} paid services and the call "
                f"named none of them{priced}",
                f"pass the service: one of {', '.join(selling or sorted(declared))}",
                allowed=selling or sorted(declared),
            )
        if name not in declared:
            near = difflib.get_close_matches(name, declared, n=1)
            raise PolyweaveError(
                "fetch.unknown-service",
                f"{name!r} is not a service this project declares",
                f"did you mean {near[0]!r}?"
                if near
                else f"name one of {', '.join(sorted(declared))}",
                given=name,
                allowed=sorted(declared),
            )
        return name

    def service_path(self, name: str | None = None) -> Path:
        """Where one service's learned schema lives, inside the tree."""
        chosen = self.service(name)
        if chosen == DEFAULT_SERVICE and not _named(self._declared.get("service", {})):
            return self.path("service.schema")
        return self.path(f"service.{chosen}.schema", self.services()[chosen]["schema"])

    # -- the look ---------------------------------------------------------------

    def styles(self) -> dict[str, dict]:
        """Every asset family's declared style, by name (§PW166).

        A bare `[style]` is one family, `default`; `[style.<family>]` tables are as many
        as the project writes. `canon` resolves to a directory inside the tree.
        """
        named = _named(self._declared.get("style", {}))
        stated = named or {DEFAULT_FAMILY: self._declared.get("style", {})}
        found = {}
        for family, own in stated.items():
            style = {**_schema().tables["style"], **own}
            address = f"style.{family}.canon" if named else "style.canon"
            style["canon"] = (
                str(self.path(address, style["canon"])) if style["canon"] else ""
            )
            at = f"style.{family}" if named else "style"
            if style["palette_source"]:
                style["palette"] = _palette_in_code(self.root, style["palette_source"],
                                                    at)
            if style["borrow"]:
                style["palette"], style["borrowed"] = _borrowed(
                    self.root, style["borrow"], at)
            found[family] = style
        return found

    def style(self, family: str | None = None) -> tuple[str, dict]:
        """One family's style, resolved as a service is: never guessed among several."""
        declared = self.styles()
        if family is None:
            if len(declared) == 1:
                return next(iter(declared.items()))
            raise PolyweaveError(
                "style.family-unnamed",
                f"the project declares {len(declared)} styles and the call named none",
                f"pass the asset's family: one of {', '.join(sorted(declared))}",
                allowed=sorted(declared),
            )
        if family not in declared:
            near = difflib.get_close_matches(family, declared, n=1)
            raise PolyweaveError(
                "style.unknown-family",
                f"{family!r} is not a family this project declares a style for",
                f"did you mean {near[0]!r}?"
                if near
                else f"name one of {', '.join(sorted(declared))}, or declare "
                f"[style.{family}]",
                given=family,
                allowed=sorted(declared),
            )
        return family, declared[family]

    # -- the audio --------------------------------------------------------------

    def sounds(self) -> dict[str, dict]:
        """Every sound family the project declares, by name, with its folder resolved.

        A bare `[sound]` is one family, `default`, and a project that writes neither
        declares no audio at all, which is an empty answer rather than a default cue.
        Two cues landing on one file are refused, since making one would overwrite the
        other.
        """
        stated_table = self._declared.get("sound", {})
        named = _named(stated_table)
        stated = named or ({DEFAULT_FAMILY: stated_table} if stated_table else {})
        found, owners = {}, {}
        for family, own in stated.items():
            sound = {**_schema().tables["sound"], **own}
            address = f"sound.{family}.folder" if named else "sound.folder"
            # Joined before resolving, so an absolute folder or one that climbs out is
            # refused by `path` like any other path setting.
            folder = self.path(
                address, Path(str(self.get("paths.audio"))) / str(sound["folder"])
            )
            sound["folder"] = str(folder)
            for cue in sound["cues"]:
                file = folder / f"{cue}.{sound['format']}"
                if file in owners:
                    raise PolyweaveError(
                        "sound.cue-twice",
                        f"{cue} in {family} and {owners[file]} both land on "
                        f"{file.relative_to(self.root).as_posix()}",
                        "rename one of them, or give one family its own folder",
                        at=f"sound.{family}.cues",
                    )
                owners[file] = f"{cue} in {family}"
            found[family] = sound
        return found

    def references(self) -> dict[str, dict]:
        """Every reference video's declared regions, by name (§PW380).

        A bare `[reference]` is one, `default`; `[reference.<name>]` tables are as many
        as the project writes. Each region is checked to be a rectangle inside `size`,
        the minimap to name one of them, and each blip to be a colour.
        """
        stated_table = self._declared.get("reference", {})
        named = _named(stated_table)
        stated = named or ({DEFAULT_FAMILY: stated_table} if stated_table else {})
        found = {}
        for name, own in stated.items():
            declared = {**_schema().tables["reference"], **own}
            at = f"reference.{name}" if named else "reference"

            def bad(key: str, what: str, remedy: str, at: str = at) -> PolyweaveError:
                return PolyweaveError("config.bad-type", f"{at}.{key} {what}", remedy,
                                      at=f"{at}.{key}")

            size = declared["size"]
            if not (isinstance(size, list) and len(size) == 2
                    and all(isinstance(v, int) and v > 0 for v in size)):
                raise bad("size", f"is {size!r}",
                          "write the source frame's [width, height] in pixels")
            for region, box in declared["regions"].items():
                if not (isinstance(box, list) and len(box) == 4
                        and all(isinstance(v, int | float) for v in box)
                        and 0 <= box[0] < box[2] <= size[0]
                        and 0 <= box[1] < box[3] <= size[1]):
                    raise bad(f"regions.{region}", f"is {box!r}",
                              f"write it as [left, top, right, bottom] inside the "
                              f"{size[0]}x{size[1]} frame")
            if declared["minimap"] and declared["minimap"] not in declared["regions"]:
                raise bad("minimap",
                          f"names {declared['minimap']!r}, which is no region",
                          f"name one of {', '.join(sorted(declared['regions']))}")
            colours = {"player": declared["player"], **{
                f"blips.{k}": v for k, v in declared["blips"].items()}}
            for key, colour in colours.items():
                if (colour or key != "player") and not (
                        isinstance(colour, str) and _HEX.fullmatch(colour)):
                    raise bad(key, f"is {colour!r}", "write a colour as #rrggbb")
            found[name] = declared
        return found

    def reference(self, name: str | None = None) -> tuple[str, dict]:
        """One reference's declaration, resolved as a style is: never guessed."""
        declared = self.references()
        if name is None and len(declared) == 1:
            return next(iter(declared.items()))
        if name not in declared:
            raise PolyweaveError(
                "capture.unknown-reference",
                f"{name!r} is not a reference this project declares"
                if name else f"the project declares {len(declared)} references and "
                "the call named none",
                f"name one of {', '.join(sorted(declared))}" if declared
                else "declare [reference.<name>] with its size and regions",
                given=str(name),
                allowed=sorted(declared),
            )
        return name, declared[name]

    def cue_files(self) -> dict[str, Path]:
        """Every declared cue by name, at the file it lands on, across all families."""
        return {
            cue: Path(sound["folder"]) / f"{cue}.{sound['format']}"
            for sound in self.sounds().values()
            for cue in sound["cues"]
        }

    def sound(self, family: str | None = None) -> tuple[str, dict]:
        """One family's declared audio, resolved as a style is: never guessed."""
        declared = self.sounds()
        if family is None:
            if len(declared) == 1:
                return next(iter(declared.items()))
            raise PolyweaveError(
                "sound.family-unnamed",
                f"the project declares {len(declared)} sound families and the call "
                f"named none",
                f"pass the family: one of {', '.join(sorted(declared)) or '(none)'}",
                allowed=sorted(declared),
            )
        if family not in declared:
            near = difflib.get_close_matches(family, declared, n=1)
            raise PolyweaveError(
                "sound.unknown-family",
                f"{family!r} is not a sound family this project declares",
                f"did you mean {near[0]!r}?"
                if near
                else f"declare [sound.{family}] with its cues",
                given=family,
                allowed=sorted(declared),
            )
        return family, declared[family]

    # -- the one read that is a decision ---------------------------------------

    def budget(self, today: date | None = None, service: str | None = None) -> dict:
        """What may be spent on one service, which is a person's decision written down.

        An expired or absent budget means no spend at all. The plugin never reads the
        absence of a ceiling as permission, because the balance being spent is real.
        **Ceilings never pool**: each service is judged against its own, in its own
        unit, because credits and dollars are not one number.
        """
        name = self.service(service)
        if _named(self._declared.get("service", {})):
            stated = _named(self._declared.get("budget", {})).get(name, {})
            ceiling = {**_NAMED_BUDGET, **stated}
            table = f"[budget.{name}]"
            amount, unit = ceiling["amount"], str(ceiling["unit"])
        else:
            ceiling = self.table("budget")
            table = "[budget]"
            amount, unit = ceiling["credits"], "credits"
        expires = str(_expand(ceiling["expires"], f"{table}.expires")).strip()
        found = {
            "service": name,
            "amount": amount,
            "unit": unit,
            # Where the person raises it, which is what a refusal has to name.
            "table": table,
            "expires": expires or None,
            "spendable": False,
            "why": "",
        }
        if amount <= 0:
            return {**found, "why": f"no {unit} are declared in {table} of {FILENAME}"}
        if not expires:
            return {
                **found,
                "why": "the budget has no expiry, and one without a date never lapses",
            }
        try:
            when = date.fromisoformat(expires)
        except ValueError:
            raise PolyweaveError(
                "config.bad-type",
                f"{table} expires is {expires!r}, which is not a date",
                "write it as YYYY-MM-DD",
            ) from None
        if when < (today or date.today()):
            return {**found, "why": f"the budget expired on {expires}"}
        return {**found, "spendable": True}


def load(root: str | Path = ".") -> Config:
    """Read this project's settings, now rather than at startup."""
    where = Path(root).expanduser().resolve()
    source = where / FILENAME
    if not source.is_file():
        return Config(where, {}, None)
    try:
        declared = tomllib.loads(source.read_text(encoding="utf-8-sig"))
    except tomllib.TOMLDecodeError as exc:
        raise PolyweaveError(
            "config.malformed",
            f"{source} is not readable as TOML",
            "fix the syntax the detail below points at",
            detail=str(exc),
        ) from exc
    except OSError as exc:
        raise PolyweaveError(
            "config.malformed",
            f"{source} could not be read",
            "check that it is a file and readable",
            detail=str(exc),
        ) from exc
    _check(declared, source)
    declared_root = declared.get("project", {}).get("root")
    if declared_root:
        where = (where / str(declared_root)).resolve()
    return Config(where, declared, source)


def _off_tables(declared: dict) -> None:
    """A table of a layer `[layers] on` leaves off, refused by the layer's name."""
    named = (declared.get("layers") or {}).get("on") or []
    if not named:
        return
    owner = _schema().owner
    for table in declared:
        if owner.get(table) and owner[table] not in named:
            raise PolyweaveError(
                "layer.off",
                f"[{table}] is the {owner[table]} layer's, and [layers] on leaves "
                f"{owner[table]} off",
                f'add "{owner[table]}" to [layers] on, or drop [{table}]',
                given=table,
            )


def _check(declared: dict, source: Path) -> None:
    """Refuse a key nothing declares, rather than ignoring it.

    §3 of the tool surface: an unknown field in any input is refused. A config key that
    is silently dropped is a setting the caller believes is in effect and is not.
    """
    _off_tables(declared)
    for table, values in declared.items():
        if table not in _schema().tables:
            near = difflib.get_close_matches(table, _schema().tables, n=1)
            raise PolyweaveError(
                "config.unknown-table",
                f"{source.name} declares [{table}], which is not a table",
                f"did you mean [{near[0]}]?"
                if near
                else f"the tables are {', '.join(sorted(_schema().tables))}",
                given=table,
                allowed=_schema().tables,
            )
        if not isinstance(values, dict):
            raise PolyweaveError(
                "config.bad-type",
                f"[{table}] is a table, and {source.name} gives it a value",
                f"write it as [{table}] with keys under it",
            )
        if table == "kit":
            loose = sorted(k for k, v in values.items() if not isinstance(v, dict))
            if loose:
                raise PolyweaveError(
                    "config.bad-type",
                    f"[kit] holds {', '.join(loose)}, and it holds one table per kit",
                    "write it as [kit.<name>], the kit's own declaration",
                    at=f"kit.{loose[0]}",
                )
            continue
        if table in _schema().named and _named(values):
            _check_named(table, values, source)
            continue
        for key, value in values.items():
            _check_key(table, key, value, source)
    _check_services(declared, source)


#: Settings of one service whose value is itself a table, so not a named service.
_KERNEL_SETTINGS = ("prices",)


def _sells(about: dict, model: str) -> bool:
    """Whether a service's `prices` has a row for a model, a speed of it included."""
    return any(
        str(row) == model or str(row).split(":", 1)[0] == model
        for row in (about.get("prices") or {})
    )


#: One `NAME = "#rrggbb"` constant of a file of code, with or without its type.
_CONSTANT = re.compile(
    r'(?m)^\s*([A-Za-z_]\w*)\s*(?::[^=]*)?=\s*["\'](#[0-9a-fA-F]{6})["\']'
)


def _palette_in_code(root: Path, source: dict, at: str) -> list[str]:
    """A palette read off the `NAME = "#rrggbb"` constants of a file (§PW387)."""
    where = root / str(source.get("file", ""))
    if not source.get("file") or not where.is_file():
        raise PolyweaveError(
            "config.bad-type",
            f"{at}.palette_source names {source.get('file')!r}, and there is no file "
            "there",
            "name the file the palette is kept in, under the project",
            at=f"{at}.palette_source",
        )
    held = {m[1]: m[2].upper() for m in _CONSTANT.finditer(where.read_text("utf-8"))}
    names = list(source.get("names") or held)
    lacking = [n for n in names if n not in held]
    if lacking:
        raise PolyweaveError(
            "config.bad-type",
            f"{where.name} holds no colour called {lacking[0]}",
            "name constants the file writes as NAME = \"#rrggbb\"",
            at=f"{at}.palette_source.names", given=lacking[0],
        )
    return [held[n] for n in names]


def _shifted(colour: str, lightness: float, saturation: float) -> str:
    """One colour moved in HLS lightness and saturation, each clamped to 0 to 1."""
    import colorsys

    r, g, b = (int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, light, sat = colorsys.rgb_to_hls(r, g, b)
    light = min(1.0, max(0.0, light + lightness))
    sat = min(1.0, max(0.0, sat + saturation))
    return "#" + "".join(f"{round(v * 255):02X}" for v in colorsys.hls_to_rgb(
        h, light, sat))


def _borrowed(root: Path, borrow: dict, at: str) -> tuple[list[str], dict]:
    """Another project's palette, shifted for this game, and whether it moved."""
    import hashlib

    source = Path(str(borrow.get("root", "")))
    source = source if source.is_absolute() else (root / source).resolve()
    if not (source / FILENAME).is_file():
        raise PolyweaveError(
            "config.bad-type",
            f"{at}.borrow names {borrow.get('root')!r}, which holds no {FILENAME}",
            "name the other project's root, relative to this one or absolute",
            at=f"{at}.borrow.root",
        )
    family, theirs = load(source).style(borrow.get("family") or None)
    palette = [str(c).upper() for c in theirs.get("palette") or []]
    digest = hashlib.sha256(",".join(palette).encode()).hexdigest()[:16]
    pinned = str(borrow.get("pinned") or "")
    shift = float(borrow.get("lightness", 0.0)), float(borrow.get("saturation", 0.0))
    return [_shifted(c, *shift) for c in palette], {
        "root": source.as_posix(), "family": family, "digest": digest,
        "pinned": pinned, "moved": bool(pinned) and pinned != digest,
        "lightness": shift[0], "saturation": shift[1],
    }


def _named(values: dict) -> dict[str, dict]:
    """The `[table.<name>]` subtables of a table that may hold several services."""
    return {
        k: v
        for k, v in values.items()
        if isinstance(v, dict) and k not in _schema().settings
    }


def _check_named(table: str, values: dict, source: Path) -> None:
    """Each `[service.<name>]` or `[budget.<name>]` takes the keys one service has."""
    loose = sorted(set(values) - set(_named(values)))
    if loose:
        raise PolyweaveError(
            "config.services-mixed",
            f"{source.name} sets {', '.join(f'{table}.{k}' for k in loose)} beside "
            f"named [{table}.<name>] tables, so whose they are is a guess",
            f"move them under the [{table}.<name>] they belong to",
            at=table,
        )
    allowed = {
        "service": _schema().tables["service"],
        "style": _schema().tables["style"],
        "sound": _schema().tables["sound"],
        "reference": _schema().tables["reference"],
    }.get(table, _NAMED_BUDGET)
    for name, stated in values.items():
        for key, value in stated.items():
            if key not in allowed:
                near = difflib.get_close_matches(key, allowed, n=1)
                raise PolyweaveError(
                    "config.unknown-key",
                    f"{source.name} sets {table}.{name}.{key}, which is not a setting",
                    f"did you mean {table}.{name}.{near[0]}?"
                    if near
                    else f"[{table}.{name}] takes {', '.join(sorted(allowed))}",
                    given=key,
                    allowed=allowed,
                    at=f"{table}.{name}.{key}",
                )
            _check_type(f"{table}.{name}.{key}", allowed[key], value, source)
            _check_value(f"{table}.{name}.{key}", key, value, source)


def _check_services(declared: dict, source: Path) -> None:
    """A ceiling belongs to a service, and is stated one way (§PW162)."""
    services = _named(declared.get("service", {}))
    budget = declared.get("budget", {})
    ceilings = _named(budget)
    if services and budget and not ceilings:
        raise PolyweaveError(
            "config.services-mixed",
            f"{source.name} names {len(services)} services and gives one bare "
            f"[budget], which says nothing about whose ceiling it is",
            f"write it as [budget.<name>] for one of {', '.join(sorted(services))}",
            at="budget",
        )
    stray = sorted(set(ceilings) - set(services))
    if stray:
        raise PolyweaveError(
            "config.services-mixed",
            f"{source.name} declares [budget.{stray[0]}], and there is no "
            f"[service.{stray[0]}] for it to be the ceiling of",
            f"declare [service.{stray[0]}], or name the ceiling after one of "
            f"{', '.join(sorted(services)) or 'the declared services'}",
            given=stray[0],
            allowed=sorted(services),
            at=f"budget.{stray[0]}",
        )


def _check_key(table: str, key: str, value: Any, source: Path) -> None:
    allowed = _schema().tables[table]
    if key not in allowed:
        if table in _schema().free:
            return
        near = difflib.get_close_matches(key, allowed, n=1)
        raise PolyweaveError(
            "config.unknown-key",
            f"{source.name} sets {table}.{key}, which is not a setting",
            f"did you mean {table}.{near[0]}?"
            if near
            else f"[{table}] takes {', '.join(sorted(allowed))}",
            given=key,
            allowed=allowed,
            at=f"{table}.{key}",
        )
    if f"{table}.{key}" in _schema().open:
        return
    _check_type(f"{table}.{key}", allowed[key], value, source)
    _check_value(f"{table}.{key}", key, value, source)


#: Settings whose value is one of a few words.
_KERNEL_CHOICES: dict[str, tuple[str, ...]] = {}

#: A colour as a palette states it.
_HEX = re.compile(r"#[0-9a-fA-F]{6}")

#: A cue's name, which is also its file's stem, so it carries no folder of its own.
_CUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")


def _check_value(address: str, key: str, value: Any, source: Path) -> None:
    """The settings whose type alone does not say whether a value is one."""
    if key == "prices":
        _check_prices(address, value, source)
    elif key in _schema().choices and value not in _schema().choices[key]:
        raise PolyweaveError(
            "config.bad-type",
            f"{address} is {value!r} in {source.name}, which is not one of "
            f"{', '.join(_schema().choices[key])}",
            f"write one of {', '.join(_schema().choices[key])}",
            given=str(value),
            allowed=_schema().choices[key],
            at=address,
        )
    elif address == "voxels.cell" and value < 0:
        raise PolyweaveError(
            "config.bad-type",
            f"{address} is {value!r} in {source.name}, and a cell has a size",
            "write the cell's size above zero, or 0 for no project-wide cell",
            at=address,
        )
    elif key == "cell" and address.startswith("style") and value and (
        len(value) != 2 or not all(isinstance(v, int) and v > 0 for v in value)
    ):
        raise PolyweaveError(
            "config.bad-type",
            f"{address} is {value!r} in {source.name}, and a cell is two whole numbers",
            "write it as [width, height] in pixels, or [] to leave the size alone",
            at=address,
        )
    elif key == "cues":
        wrong = [c for c in value if not isinstance(c, str) or not _CUE.fullmatch(c)]
        if wrong:
            raise PolyweaveError(
                "config.bad-type",
                f"{address} holds {wrong[0]!r} in {source.name}, and a cue is a bare "
                f"name that becomes its file's stem",
                "write the name alone, such as music_calm; a folder goes in `folder`",
                at=address,
            )
    elif key == "palette":
        wrong = [c for c in value if not isinstance(c, str) or not _HEX.fullmatch(c)]
        if wrong:
            raise PolyweaveError(
                "config.bad-type",
                f"{address} holds {wrong[0]!r} in {source.name}, and a palette colour "
                f"is a value, not a name",
                "write each colour as #rrggbb",
                at=address,
            )


#: The units a `prices` row may be charged by, besides one call (§PW320).
PER = ("character",)


def _check_prices(address: str, prices: dict, source: Path) -> None:
    """A price is a number above nothing: a free row would under-count the ceiling.

    A row may name its unit instead, `{ per = "character", rate = <n> }`, for a service
    that bills by what is sent rather than by the call (§PW320).
    """
    for row, price in prices.items():
        if isinstance(price, dict):
            _check_rate(f"{address}.{row}", price, source)
            continue
        if isinstance(price, bool) or not isinstance(price, int | float) or price <= 0:
            raise PolyweaveError(
                "config.bad-type",
                f"{address}.{row} is {price!r} in {source.name}, and a price is a "
                f"number above zero",
                "write what one output costs, in the unit of the service's ceiling",
                at=f"{address}.{row}",
            )


def _check_rate(address: str, row: dict, source: Path) -> None:
    """A row by the unit: what it is charged per, and a rate above nothing."""
    unknown = sorted(set(row) - {"per", "rate"})
    rate = row.get("rate")
    if unknown or row.get("per") not in PER or (
        isinstance(rate, bool) or not isinstance(rate, int | float) or rate <= 0
    ):
        raise PolyweaveError(
            "config.bad-type",
            f"{address} is {row!r} in {source.name}, and a row by the unit is "
            f"{{ per = <unit>, rate = <price of one> }}",
            f"write per as one of {', '.join(PER)} and rate as a number above zero, "
            "in the unit of the service's ceiling",
            at=address,
        )


def _check_type(address: str, default: Any, value: Any, source: Path) -> None:
    if isinstance(default, bool) != isinstance(value, bool) or not isinstance(
        value, type(default) if not isinstance(default, int | float) else int | float
    ):
        raise PolyweaveError(
            "config.bad-type",
            f"{address} is a {type(default).__name__}, and {source.name} gives "
            f"a {type(value).__name__}",
            f"write it as a {type(default).__name__}",
        )


def _merge(base: dict, over: dict, at: str = "") -> dict:
    out: dict[str, Any] = {}
    for key, value in base.items():
        address = f"{at}.{key}" if at else key
        stated = over.get(key)
        if isinstance(value, dict) and address in _schema().open:
            # Keyed by names the project chooses, so what it states replaces the
            # default outright: a project that renames its rungs would otherwise
            # inherit samples for rungs it does not have.
            out[key] = dict(stated) if stated else dict(value)
        elif isinstance(value, dict):
            out[key] = _merge(value, stated or {}, address)
        elif key in over:
            out[key] = stated
        else:
            out[key] = list(value) if isinstance(value, list) else value
    for key, value in over.items():
        out.setdefault(key, value)
    return out


def _expand(value: Any, address: str) -> Any:
    """Resolve `${NAME}` against the environment, now rather than at startup."""
    if isinstance(value, list):
        return [_expand(v, address) for v in value]
    if isinstance(value, dict):
        return {k: _expand(v, f"{address}.{k}") for k, v in value.items()}
    if not isinstance(value, str):
        return value

    def one(match: re.Match) -> str:
        name = match.group(1)
        found = os.environ.get(name)
        if found is None:
            raise PolyweaveError(
                "config.env-unset",
                f"{address} names ${{{name}}}, and {name} is not set here",
                f"set {name} in this environment, or write the value in {FILENAME}",
            )
        return found

    return _ENV_REF.sub(one, value)
