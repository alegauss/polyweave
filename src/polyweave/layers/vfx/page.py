"""The vfx layer's part of the brief: an effect and what it measures (§PW505)."""

from __future__ import annotations

from pathlib import Path

from polyweave.kernel.errors import PolyweaveError


def read(item: dict, record: dict, here: Path) -> dict | None:
    """An effect in the brief, as its table declares it and as a build measures it."""
    from polyweave.loop import declared

    from . import vfx

    path = item["declaration"]
    if not path or not path.endswith(".toml"):
        return None
    try:
        answer = declared._effect(item, path, record, here)
        if "table" in answer:
            answer["measures"] = vfx.measured_whole(
                vfx.declared(answer["effect"], answer["table"], here))
    except PolyweaveError as refused:
        return {"path": path, "refused": refused.as_dict()}
    return answer
