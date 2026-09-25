# The world declaration

A game's world is written twice. The prose (Starship's `docs/design/world.md`) is what a
person writes and reads. Beside it, a `*.world.toml` in the consumer's repository declares
the part a tool can check: which names, factions and characters the world holds. The prose
stays the source; the declaration is what every later line in Block Q checks against, and
what Block R's level declarations refer to by id.

**A person writes this file and the plugin only reads it.** Nothing in polyweave composes
an entity, a name or a rule, for the reason the non-goal on a game's story gives.

## The file

```toml
[entity.crew]
name = "The Crew"
kind = "faction"

[entity.ada]
code = "ada"              # the name the game's scripts use; the id where unset
name = "Captain Ada"      # the name a player reads
kind = "character"        # place, faction, character, enemy or item
faction = "crew"          # the id of an entity whose kind is faction
style = "portrait"        # the [style.<family>] of polyweave.toml its pictures are held to
first = "act 1"           # where in the run it first appears

[rules]
longest_line = 80         # the longest line a player reads, in characters
silent = ["drone"]        # entities that never speak
unshown = ["nemesis"]     # entities whose name is never shown
```

- An entity is `[entity.<id>]`. The id is how everything else refers to it, and is unique
  because TOML refuses a table written twice.
- `name` and `kind` are required. `code`, `faction`, `style` and `first` are optional and
  are text.
- `[entity.<id>.look]` is optional: a `description` and two lists of texts, `shows` (the
  traits that must appear) and `never` (the ones that must not). It is what a picture or
  a mesh of the entity is bought from.
- `[rules]` is optional, and each of its three keys is too.
- Any other table, entity field or rule is refused, as an unknown config key is: a field
  that is silently dropped is a setting the author believes is in effect and is not.

## The operations

`world.read` returns every entity and the rules, or one entity with `entity`. It refuses a
file whose shape is wrong, with the first fault's code.

`world.validate` returns `valid`, the entity count and `findings`: each is an error in the
wire form of [tool-surface.md](tool-surface.md) §3 with the `line` it is written on, and
`at` as `<file>:<line>`. Beside every fault of shape, it reports

| Code | What it finds |
|---|---|
| `world.duplicate-name` | two entities sharing a `name`, or a `code`, compared without case |
| `world.unknown-faction` | a `faction` naming no entity, or one whose kind is not faction |
| `world.unknown-family` | a `style` that polyweave.toml's `[style]` tables do not declare |
| `world.unknown-entity` | a rule naming an id no entity has |

Both find the file themselves where the project holds one, skipping dot-directories, and
refuse with `world.several` where it holds more than one and the call named none.

    python -m polyweave world.validate --world docs/design/starship.world.toml --json

## An asset bought from an entity

`picture.buy` and `mesh.buy` take `entity=<id>` (and `world` where the project holds
several). The prompt is composed from the entity: its look's description, or its name
where it has no look, then the call's own words as detail, then `It shows ...` and
`It never shows ...` from its traits, so where the call's words disagree the last word
the service reads is the world's. On 4.0 that is the structured prompt's
`high_level_description`, composed over the entity's style family as any structured
prompt is. A `family` other than the entity's own `style` is refused with
`world.family-mismatch`. A mesh bought from a picture still needs the gate, and records
the entity all the same.

The record carries `details.entity` (the id, the world file and the SHA-256 of the
entity's name, kind, style and look) and the world file as an input with the role
`world`. So `provenance.dependents` on the world names each artefact's entity, and
`provenance.outdated` counts a changed world against an artefact only where that
entity's own digest changed. Buying again is still a person's decision under the
purchase ceiling; a world edit triggers nothing.

## The text a player reads

The text is held to the world through a string table, never through a pattern about one
project's scripts: the game reads it through Godot's translation CSV with `tr()`, one key
per row and one column per locale, and `[words] table` in polyweave.toml names the file.
A column whose header starts with an underscore is one Godot skips; `[words] speaker`
(default `_speaker`) names the one holding the id of the entity that speaks the line.

`words.check` returns `passed`, the locales, the row count and `findings`, each with the
`key`, the `locale` (none for a speaker finding), the `rule` and the CSV `row`:

| Code | Rule | What it finds |
|---|---|---|
| `words.unknown-name` | `names` | a word capitalised mid-sentence, or in capitals anywhere, that is no word of a shown name, no code name and not in `[words] ordinary` |
| `words.code-name` | `code_names` | an entity's `code` on screen, where it differs from every shown name |
| `words.too-long` | `longest_line` | a line over `[rules] longest_line`, split at a newline or Godot's escaped `\n` |
| `words.silent-speaks` | `silent` | a row whose speaker the rules call silent |
| `words.unknown-speaker` | `speaker` | a row whose speaker is no entity |
| `words.hidden-name` | `unshown` | any word of an unshown entity's name that no shown name shares |

A `{placeholder}`, a `%s` and a BBCode tag are not read as words.

`words.unlisted` answers what the check cannot see: every literal `text` a node carries
in the project's `.tscn` files that is not a key of the table, as `count` and
`literals` with the scene, line and node.
