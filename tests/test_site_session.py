"""The site's session transcript runs real commands (§PW602).

The landing page shows an agent's session as a terminal, and a reader copies a line from
it. It once showed `polyweave accept`, `polyweave search` and `polyweave bake`, none of
which the command line had, under a note saying they were the fixed surface. Each line
here is parsed by the command line itself, and each failure code it shows is a code.
"""

from __future__ import annotations

import html
import re
import shlex
from pathlib import Path

from polyweave.kernel.errors import codes
from polyweave.surface.cli import command_line

DIAGRAMS = Path(__file__).parents[1] / "site" / "src" / "lib" / "diagrams.ts"


def _session() -> str:
    source = DIAGRAMS.read_text("utf-8")
    body = source.split("export const sessionTerminal = `", 1)[1].split("`;", 1)[0]
    return html.unescape(re.sub(r"<[^>]+>", "", body))


def test_every_command_in_the_session_parses():
    commands = [
        line.removeprefix("> polyweave ")
        for line in _session().splitlines()
        if line.startswith("> polyweave ")
    ]
    assert len(commands) >= 4
    parser = command_line()
    for command in commands:
        parser.parse_args(shlex.split(command))


def test_every_failure_it_shows_is_a_code():
    shown = re.findall(r"^  ([a-z]+\.[a-z-]+): ", _session(), re.MULTILINE)
    assert shown
    assert set(shown) <= set(codes())
