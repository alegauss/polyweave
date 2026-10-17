"""Reading an image into an array, in one place.

Every check and every measurement asks the same two questions first — how big is it, and
which pixels are the subject — so they ask them here. Block B's vocabulary is built on
this loader rather than beside it.

Colour is sRGB, 8 bits per channel, exactly as `docs/specs/tool-surface.md` §6 fixes it.
Linear values belong inside a renderer and never in an interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image as PILImage
from PIL import UnidentifiedImageError

from .errors import PolyweaveError


@dataclass(frozen=True)
class Image:
    """An image as an `(h, w, 4)` array of bytes, plus what it was before conversion."""

    path: Path | None
    rgba: np.ndarray
    had_alpha: bool

    @property
    def width(self) -> int:
        return int(self.rgba.shape[1])

    @property
    def height(self) -> int:
        return int(self.rgba.shape[0])

    @property
    def size(self) -> tuple[int, int]:
        return (self.width, self.height)

    @property
    def alpha(self) -> np.ndarray:
        return self.rgba[:, :, 3]

    def subject(self, alpha_floor: float) -> np.ndarray:
        """The mask of pixels that are the asset rather than the background.

        `alpha_floor` is a fraction of one, matching `[tolerance] alpha_floor`, and it
        is **required**: a default here would be a second home for a number that has
        one (§PW40), and the one it had was zero where the config said 0.02 — so a
        caller who forgot measured the background as part of the subject and nothing
        said so. An image that never had an alpha channel is all subject either way.
        """
        if not self.had_alpha:
            return np.ones(self.rgba.shape[:2], dtype=bool)
        return self.alpha > round(alpha_floor * 255)


def load(source: str | Path) -> Image:
    """Open `source` as an image, or refuse with a code saying which door is shut."""
    path = Path(source)
    if not path.exists():
        raise PolyweaveError(
            "post.file-missing",
            f"there is no file at {path}",
            "check the path, or read the job's log for what the operation wrote",
        )
    try:
        with PILImage.open(path) as opened:
            had_alpha = opened.mode in ("RGBA", "LA", "PA") or "transparency" in (
                opened.info or {}
            )
            rgba = np.asarray(opened.convert("RGBA"), dtype=np.uint8)
    except UnidentifiedImageError as exc:
        raise PolyweaveError(
            "post.not-an-image",
            f"{path} is not in any image format this can read",
            "check that the operation wrote what it said it wrote, and to this path",
            detail=str(exc),
        ) from exc
    except OSError as exc:
        raise PolyweaveError(
            "post.unreadable",
            f"{path} could not be read to the end",
            "the file is truncated or still being written; run the operation again",
            detail=str(exc),
        ) from exc
    return Image(path=path, rgba=rgba, had_alpha=had_alpha)
