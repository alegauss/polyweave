"""Writes a tone and reads its pitch and length back."""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

from polyweave.kernel.errors import PolyweaveError

RATE = 8000


def write(path: Path, *, pitch: float, seconds: float, shape: str = "sine") -> Path:
    if not 20 <= pitch <= 20_000:
        raise PolyweaveError(
            "tone.bad-pitch",
            f"a tone at {pitch} Hz is outside what a person hears",
            "declare a pitch between 20 and 20000",
            given=str(pitch),
        )
    frames = []
    for i in range(int(RATE * seconds)):
        value = math.sin(2 * math.pi * pitch * i / RATE)
        if shape == "square":
            value = 1.0 if value >= 0 else -1.0
        frames.append(struct.pack("<h", int(value * 20_000)))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(b"".join(frames))
    return path


def read(path: Path) -> dict:
    with wave.open(str(path), "rb") as one:
        count = one.getnframes()
        values = struct.unpack(f"<{count}h", one.readframes(count))
    rising = sum(1 for a, b in zip(values, values[1:], strict=False) if a < 0 <= b)
    seconds = count / RATE
    return {"pitch_hz": rising / seconds if seconds else 0.0, "tone_seconds": seconds}
