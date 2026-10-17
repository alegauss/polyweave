"""The review page is the window's decision screen, built and committed (§PW403).

`python -m polyweave review` serves src/polyweave/loop/review_page/screen, which
`npm run build:review` in gui/ builds from the screen's sources. The bundle is committed
so the page needs Python alone; this is what keeps it from going stale behind them, as
tests/test_operations_ts.py does for the SDK.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from polyweave.loop import review

REPO = Path(__file__).parents[1]


def digest(sources: list[str]) -> str:
    """The sources' digest as the build computes it, line endings read as LF."""
    hashed = hashlib.sha256()
    for path in sorted(sources):
        hashed.update(path.encode() + b"\0")
        text = (REPO / path).read_text(encoding="utf-8").replace("\r\n", "\n")
        hashed.update(text.encode() + b"\0")
    return hashed.hexdigest()


def test_the_committed_screen_is_built_from_its_sources_as_they_are():
    stamp = json.loads((review.SCREEN / "stamp.json").read_text(encoding="utf-8"))
    assert digest(stamp["sources"]) == stamp["sha256"], (
        "the review page is older than the screen it is built from: "
        + stamp["rebuild"]
    )


def test_the_stamp_names_every_source_the_screen_is_made_of():
    stamp = json.loads((review.SCREEN / "stamp.json").read_text(encoding="utf-8"))
    for one in ("gui/packages/ui/src/Decide.tsx", "gui/packages/ui/src/Advanced.tsx",
                "gui/packages/ui/src/review.tsx", "gui/packages/core/src/desk.ts"):
        assert one in stamp["sources"]


def test_the_page_runs_the_screen_and_nothing_else():
    page = (review.SCREEN / "index.html").read_text(encoding="utf-8")
    assert "./review.js" in page
    assert not (review.PAGE / "page.js").exists()
