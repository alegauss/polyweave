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

[entity.foreman]
name = "Foreman"
plural = "Foremen"        # only where English does not make it by rule
kind = "enemy"

[rules]
longest_line = 80         # the longest line a player reads, in characters
silent = ["drone"]        # entities that never speak
unshown = ["nemesis"]     # entities whose name is never shown
```

- An entity is `[entity.<id>]`. The id is how everything else refers to it, and is unique
  because TOML refuses a table written twice.
- `name` and `kind` are required. `code`, `plural`, `faction`, `style` and `first` are
  optional and are text.
- `[entity.<id>.look]` is optional: a `description` and two lists of texts, `shows` (the
  traits that must appear) and `never` (the ones that must not). It is what a picture or
  a mesh of the entity is bought from.
- `[entity.<id>.voice]` is optional: the service's voice `id` a person chose, a
  `description` of how it should sound and a `sample` line, all text, and its delivery,
  `stability`, `similarity` and `style` from 0 to 1 and `speed` from 0.7 to 1.2. It is
  what every line the entity speaks is spoken in (§PW321).
- `[rules]` is optional, and each of its keys is too. `tone` is a list of sentences no
  check applies: it is what a person judges a line by.
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

## A line an entity speaks

A character is known by its voice across every line, so its voice is read from the world
and never passed per call (§PW321). `sound.speak` takes `entity=<id>` and speaks in the
voice's `id`, with the voice's delivery where the line sets none and the line's own
where it does. An entity whose voice has no `id`, only words about one, is refused with
`world.no-voice` rather than spoken in a voice nobody chose for it, and a call naming a
`voice` other than the entity's is refused with `world.voice-mismatch`.

The record carries `details.entity` as a bought picture's does, with `of = "voice"` and
the SHA-256 of the voice table alone, and the world as an input. So a new voice or
delivery makes every line spoken in it outdated, and an edit to the entity's look does
not.

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

A `{placeholder}`, a `%s` and a BBCode tag are not read as words. In an English locale
(`en`, `en_GB`, `en-US` and the like) the pronoun's contractions `I'm`, `I'll`, `I've`
and `I'd` are never names (§PW244): English capitalises them wherever they
fall, so "Hold still, I've got you" passes with nothing in `[words] ordinary`. Another
locale still reads them, since there they are no pronoun.

**A column is held to its own language's names** (§PW329). An entity may declare its
name in another language as `[entity.<id>.names.<locale>]`, keyed by the column's
header (`pt_BR`): `name`, and where the language's rule does not make them, `plural`,
the grammatical `gender` (`m` or `f`), and for a role a woman may hold, `feminine` and
`feminine_plural`. In that column the form is what the entity is shown by, its plural
by `plural` or else `-s` and `-es`; an entity with no form for the locale keeps its own
name there, which is how a proper noun stays the same. The English name of an entity
the locale renames reads there as its code, and the form reads as an unknown name in
any other column. `[words] ordinary_in = { pt_BR = [...] }` adds ordinary words to one
locale alone. `world.validate` refuses a form with no `name`, a key a form does not
have, and a gender that is neither.

**A name's plural is the name** (§PW257). Every entity is spoken of in the plural
somewhere, so each word of a name counts in its English plural too: `-s`, `-es` after s,
x, z, ch and sh, `-ies` after a consonant's y, and both `-s` and `-men` for `-man`
(Gleaners, Flies, Foremen). An entity whose plural is none of these states it as `plural`,
which then replaces the rule. The same holds for an unshown name. A word that is no name
but near one says which it is near, since that is most often the name misspelled.

**A cell's line break is a line break however it is written** (§PW243). Godot's importer
takes a quoted cell holding a real line break as well as one holding the escaped `\n`, so
the table is read as one stream and a real break, `\n` or `\r\n`, splits the cell exactly
as the escaped one does, both for the words and for the length of each line. Read line by
line, the halves were glued: "REPLAY OVER" over "FIRE" came back as the unknown name
`OVERFIRE`.

`words.check` also returns `unjudged`: the keys whose current text no person has given a
verdict on. They do not fail the check, because whether a line obeys the world's rules is
mechanical and whether it sounds like the world is a person's call.

## A line's tone, judged by a person

`[words] canon` names a JSON file holding every verdict a person gave on a line, oldest
first: the `key`, the `speaker`, the `text` in every locale, its `sha256`, `approved`,
and the `verdict` (`choice`, `why`, `when`). A verdict covers a line only while its text
is the one judged, so a changed line is unjudged again, and the canon keeps what was
approved as it was approved.

`words.sheet` lays out every unjudged line as a sitting for the review page, one family
a line, named `<speaker>.<key>` so a speaker's lines sit together. Each sheet shows the
line in every locale, its speaker, the world's `tone`, the speaker's last approved lines
(`examples`, three by default) and any rule `words.check` says it breaks. The page offers
`accept` (it joins the canon) and `look` (it stays out, with the reason). The answer goes
through `verdict.judge`, whose line members are the only writer of the canon; `number`
is refused, since a line has no bound to move.

`world.read` with `entity` returns that speaker's approved `lines`, the examples a new
line starts from.

`words.unlisted` answers what the check cannot see: every literal `text` a node carries
in the project's `.tscn` files that is not a key of the table, as `count` and
`literals` with the scene, line and node.
