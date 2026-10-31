"""The notes of a GitHub release, beside the PyPI upload of the same tag (§PW662).

    python tools/release_notes.py v0.2.0 > notes.md

publish.yml runs this once PyPI has the version, and makes the release with the wheel
and the sdist attached, so the repository's Releases page lists what PyPI does: with no
release, a visitor from the marketplace read the project as never shipped. The notes
are what docs/CHANGELOG.md gained since the tag before, one entry a line, under the
install line and the one sentence on why the package is not named `polyweave`.

A tag published before the workflow made releases is backfilled by hand, once:

    python tools/release_notes.py v0.1.0 > notes.md
    gh release create v0.1.0 --verify-tag --title "polyweave-gamekit 0.1.0" \\
        --notes-file notes.md dist/*
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = "docs/CHANGELOG.md"
#: How a shipped entry opens in the changelog roadkeep writes.
SHIPPED = "- ✅ "


def git(*args: str) -> str:
    done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", check=False)
    return done.stdout if done.returncode == 0 else ""


def previous(tag: str) -> str:
    """The version tag before `tag`, or "" where it is the first."""
    return git("describe", "--tags", "--abbrev=0", "--match", "v*", f"{tag}^").strip()


def entries(diff: str) -> list[str]:
    """The shipped entries a changelog diff adds, each as the changelog spells it."""
    return [line[1:] for line in diff.splitlines()
            if line.startswith("+" + SHIPPED)]


def notes(tag: str, before: str, added: list[str]) -> str:
    version = tag.removeprefix("v")
    lines = [
        "```", f"pip install polyweave-gamekit=={version}", "```", "",
        "On PyPI the package is `polyweave-gamekit`: `polyweave` there is an "
        "unrelated project. The import, the `polyweave` command and the plugin keep "
        "the short name.",
        "",
    ]
    if not before:
        lines.append(f"The first release. What it holds is in [{CHANGELOG}]"
                     f"(https://github.com/alegauss/polyweave/blob/{tag}/{CHANGELOG}).")
    elif added:
        lines += [f"## Since {before}", "", *added]
    else:
        lines.append(f"No entry shipped since {before}.")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 1 or not argv[0].startswith("v"):
        print("usage: release_notes.py v<version>", file=sys.stderr)
        return 2
    tag = argv[0]
    before = previous(tag)
    added = entries(git("diff", f"{before}..{tag}", "--", CHANGELOG)) if before else []
    sys.stdout.write(notes(tag, before, added))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
