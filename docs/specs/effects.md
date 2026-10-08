# Retro effects from a seed

Binds **PW189**, and is what the credits (PW191) and Cottony's adoption (PW192) read.

A game's retro effects are made by sfxr, DrPetter's generator, ported whole: its parameter
set, its synth loop and its seven generators. They are driven by a `*.sfx.toml` of effects
the game owns, so a person tunes an effect by editing a number, and `sound.synth` makes
them. The same generator and seed give the same bytes on any machine, so a verdict on an
effect holds across runs.

## The file

```toml
[effect.pop_candy]
generator    = "pickup"    # pickup, laser, explosion, powerup, hit, jump or blip
seed         = 12          # the effect's name's CRC32 when left out
min_duration = 0.15        # bounds in seconds; a draw outside moves to the next seed
max_duration = 0.6
peak         = -3.0        # the dBFS the effect is normalised to; a ceiling beside loudness
loudness     = -18.6       # or match = "audio/old_kill.wav": the RMS dBFS it lands at
base_freq    = 0.45        # any sfxr parameter pins the draw's value

[effect.kick]              # no generator: every parameter set by hand
wave      = "sine"         # square, saw, sine or noise
base_freq = 0.32
freq_ramp = -0.55
```

sfxr's parameters are `wave`, `base_freq`, `freq_limit`, `freq_ramp`, `freq_dramp`, `duty`,
`duty_ramp`, `vib_strength`, `vib_speed`, `env_attack`, `env_sustain`, `env_punch`,
`env_decay`, `lpf_resonance`, `lpf_freq`, `lpf_ramp`, `hpf_freq`, `hpf_ramp`, `pha_offset`,
`pha_ramp`, `repeat_speed`, `arp_speed` and `arp_mod`, each from 0 to 1, or from -1 to 1
for a ramp, `pha_offset` and `arp_mod`. Anything else is refused with its nearest name
(`sound.bad-effect`), and so is an effect with neither a generator nor a parameter.

## Making them

`sound.synth` makes every effect in a file, or the one named. Each is centred, faded over
its last 5 ms so it stops on silence, normalised to its peak and written as mono 16-bit WAV
at 44.1 kHz. **An effect named as a cue a project declares under `[sound]` lands at that
cue's file**, encoded by ffmpeg where the family's format is not WAV (`sound.no-encoder`
where there is none); any other lands beside the `*.sfx.toml`.

**A bound draws again.** A first draw can miss its purpose: in the PW184 spike a powerup
meant for a won level came out at 0.11 s. Where an effect with a generator states
`min_duration` or `max_duration`, a draw outside them moves to the next seed, up to 64,
and the answer says the `seed` kept and the `tries` it took. An effect set wholly by hand
has nothing to draw, so a bound it misses is refused (`sound.no-draw`) with the two
parameters that set a length.

The answer gives each effect's `file`, `generator`, `seed`, `tries`, whether it was
`declared`, and its `duration`, `peak` and `loudness`, the measures a one-shot has, which
`sound.measure` and an effect's `*.accept.toml` read the same way.

**An effect may be made to a loudness** (§PW254). A game's mix is weighted on each
effect's loudness, and normalised to a peak alone sfxr's dense explosions came out about
10 dB louder in RMS than the sounds they replaced. So an effect may declare `loudness`,
RMS dBFS as `sound.measure` reports it, or `match` the sound it replaces, whose loudness is
measured; the effect is levelled to it, and `peak` is then a ceiling. The answer adds
`aimed`, the loudness asked for, and `ceiling_bound`, true where the peak held it quieter.
Declaring both is `sound.bad-effect`.

The port is held to the spike's ten effects, which a person listened to and passed: the
same generators and seeds give the lengths the spike measured, to the millisecond.

## A jingle as one

**An arrangement is effects at the times a game plays them** (§PW313). Played one by one
on a sitting, a jingle's parts are heard and the jingle is not: whether the boing is too
loud over the whistle, or the pops land on the beat. The same `*.sfx.toml` may say:

```toml
[arrangement.splash]
peak = -1.0              # the mix's ceiling in dBFS; -1 when left out
cues = [
  { effect = "splash_gather", at = 0.0 },
  { effect = "splash_pop", at = 0.40, pitch = 2 },
  { effect = "splash_pop", at = 0.55, pitch = 4, gain = -3 },
  { effect = "splash_boing", at = 1.2 },
]
```

`at` is seconds from the start, `pitch` semitones (played faster and shorter, as a game's
`pitch_scale` does) and `gain` dB. A cue naming an effect the file does not declare, with
no time, or with a key of its own is `sound.bad-effect`, naming the cue. `sound.synth`
mixes each arrangement after the effects, holds the mix under its `peak`, and places it as
an effect is placed: at the cue `[sound]` declares under the arrangement's name, or
beside the file. Its record names the arrangement and its cues, and the answer's
`arrangements` gives each one's `file`, `duration`, `peak`, `loudness` and
`ceiling_bound`.

