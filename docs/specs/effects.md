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
peak         = -3.0        # the dBFS the effect is normalised to
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
`declared`, and its `duration`, `peak` and `loudness`, measured here since a one-shot is
shorter than `sound.measure`'s seam window.

The port is held to the spike's ten effects, which a person listened to and passed: the
same generators and seeds give the lengths the spike measured, to the millisecond.
