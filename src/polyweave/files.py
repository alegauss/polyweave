"""Writing a file that another process may be reading at the same time.

Two things here, and both exist because state this plugin keeps is read across
processes: a job record polled from another session, a cache entry read while a worker
writes one.

Neither is interesting. Both are wrong often enough on Windows to be worth having in one
place rather than in each of the modules that needs them.
"""

from __future__ import annotations

import os
import secrets
import time
from pathlib import Path


def write_atomic(path: Path, text: str, attempts: int = 10) -> None:
    """Replace `path` in one step, so a concurrent reader sees one version or the other.

    The temporary lands in the same directory because `os.replace` is only atomic within
    a filesystem. The retry is Windows: a file another process has open cannot be
    replaced there, and a worker reporting a stage loses that race often enough to
    matter.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{secrets.token_hex(3)}.tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        for attempt in range(attempts):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                if attempt == attempts - 1:
                    raise
                time.sleep(0.01 * (attempt + 1))
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def read_text_retrying(path: Path, attempts: int = 5) -> str | None:
    """Read `path`, tolerating the moment another process is replacing it.

    On Windows a reader that opens a file mid-replace gets a sharing violation rather
    than either version, so a read that would otherwise be atomic needs a retry.
    """
    for attempt in range(attempts):
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(0.02 * (attempt + 1))
    return None