**The game reads the times the person heard.** Beside the mix,
`<name>.arrangement.json` lists every cue with its effect's file, its time, pitch and
gain, so the code that plays the jingle reads them rather than repeating them. A person
hears the jingle on a sitting by naming the mix as a member beside its parts:
`sound.sitting` with `new` the mix, and one member per effect. A verdict on the mix covers
the balance and the timing, and `sound.measure` reads its summed peak.

## Bought effects

Footsteps, glass or rain are not what a synthesiser does well. `sound.buy` (a `fetch` job)
buys one from ElevenLabs' sound generation, through the doors `picture.buy` and
`mesh.buy` go through, in this order and with nothing sent until all of them pass:

1. the effect lands at a `cue` a `[sound]` family declares (`sound.unknown-cue` for one it
   does not), or at an `out` path with a sound's suffix;
2. the price is the service's `prices` row for the `model`
   (`eleven_text_to_sound_v2` by default), never the caller's figure, and a model with
   no row is refused (`fetch.unpriced`);
3. a cue in a format other than MP3 needs ffmpeg to transcode what the service answers,
   and is refused before spending where there is none (`sound.no-encoder`);
4. `purchase.allow` is asked against the service's own ceiling. **No budget means no
   spend**, and the ceiling is a person's, written into `[budget.<name>]`.

```toml
[service.elevenlabs]
base    = "https://api.elevenlabs.io"
key_env = "ELEVENLABS_API_KEY"
prices  = { "eleven_text_to_sound_v2" = 0.05 }   # per sound, in the ceiling's unit

[budget.elevenlabs]
amount  = 5.0
unit    = "USD"
expires = "2026-12-31"
```

The request is the words, the model, `influence` (0 to 1, how closely it follows them),
`seconds` (0.5 to 30, or the service's choice) and `loop` for a sound that repeats, such as
rain. The answer is transcoded to the cue's format where it is not MP3, then captured
before anything else: written, hashed and ledgered as a `sound`, with the service's
request id as its task. The answer is the ledger entry, the `file` and what it measures.

## A line spoken aloud

The effects model makes a sound from a description and does not reliably say a given
line, so a studio tag read aloud has its own operation (§PW314). `sound.speak` (a `fetch`
job) sends `text`, word for word, to ElevenLabs' text to speech in the `voice` named, a
service voice id, through the same four doors as `sound.buy`. A missing text or voice is
`fetch.missing-field`, before anything is priced.

Speech is billed by the character, so its `prices` row is one by the character
(fetching.md, §PW320): the line is counted, the price is the count times the rate, and
the spend is read off the service's usage where it answers it.

```toml
prices = { "eleven_multilingual_v2" = { per = "character", rate = 0.0003 } }
```

The delivery is the voice's own unless the call sets it: `stability`, `similarity` and
`style` (0 to 1) and `speed` (0.7 to 1.2), sent as the service's `voice_settings`. The
take is captured as a `sound`, and its record keeps the words, the voice, the model and
the delivery set, so the same line can be made again. `entity=<id>` speaks in the voice
the world gives that entity instead of a `voice` the call names (world.md, §PW321).

## A take that says its line

A speech service drops words, adds breaths and pads silence, so a take is measured
against its line before a person hears it (§PW323). `sound.speech(take, text=)` (the
words from the take's record where `text` is unset) answers:

- `lead_silence` and `tail_silence`: seconds before the first frame within 40 dB of the
  take's loudest, judged over 20 ms frames, and after the last, which the game would play
  as a pause;
- `rate`: the line's characters, spaces left out, per second between them, so a skipped
  phrase reads fast and a repeated one slow;
- `loudness`, as `sound.measure` gives it, and `duration`;
- `said`: where faster-whisper is installed, what a local transcription heard, with the
  line's words it `missing` and those it heard `extra`, the world's names passed as the
  words to expect, since an invented name is what a service misreads. It runs locally
  because paying a service to check a take is spending on the agent's own judgement;
  where it is not installed `said` is null and `unheard` says why.

`failed` names each measure outside the project's `[voice]` bound: `lead_silence` and
`tail_silence` as maxima, `rate` and `loudness` as `[low, high]` bands, and `said` where
the words differ. Zero or an empty band bounds nothing, since the numbers are the
game's. `sound.speak` and `voice.lines` answer the same `speech` with each take, and a
sound sitting member given its `line` shows the measures on its sheet and is marked as
failing where any bound fails. A failing take is kept and reported, never bought again:
whether to spend on another is the person's ceiling.
