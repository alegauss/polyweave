# A score as a source

Binds **PW186**, and is what the render (PW187), the layers (PW188) and the credits (PW191)
read.

An agent composes well only when its output is structured and a validator answers it. A
piece is also something a person reopens and changes. So the file that is edited and the
model that is checked are two layers: the **source**, a `*.music.toml` in the consumer's
repository beside its `*.accept.toml`, and the **model**, compiled from it and never
edited.

## The source

```toml
[music]
title = "Sugar Rush"
bpm   = 132                  # 20 to 400
meter = [4, 4]               # [beats, unit]; a bar of [6, 8] is three quarter notes
key   = "C major"            # display text, as piano keeps it
form  = ["A", "B", "A", "C"] # the sections in the order they play
loop  = true                 # false for a stinger that plays once
loop_from = "A"              # where the loop comes back in; the first section by default

[section.A]
bars = 8

[pattern]                    # one named line each, in mini-notation, one cycle per bar
lead_a = "<[g4 c5 e5 g5@2 e5 g5@2] [f5 e5 d5@2 b4@2 g4@2]>"
bass_a = "<[c2 c3]*4 [g2 g3]*4>"
beat   = "[bd ~ sd ~, hh*8]"

[[track]]
name       = "lead"          # a lower-case id, once per score
instrument = "surge:chip_lead"   # the renderer's business; gm:<program> sets a MIDI program
layer      = "base"          # which intensity it belongs to
drums      = false           # true puts it on the drum channel and allows drum names
velocity   = 96              # 1 to 127
groove     = 0.0             # 0 to 1: how much the grid accents a downbeat over an offbeat
wobble     = 0.0             # a seeded spread on velocity, the same on every compile
gate       = 0.9             # how much of its step a note sounds, 0.05 to 4
play       = { A = "lead_a", B = "lead_b" }   # section -> pattern; a section left out is silent
```

**Every key is refused unless it is one of these**, with the nearest name offered, and
`title`, `bpm`, `form`, and each track's `name`, `instrument` and `play` are required.

## The notation

Strudel's mini-notation, a subset, where **one cycle is one bar**:

| Written | Means |
|---|---|
| `c4 d4 e4` | three steps sharing the bar evenly; C4 is MIDI 60, `f#5`, `eb3` and `cs4` are notes |
| `c4@3 d4` | weights: C4 holds three parts of four |
| `c4 _ _ d4` | `_` extends the step before it, the same as `c4@3 d4` |
| `~` | a rest |
| `[a4 b4]` | subdivides one step |
| `[c4, e4, g4]` | a stack, played together |
| `<c4 d4 e4>` | one per bar, in turn; nests, so `<a4 <b4 c5>>` plays a b a c |
| `c4*4` | the step repeated four times inside itself |
| `c4!3` | the step replicated as three steps |
| `bd sd hh oh cp rim lt mt ht cr rd tb cb sh ph` | General MIDI drums, on a `drums = true` track only |

The PW184 spike chose it over ABC. ABC wrote the same three pieces with no disagreement,
but ran two to three times longer on drums and arpeggios, cannot stack voices, and its
accidentals last to the end of the bar, so one missed sharp became two wrong notes.

## The model

The shape of piano's score JSON, version 1, so either program reads it:
`formatVersion`, `metadata` (`title`, `key`), `timing` (`ticksPerQuarter` of 480, `tempo`,
`timeSignatures`), `parts` (one per track), `notes` (each `pitch`, `start` and `duration`
in absolute ticks, `velocity` and `part`) and `sections` (`startTick`, `endTick`). What
piano has no field for is under `extensions["dev.alegauss.polyweave.music"]`: the tempo in
bpm, the `loop` as ticks (null for a stinger), and each track's `instrument`, `layer` and
`drums`.

- **The same source compiles to the same notes**, velocities included: the wobble is
  seeded by the score's and the track's names.
- **One pitch never overlaps itself in a track**: a note is cut where the next strike of
  its pitch begins. Two strikes of one pitch on one tick are refused, since MIDI cannot
  hold them.
- **A source with any problem compiles to nothing.** A half-compiled score is one a render
  would play wrong without saying so.

## The operations

`music.validate` compiles a source and answers **every problem at once**, each as `code`,
`line`, `message` and `remedy`, because an agent repairing a score fixes everything it is
told in one pass. A valid score answers its length in `seconds`, its `notes` per track and
its `loop`. The codes are the `music.` area's: `unreadable`, `unknown-key`, `missing`,
`bad-value`, `unknown-section`, `unknown-pattern`, `bad-pattern` (with the character in
the pattern), `out-of-range` and `overlap`.

`music.to_midi` writes a valid score as a Standard MIDI File, format 1: a conductor track
(title, tempo, meter), then one track per part. A drum part plays on channel 10, and an
instrument written `gm:<program>` sets the program, so any DAW opens the result. A score
with problems is refused with `music.invalid`. The file goes beside the score unless `out`
names somewhere else in the project.
