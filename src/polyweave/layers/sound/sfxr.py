"""DrPetter's sfxr, seeded: its parameters, its synth loop and its generators (§PW189).

The generators are the original's, driven by `random.Random(seed)`, so one generator and
one seed are one sound forever, byte for byte. The synth is the original's loop: a
square, saw, sine or noise oscillator with a pitch slide, vibrato and arpeggio, an
attack-sustain-punch-decay envelope, a resonant low-pass, a high-pass and a phaser,
supersampled eight times. Output is mono floats at 44.1 kHz.

Pure Python and the standard library, like the rest of the package's core, so nothing
has to be installed to make an effect.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, fields

RATE = 44100

#: The four oscillators, by the number sfxr stores.
WAVES = {"square": 0, "saw": 1, "sine": 2, "noise": 3}

#: The longest effect the synth will write, in samples: a runaway envelope stops here.
LONGEST = RATE * 4


@dataclass
class Params:
    """sfxr's parameters. `wave` is 0-3; the rest are 0 to 1, or -1 to 1 for a ramp."""

    wave: int = 0
    base_freq: float = 0.3
    freq_limit: float = 0.0
    freq_ramp: float = 0.0
    freq_dramp: float = 0.0
    duty: float = 0.0
    duty_ramp: float = 0.0
    vib_strength: float = 0.0
    vib_speed: float = 0.0
    env_attack: float = 0.0
    env_sustain: float = 0.3
    env_punch: float = 0.0
    env_decay: float = 0.4
    lpf_resonance: float = 0.0
    lpf_freq: float = 1.0
    lpf_ramp: float = 0.0
    hpf_freq: float = 0.0
    hpf_ramp: float = 0.0
    pha_offset: float = 0.0
    pha_ramp: float = 0.0
    repeat_speed: float = 0.0
    arp_speed: float = 0.0
    arp_mod: float = 0.0


#: The parameters that may run negative, which is how sfxr says down rather than up.
SIGNED = frozenset({"freq_ramp", "freq_dramp", "duty_ramp", "lpf_ramp", "hpf_ramp",
                    "pha_offset", "pha_ramp", "arp_mod"})

NAMES = tuple(f.name for f in fields(Params))


class _State:
    """The synth's running state, reset whole at the start and in part on a repeat."""

    def __init__(self, p: Params, noise: random.Random):
        self.p, self.noise = p, noise
        self.reset(restart=False)

    def reset(self, restart: bool) -> None:
        p = self.p
        self.fperiod = 100.0 / (p.base_freq**2 + 0.001)
        self.fmaxperiod = 100.0 / (p.freq_limit**2 + 0.001)
        self.fslide = 1.0 - p.freq_ramp**3 * 0.01
        self.fdslide = -(p.freq_dramp**3) * 0.000001
        self.duty = 0.5 - p.duty * 0.5
        self.duty_slide = -p.duty_ramp * 0.00005
        if p.arp_mod >= 0:
            self.arp_mod = 1.0 - p.arp_mod**2 * 0.9
        else:
            self.arp_mod = 1.0 + p.arp_mod**2 * 10.0
        self.arp_time = 0
        self.arp_limit = (
            0 if p.arp_speed == 1.0 else int((1.0 - p.arp_speed) ** 2 * 20000 + 32)
        )
        if restart:
            return
        self.phase = 0
        self.fltp = self.fltdp = self.fltphp = 0.0
        self.fltw = p.lpf_freq**3 * 0.1
        self.fltw_d = 1.0 + p.lpf_ramp * 0.0001
        damping = 5.0 / (1.0 + p.lpf_resonance**2 * 20.0) * (0.01 + self.fltw)
        self.fltdmp = min(0.8, damping)
        self.flthp = p.hpf_freq**2 * 0.1
        self.flthp_d = 1.0 + p.hpf_ramp * 0.0003
        self.vib_phase = 0.0
        self.vib_speed = p.vib_speed**2 * 0.01
        self.vib_amp = p.vib_strength * 0.5
        self.env_stage = self.env_time = 0
        self.env_length = [
            int(p.env_attack**2 * 100000),
            int(p.env_sustain**2 * 100000),
            int(p.env_decay**2 * 100000),
        ]
        self.fphase = math.copysign(p.pha_offset**2 * 1020.0, p.pha_offset)
        self.fdphase = math.copysign(p.pha_ramp**2, p.pha_ramp)
        self.ipp = 0
        self.phaser = [0.0] * 1024
        self.noise_buffer = [self.noise.uniform(-1, 1) for _ in range(32)]
        self.rep_time = 0
        self.rep_limit = (
            0 if p.repeat_speed == 0 else int((1.0 - p.repeat_speed) ** 2 * 20000 + 32)
        )


