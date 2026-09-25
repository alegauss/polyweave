"""The declaration is the source, and the guard says so (§PW133).

A built mesh or voxel file is derived from its declaration, as a roadmap line is derived
from its fields, so an agent editing the output by hand makes a file that no longer
follows its source, and the build stamp, which hashes inputs, keeps calling it cached.
This hook holds the rule where it is broken rather than in a sentence:

    guard.py pre     PreToolUse: deny an edit to a built or recorded file, naming the
                     declaration and the build to run instead; `ask` for a shell
                     command that names one, since nobody parses what it writes
    guard.py start   SessionStart: mark when the session began
    guard.py stop    Stop: every recorded artefact touched since then that no longer
                     matches its record blocks the stop, with the file named

Standard library only, so numpy and Blender are never loaded to decide a write, and any
failure inside allows the edit: a guard that breaks must never break the session.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import sys
import time
from pathlib import Path

EDITS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
STAMP = ".build.json"
RECORD = ".prov.json"
MARK = Path(".polyweave") / "session-start"


def _stamped(target: Path) -> dict | None:
    """The build stamp beside `target` that lists it as an output, if any."""
    for stamp in target.parent.glob(f"*{STAMP}"):
        try:
            said = json.loads(stamp.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        outputs = {str(Path(one).resolve()) for one in said.get("outputs", ())}
        if str(target.resolve()) in outputs:
            return said
    return None


def _recorded(target: Path) -> dict | None:
    sidecar = target.with_name(target.name + RECORD)
    try:
        return json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def why_derived(target: Path) -> str | None:
    """Why `target` must not be edited by hand, or None when it may be."""
    stamp = _stamped(target)
    if stamp is not None:
        source = stamp.get("source") or "its declaration"
        return (
            f"{target.name} is built from {source}: change that, then run "
            f"`python -m polyweave geometry.build --source {source}`"
        )
    record = _recorded(target)
    if record is not None:
        kind = record.get("kind", "an operation")
        return (
            f"{target.name} was made by {kind} and carries a record beside it: change "
            "what made it and make it again, so the record stays true"
        )
    return None


def _decide(decision: str, reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": decision,
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


def pre(event: dict) -> None:
    tool = event.get("tool_name", "")
    given = event.get("tool_input") or {}
    root = Path(event.get("cwd") or ".")
    if tool in EDITS:
        named = given.get("file_path") or given.get("notebook_path")
        if not named:
            return
        target = Path(named)
        target = target if target.is_absolute() else root / target
        reason = why_derived(target) if target.is_file() else None
        if reason:
            _decide("deny", reason)
    elif tool == "Bash":
        try:
            words = shlex.split(given.get("command", ""), posix=True)
        except ValueError:
            return
        for word in words:
            target = Path(word) if Path(word).is_absolute() else root / word
            if len(word) < 260 and target.suffix and target.is_file():
                reason = why_derived(target)
                if reason:
                    _decide("ask", f"this command names a derived file. {reason}")
                    return


def start(event: dict) -> None:
    mark = Path(event.get("cwd") or ".") / MARK
    mark.parent.mkdir(parents=True, exist_ok=True)
    mark.write_text(str(time.time()), encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def stop(event: dict) -> None:
    root = Path(event.get("cwd") or ".")
    if event.get("stop_hook_active"):
        return  # already continuing because of this hook; never loop
    try:
        since = float((root / MARK).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    drifted = []
    for sidecar in root.rglob(f"*{RECORD}"):
        if ".polyweave" in sidecar.parts:
            continue
        artefact = sidecar.with_name(sidecar.name[: -len(RECORD)])
        if not artefact.is_file() or artefact.stat().st_mtime < since:
            continue
        try:
            said = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if (said.get("artefact") or {}).get("sha256") not in (None, _sha256(artefact)):
            drifted.append(artefact.relative_to(root).as_posix())
    if drifted:
        print(
            json.dumps(
                {
                    "decision": "block",
                    "reason": "these no longer match the record beside them, so "
                    "something edited them by hand: "
                    + ", ".join(sorted(drifted))
                    + ". Make them again from their source.",
                }
            )
        )


def main(argv: list[str]) -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
        {"pre": pre, "start": start, "stop": stop}[argv[1]](event)
    except Exception:  # noqa: BLE001 - a guard that breaks allows the edit
        return 0
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    sys.exit(main(sys.argv))
