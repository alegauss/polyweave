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
