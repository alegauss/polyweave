"""The fixture layer's one operation."""

from __future__ import annotations

import tomllib
from typing import Annotated

from polyweave.kernel import provenance
from polyweave.kernel.config import load
from polyweave.kernel.describe import Param, operation

from . import wave


@operation("tone.make")
def make(
    declaration: Annotated[str, Param("the .tone.toml naming the pitch and length")],
    out: Annotated[str, Param("the wav to write")],
    *,
    root: Annotated[str, Param("the project the paths resolve against")] = ".",
) -> dict:
    """A tone written from its declaration and recorded with it as its source."""
    config = load(root)
    here = config.root
    said = tomllib.loads((here / declaration).read_text(encoding="utf-8"))
    pitch = float(said.get("pitch", config.get("tone.pitch")))
    seconds = float(said.get("seconds", config.get("tone.seconds")))
    written = wave.write(here / out, pitch=pitch, seconds=seconds,
                         shape=config.get("tone.wave"))
    record = provenance.build(
        "tone", written, root=here,
        inputs=[provenance.source("tone-source", here / declaration, here)],
    )
    record["details"] = {"pitch": pitch}
    provenance.write(record, here)
    return {"artefact": str(written), "pitch": pitch, "seconds": seconds}
