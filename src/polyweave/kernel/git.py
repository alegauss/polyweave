"""A committed version of a file, read back out of git (§PW425, §PW481).

A render rewrites its file in place, so what a person compares a new take or picture
against often exists only in git. Any layer that lays out a comparison reads it here.
"""

from __future__ import annotations

import re
from pathlib import Path

from .errors import PolyweaveError

#: `<revision>:<path>`, a committed file; two characters at least before the colon, so
#: a Windows drive (`C:/...`) is never read as one.
_COMMITTED = re.compile(r"^(?P<rev>[\w.~^/@{}-]{2,}):(?P<path>[^:].*)$")

#: What a Git LFS pointer starts with, where the file itself is kept elsewhere.
_LFS = b"version https://git-lfs"


def committed(given: str) -> tuple[str, str] | None:
    """The revision and the path an `old` names, where it names a committed version."""
    found = _COMMITTED.match(given)
    return (found["rev"], found["path"]) if found else None


def checked_out(rev: str, path: str, here: Path, work: Path, kind: str = "sound",
                 code: str = "sound.no-source") -> tuple[str, dict]:
    """A committed version of a file, written into the work area to be compared
    (§PW425): a sound to be heard, or a picture to be looked at (§PW481).

    A render rewrites its file in place, so the version a person compares against lives
    only in git, and in a project that keeps audio in LFS as a pointer: spinhold took
    three commands a track to get one back. Answers where it landed and where it came
    from, the commit it resolved to, for the sitting to say.
    """
    import hashlib
    import subprocess

    def git(*args: str, given: bytes | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(["git", *args], cwd=here, input=given,
                              capture_output=True, check=False)

    shown = git("show", f"{rev}:{path}")
    commit = git("rev-parse", "--verify", f"{rev}^{{commit}}")
    if shown.returncode or commit.returncode:
        raise PolyweaveError(
            code,
            f"git has no {path} at {rev}",
            "name a revision and a path the repository holds, as HEAD:<path>",
            detail=(shown.stderr or commit.stderr).decode("utf-8", "replace")[:300],
            given=f"{rev}:{path}",
        )
    body = shown.stdout
    if body.startswith(_LFS):
        smudged = git("lfs", "smudge", path, given=body)
        if smudged.returncode or not smudged.stdout:
            raise PolyweaveError(
                code,
                f"{path} at {rev} is a Git LFS pointer, and git lfs could not fetch it",
                "install Git LFS and fetch the object (git lfs fetch), then ask again",
                detail=smudged.stderr.decode("utf-8", "replace")[:300],
            )
        body = smudged.stdout
    sha = commit.stdout.decode().strip()
    landed = work / kind / "old" / sha[:12] / path
    landed.parent.mkdir(parents=True, exist_ok=True)
    landed.write_bytes(body)
    from polyweave.kernel.provenance import relative

    return relative(landed, here), {
        "rev": rev, "commit": sha, "path": path,
        "sha256": hashlib.sha256(body).hexdigest(),
    }
