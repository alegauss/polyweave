"""What must be true of a file that arrived over the network.

A truncated download is a mesh that loads with half its faces, and the failure surfaces
wherever that mesh is next used rather than where the bytes went missing.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ..errors import PolyweaveError

ACCEPTS_DOWNLOAD = frozenset({"declared_length", "sha256"})

_CHUNK = 1 << 20


def check_download(
    subject: Any,
    *,
    declared_length: int | None = None,
    sha256: str | None = None,
) -> dict:
    """Byte length matches the declared length, and the digest is recorded."""
    if isinstance(subject, bytes | bytearray):
        length = len(subject)
        digest = hashlib.sha256(subject).hexdigest()
        where = "the response body"
    else:
        path = Path(subject)
        if not path.is_file():
            raise PolyweaveError(
                "post.file-missing",
                f"nothing was written to {path}",
                "the transfer never started; check the service's response before "
                "spending the credit again",
            )
        hasher = hashlib.sha256()
        length = 0
        with open(path, "rb") as fh:
            while chunk := fh.read(_CHUNK):
                hasher.update(chunk)
                length += len(chunk)
        digest = hasher.hexdigest()
        where = str(path)

    if declared_length is not None and length != int(declared_length):
        short = int(declared_length) - length
        raise PolyweaveError(
            "post.download-length",
            f"{where} holds {length} bytes and the response declared "
            f"{int(declared_length)}",
            f"the transfer stopped {short} bytes early; download it again rather than "
            f"reading it"
            if short > 0
            else "the response declared fewer bytes than arrived; the length header is "
            "wrong, so verify the digest before trusting the file",
        )
    if sha256 is not None and digest != sha256.lower():
        raise PolyweaveError(
            "post.download-digest",
            f"{where} hashes to {digest[:12]}… and {sha256.lower()[:12]}… was expected",
            "the bytes are not the ones that were promised; download it again, and if "
            "it differs a second time the service is serving something else",
        )
    return {"bytes": length, "sha256": digest}
