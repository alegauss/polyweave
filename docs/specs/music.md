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
room  = 0.55                 # the reverb's size, 0 to 1

[section.A]
bars = 8

[pattern]                    # one named line each, in mini-notation, one cycle per bar
lead_a = "<[g4 c5 e5 g5@2 e5 g5@2] [f5 e5 d5@2 b4@2 g4@2]>"
bass_a = "<[c2 c3]*4 [g2 g3]*4>"
beat   = "[bd ~ sd ~, hh*8]"

[patch.chip_lead]            # a Surge XT sound: its own parameter names, as it shows them
a_osc_1_shape    = -100.0    # square
a_osc_1_width_1  = 25.0      # a 25% pulse
a_amp_eg_release = 40.0      # a number; the render picks Surge's nearest label, "40.0 ms"
a_play_mode      = "Mono"

[[track]]
name       = "lead"          # a lower-case id, once per score
instrument = "surge:chip_lead"   # surge:<patch>, gm:<program 0-127> or drums:<kit 0-127>
layer      = "base"          # which intensity it belongs to
drums      = false           # true puts it on the drum channel and allows drum names
velocity   = 96              # 1 to 127
groove     = 0.0             # 0 to 1: how much the grid accents a downbeat over an offbeat
wobble     = 0.0             # a seeded spread on velocity, the same on every compile
gate       = 0.9             # how much of its step a note sounds, 0.05 to 4
gain       = 0.0             # dB, after every stem is levelled to one RMS; -60 to 24
pan        = 0.0             # -1 left to 1 right
reverb     = -12.0           # the send, in dB; left out is no reverb
delay      = -18.0           # a dotted-eighth echo send, in dB; left out is none
play       = { A = "lead_a", B = "lead_b" }   # section -> pattern; a section left out is silent
```

An instrument is checked when the score compiles: a `surge:` patch the score does not
declare, a program past 127, or a drum kit on a track that is not `drums = true` is a
problem `music.validate` names (`music.unknown-instrument`). Which parameter names a patch
may use is Surge's to say, and changes with the oscillator type, so those are checked when
the render sets them (`music.unknown-parameter`, with the nearest name).

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

## Rendering

`music.render` is a job (`bake`) that turns a valid score into WAV and OGG headlessly,
through engines that already exist. The PW184 spike chose them, and a person judged three
loops made this way good enough to ship:

- **`surge:` parts** play through Surge XT, a VST3 loaded by Pedalboard (the `audio`
  extra). A load takes 25 to 77 seconds, so one instance serves the whole render and is
  reset between patches by restoring each parameter's raw value; restoring its saved
  state silences it. On Windows the binary inside the bundle is the one loaded.
- **`gm:` and `drums:` parts** play through FluidSynth's command line from the
  SoundFont `[paths] soundfont` names, with FluidSynth's own reverb and chorus off.
- A missing engine is refused by name before any part renders (`music.no-engine`).

**One fixed chain**, because the instruments and the mix decide how professional it sounds
more than the notes do: every stem is levelled to -20 dBFS at the 95th percentile of its
50 ms RMS windows, then the track's `gain`, `pan` and sends apply; the sends go to a reverb
of the score's `room` and a dotted-eighth delay; the master is a 30 Hz high-pass, a 2.5:1
compressor and a limiter, levelled to -18 dBFS RMS under a -1 dBFS peak.

**A loop is rendered as a loop.** Four seconds past the end are rendered and folded back
onto the loop's start, so a release or a reverb rings across the seam; where the loop
starts the piece, the master runs over it as a cycle, so the compressor at the start has
heard the end. A stinger (`loop = false`) keeps its tail and has no seam. The answer
carries what `sound.measure` says of the WAV, without the seam for a stinger, and each
part's engine.

## Layers

Game music changes with play, so one theme can be written at several intensities: each
track names a `layer` (a lower-case id, `base` by default), and a score with more than one
also writes `<out>.<layer>.wav` and `.ogg` per layer, beside the whole mix. **Every layer
file has the render's exact length and grid**, so a game fading layers in and out never
hears them drift; which layer plays when is the game's.

A layer is its tracks mixed with their own sends and folded like the whole, then passed
through the master's 30 Hz high-pass and **the gain the master applied to the whole,
moment by moment** (read off 10 ms windows of what went in and what came out). So the
layers add back up to the mix the game hears with every layer in: on the test score they
correlate with it at 0.997, where one static gain for every layer reached 0.906 and drifted
wherever the compressor moved. The whole mix is the file an acceptance spec bounds for the
layers' summed loudness; each layer file is measured in the answer like any other.