def synth(p: Params, seed: int = 0) -> list[float]:
    """The samples of one effect, from its parameters; `seed` drives only its noise."""
    s = _State(p, random.Random(seed))
    out: list[float] = []
    while len(out) < LONGEST:
        sample = _step(s)
        if sample is None:
            break
        out.append(sample)
    return out


def _step(s: _State) -> float | None:
    """One output sample, or None when the effect has ended."""
    p = s.p
    s.rep_time += 1
    if s.rep_limit and s.rep_time >= s.rep_limit:
        s.rep_time = 0
        s.reset(restart=True)
    s.arp_time += 1
    if s.arp_limit and s.arp_time >= s.arp_limit:
        s.arp_limit = 0
        s.fperiod *= s.arp_mod
    s.fslide += s.fdslide
    s.fperiod *= s.fslide
    if s.fperiod > s.fmaxperiod:
        s.fperiod = s.fmaxperiod
        if p.freq_limit > 0:
            return None
    period = s.fperiod
    if s.vib_amp > 0:
        s.vib_phase += s.vib_speed
        period = s.fperiod * (1.0 + math.sin(s.vib_phase) * s.vib_amp)
    period = max(8, int(period))
    s.duty = min(0.5, max(0.0, s.duty + s.duty_slide))
    s.env_time += 1
    while s.env_time > s.env_length[s.env_stage]:
        s.env_time = 0
        s.env_stage += 1
        if s.env_stage == 3:
            return None
    length = max(1, s.env_length[s.env_stage])
    if s.env_stage == 0:
        env = s.env_time / length
    elif s.env_stage == 1:
        env = 1.0 + (1.0 - s.env_time / length) * 2.0 * p.env_punch
    else:
        env = 1.0 - s.env_time / length
    s.fphase += s.fdphase
    iphase = min(1023, abs(int(s.fphase)))
    if s.flthp_d != 0:
        s.flthp = min(0.1, max(0.00001, s.flthp * s.flthp_d))
    total = 0.0
    for _ in range(8):
        total += _oscillate(s, period, iphase) * env
    return max(-1.0, min(1.0, total / 8.0))


