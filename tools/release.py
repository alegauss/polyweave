"""Release the next version to PyPI in one command (§PW602).

    python tools/release.py patch        0.1.0 -> 0.1.1
    python tools/release.py minor        0.1.0 -> 0.2.0
    python tools/release.py major        0.1.0 -> 1.0.0
    python tools/release.py 0.3.0        exactly that
    python tools/release.py patch --dry-run

The version lives in two files, `src/polyweave/__init__.py` and the plugin manifest,
which tests/test_packaging.py holds equal. This writes both, commits them, tags the
commit `v<version>` and pushes the branch and the tag together; the tag is what starts
.github/workflows/publish.yml, which publishes to TestPyPI and then to PyPI. A number
PyPI already holds can never be published again, so everything is checked first: on
main, a clean tree, nothing on origin that main lacks, and a tag that exists nowhere
yet. Local commits not yet pushed go up with the tag.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "polyweave" / "__init__.py"
MANIFEST = ROOT / "plugin" / ".claude-plugin" / "plugin.json"

VERSION = re.compile(r'^__version__ = "(\d+)\.(\d+)\.(\d+)"$', re.MULTILINE)
PARTS = ("major", "minor", "patch")


class Refused(Exception):
    """A release that must not go ahead, with the reason."""


def current() -> str:
    found = VERSION.search(PACKAGE.read_text(encoding="utf-8"))
    if not found:
        raise Refused(f"{PACKAGE} holds no __version__ = \"X.Y.Z\"")
    return ".".join(found.groups())


def bumped(version: str, asked: str) -> str:
    """The version after `asked`: a part to raise, or an exact X.Y.Z above `version`."""
    now = tuple(int(n) for n in version.split("."))
    if asked in PARTS:
        at = PARTS.index(asked)
        return ".".join(str(n) for n in (*now[:at], now[at] + 1, *([0] * (2 - at))))
    if not re.fullmatch(r"\d+\.\d+\.\d+", asked):
        raise Refused(f"{asked!r} is not patch, minor, major or a version X.Y.Z")
    if tuple(int(n) for n in asked.split(".")) <= now:
        raise Refused(f"{asked} is not above {version}, and PyPI takes a number once")
    return asked


def written(version: str) -> None:
    """The new version in both files, every other byte as it was."""
    text = PACKAGE.read_text(encoding="utf-8")
    PACKAGE.write_text(VERSION.sub(f'__version__ = "{version}"', text, count=1),
                       encoding="utf-8", newline="\n")
    manifest = MANIFEST.read_text(encoding="utf-8")
    replaced, count = re.subn(r'("version":\s*")[^"]+(")', rf"\g<1>{version}\g<2>",
                              manifest, count=1)
    if count != 1 or json.loads(replaced)["version"] != version:
        raise Refused(f"{MANIFEST} has no version to set")
    MANIFEST.write_text(replaced, encoding="utf-8", newline="\n")


def git(*args: str) -> str:
    done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          check=False)
    if done.returncode != 0:
        raise Refused(f"git {' '.join(args)}: {(done.stderr or done.stdout).strip()}")
    return done.stdout.strip()


def checked(tag: str) -> None:
    """Refuse a release from anywhere but a clean main in step with origin."""
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if branch != "main":
        raise Refused(f"on {branch}, and a release is made from main")
    if git("status", "--porcelain"):
        raise Refused("the tree has changes; commit or set them aside first")
    git("fetch", "--quiet", "--tags", "origin")
    # Ahead is fine, since the push takes main with the tag; behind or apart is not.
    try:
        git("merge-base", "--is-ancestor", "origin/main", "HEAD")
    except Refused:
        raise Refused("origin/main has commits main does not; pull first") from None
    if git("tag", "--list", tag):
        raise Refused(f"the tag {tag} already exists")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("bump", help="patch, minor, major, or an exact X.Y.Z")
    parser.add_argument("--dry-run", action="store_true",
                        help="say what would happen, writing and pushing nothing")
    args = parser.parse_args(argv)
    try:
        was = current()
        version = bumped(was, args.bump)
        tag = f"v{version}"
        checked(tag)
        if args.dry_run:
            print(f"release: would take {was} to {version}, commit, tag {tag} and push")
            return 0
        written(version)
        git("add", "--", *(str(p.relative_to(ROOT)) for p in (PACKAGE, MANIFEST)))
        git("commit", "--quiet", "-m", f"chore(release): polyweave-gamekit {version}")
        git("tag", "-a", tag, "-m", f"polyweave-gamekit {version}")
        git("push", "--atomic", "origin", "main", tag)
    except Refused as refused:
        print(f"release: {refused}", file=sys.stderr)
        return 1
    print(f"release: {was} -> {version}, tag {tag} pushed; publish.yml takes it to "
          "TestPyPI and then PyPI (gh run watch to follow it)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
