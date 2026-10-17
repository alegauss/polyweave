"""The geometry layer's part of the brief and the review page (§PW505)."""

from __future__ import annotations

import json

from polyweave.kernel.config import load
from polyweave.kernel.files import read_text_retrying

from .shape import TURNTABLES


def turntables(root) -> list[dict]:
    """Every turntable laid out in this project, newest last (§PW176)."""
    config = load(root)
    index = config.path("paths.work") / TURNTABLES
    found = []
    for listed in json.loads(read_text_retrying(index) or "[]"):
        text = read_text_retrying(config.root / listed)
        if text is not None:
            found.append({"manifest": listed, **json.loads(text)})
    return found