def _oscillate(s: _State, period: int, iphase: int) -> float:
    """One supersample: the oscillator, the two filters and the phaser."""
    p = s.p
    s.phase += 1
    if s.phase >= period:
        s.phase %= period
        if p.wave == 3:
            s.noise_buffer = [s.noise.uniform(-1, 1) for _ in range(32)]
    fp = s.phase / period
    if p.wave == 0:
        sample = 0.5 if fp < s.duty else -0.5
    elif p.wave == 1:
        sample = 1.0 - fp * 2.0
    elif p.wave == 2:
        sample = math.sin(fp * 2.0 * math.pi)
    else:
        sample = s.noise_buffer[s.phase * 32 // period]
    before = s.fltp
    s.fltw = min(0.1, max(0.0, s.fltw * s.fltw_d))
    if p.lpf_freq != 1.0:
        s.fltdp += (sample - s.fltp) * s.fltw
        s.fltdp -= s.fltdp * s.fltdmp
    else:
        s.fltp, s.fltdp = sample, 0.0
    s.fltp += s.fltdp
    s.fltphp += s.fltp - before
    s.fltphp -= s.fltphp * s.flthp
    sample = s.fltphp
    s.phaser[s.ipp & 1023] = sample
    sample += s.phaser[(s.ipp - iphase + 1024) & 1023]
    s.ipp = (s.ipp + 1) & 1023
    return sample


# ------------------------------------------------------------ the original generators


def _pickup(r: random.Random) -> Params:
    p = Params(base_freq=0.4 + r.random() * 0.5, env_sustain=r.random() * 0.1,
               env_decay=0.1 + r.random() * 0.4, env_punch=0.3 + r.random() * 0.3)
    if r.randint(0, 1):
        p.arp_speed = 0.5 + r.random() * 0.2
        p.arp_mod = 0.2 + r.random() * 0.4
    return p


def _laser(r: random.Random) -> Params:
    p = Params(wave=r.randint(0, 2))
    if p.wave == 2 and r.randint(0, 1):
        p.wave = r.randint(0, 1)
    p.base_freq = 0.5 + r.random() * 0.5
    p.freq_limit = max(0.2, p.base_freq - 0.2 - r.random() * 0.6)
    p.freq_ramp = -0.15 - r.random() * 0.2
    if r.randint(0, 2) == 0:
        p.base_freq = 0.3 + r.random() * 0.6
        p.freq_limit = r.random() * 0.1
        p.freq_ramp = -0.35 - r.random() * 0.3
    if r.randint(0, 1):
        p.duty, p.duty_ramp = r.random() * 0.5, r.random() * 0.2
    else:
        p.duty, p.duty_ramp = 0.4 + r.random() * 0.5, -r.random() * 0.7
    p.env_sustain = 0.1 + r.random() * 0.2
    p.env_decay = r.random() * 0.4
    if r.randint(0, 1):
        p.env_punch = r.random() * 0.3
    if r.randint(0, 2) == 0:
        p.pha_offset, p.pha_ramp = r.random() * 0.2, -r.random() * 0.2
    if r.randint(0, 1):
        p.hpf_freq = r.random() * 0.3
    return p


def _explosion(r: random.Random) -> Params:
    p = Params(wave=3)
    if r.randint(0, 1):
        p.base_freq, p.freq_ramp = 0.1 + r.random() * 0.4, -0.1 + r.random() * 0.4
    else:
        p.base_freq, p.freq_ramp = 0.2 + r.random() * 0.7, -0.2 - r.random() * 0.2
    p.base_freq *= p.base_freq
    if r.randint(0, 4) == 0:
        p.freq_ramp = 0.0
    if r.randint(0, 2) == 0:
        p.repeat_speed = 0.3 + r.random() * 0.5
    p.env_sustain = 0.1 + r.random() * 0.3
    p.env_decay = r.random() * 0.5
    if r.randint(0, 1) == 0:
        p.pha_offset, p.pha_ramp = -0.3 + r.random() * 0.9, -r.random() * 0.3
    p.env_punch = 0.2 + r.random() * 0.6
    if r.randint(0, 1):
        p.vib_strength, p.vib_speed = r.random() * 0.7, r.random() * 0.6
    if r.randint(0, 2) == 0:
        p.arp_speed, p.arp_mod = 0.6 + r.random() * 0.3, 0.8 - r.random() * 1.6
    return p


def _powerup(r: random.Random) -> Params:
    p = Params()
    if r.randint(0, 1):
        p.wave = 1
    else:
        p.duty = r.random() * 0.6
    if r.randint(0, 1):
        p.base_freq, p.freq_ramp = 0.2 + r.random() * 0.3, 0.1 + r.random() * 0.4
        p.repeat_speed = 0.4 + r.random() * 0.4
    else:
        p.base_freq, p.freq_ramp = 0.2 + r.random() * 0.3, 0.05 + r.random() * 0.2
        if r.randint(0, 1):
            p.vib_strength, p.vib_speed = r.random() * 0.7, r.random() * 0.6
    p.env_sustain = r.random() * 0.4
    p.env_decay = 0.1 + r.random() * 0.4
    return p


def _hit(r: random.Random) -> Params:
    p = Params(wave=r.randint(0, 2))
    if p.wave == 2:
        p.wave = 3
    if p.wave == 0:
        p.duty = r.random() * 0.6
    p.base_freq = 0.2 + r.random() * 0.6
    p.freq_ramp = -0.3 - r.random() * 0.4
    p.env_sustain = r.random() * 0.1
    p.env_decay = 0.1 + r.random() * 0.2
    if r.randint(0, 1):
        p.hpf_freq = r.random() * 0.3
    return p


def _jump(r: random.Random) -> Params:
    p = Params(wave=0, duty=r.random() * 0.6, base_freq=0.3 + r.random() * 0.3,
               freq_ramp=0.1 + r.random() * 0.2, env_sustain=0.1 + r.random() * 0.3,
               env_decay=0.1 + r.random() * 0.2)
    if r.randint(0, 1):
        p.hpf_freq = r.random() * 0.3
    if r.randint(0, 1):
        p.lpf_freq = 1.0 - r.random() * 0.6
    return p


def _blip(r: random.Random) -> Params:
    p = Params(wave=r.randint(0, 1))
    if p.wave == 0:
        p.duty = r.random() * 0.6
    p.base_freq = 0.2 + r.random() * 0.4
    p.env_sustain = 0.1 + r.random() * 0.1
    p.env_decay = r.random() * 0.2
    p.hpf_freq = 0.1
    return p


#: sfxr's seven buttons, by the name a declaration uses.
GENERATORS = {
    "pickup": _pickup, "laser": _laser, "explosion": _explosion, "powerup": _powerup,
    "hit": _hit, "jump": _jump, "blip": _blip,
}


def drawn(generator: str, seed: int) -> Params:
    """What one generator draws from one seed: the same parameters every time."""
    return GENERATORS[generator](random.Random(seed))
