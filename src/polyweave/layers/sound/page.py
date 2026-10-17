"""The sound layer's part of the brief: a cue as music.validate says it (§PW505)."""

from __future__ import annotations

from pathlib import Path

from polyweave.kernel.errors import PolyweaveError


def music(item: dict, record: dict, here: Path) -> dict | None:
    """A music cue in the brief, as music.validate reads its source."""
    from . import music as score

    path = item["declaration"]
    if not path:
        return None
    try:
        return {"path": path, **score.validate(path, root=str(here))}
    except PolyweaveError as refused:
        return {"path": path, "refused": refused.as_dict()}
