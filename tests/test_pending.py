"""A person's time asked for once, not once per family (§PW110)."""

from __future__ import annotations

from PIL import Image

from polyweave import loop, provenance, verdict

SPEC = """asset = "{name}"

[[predicate]]
id      = "no-hot-facet"
measure = "luma_p99"
region  = "frame"
max     = 0.9
"""


def asset(tmp_path, name, *, rendered_at=None):
    """A spec under the default specs folder, and a render record where one is asked."""
    specs = tmp_path / "docs" / "accept"
    specs.mkdir(parents=True, exist_ok=True)
    (specs / f"{name}.accept.toml").write_text(SPEC.format(name=name), encoding="utf-8")
    if rendered_at:
        renders = tmp_path / "docs" / "renders"
        renders.mkdir(parents=True, exist_ok=True)
        Image.new("RGBA", (8, 8), (90, 90, 90, 255)).save(renders / f"{name}.png")
        provenance.write(
            provenance.build(
                "render",
                renders / f"{name}.png",
                root=tmp_path,
                produced_at=rendered_at,
            ),
            root=tmp_path,
        )


def judged(tmp_path, name, *, at):
    run = loop.start(name, "after", root=tmp_path)
    loop.judged(run, tool_passed=True, person_accepted=True)
    run["verdicts"][-1]["at"] = at
    loop.finish(run, root=tmp_path)


def test_a_candidate_nobody_has_looked_at_waits(tmp_path):
    asset(tmp_path, "star_dim", rendered_at="2026-09-24T12:00:00Z")
    asset(tmp_path, "star_gold", rendered_at="2026-09-24T12:00:00Z")
    asset(tmp_path, "cloud")  # a spec and nothing made yet
    found = loop.pending(tmp_path)
    assert found["pending"] == ["star_dim", "star_gold"]
    assert "one sitting can take all of them" in found["says"]
    cloud = next(r for r in found["assets"] if r["asset"] == "cloud")
    assert cloud["spec"] == "docs/accept/cloud.accept.toml"
    assert cloud["candidate"] is None and not cloud["waiting"]


def test_a_verdict_given_after_the_render_clears_it(tmp_path):
    asset(tmp_path, "star_dim", rendered_at="2026-09-24T12:00:00Z")
    judged(tmp_path, "star_dim", at=1_900_000_000.0)  # 2030, after the render
    (row,) = loop.pending(tmp_path)["assets"]
    assert not row["waiting"]
    assert row["after"] is True and row["before"] is False
    assert row["judged"]


def test_a_render_newer_than_the_last_verdict_waits_again(tmp_path):
    asset(tmp_path, "star_dim", rendered_at="2026-09-24T12:00:00Z")
    judged(tmp_path, "star_dim", at=1_700_000_000.0)  # 2023, before the render
    assert loop.pending(tmp_path)["pending"] == ["star_dim"]


def test_nothing_waiting_says_so(tmp_path):
    asset(tmp_path, "cloud")
    assert loop.pending(tmp_path)["says"].startswith("0 asset(s) wait")


def test_every_pending_sheet_is_laid_out_in_one_sitting(tmp_path):
    asset(tmp_path, "star_dim", rendered_at="2026-09-24T12:00:00Z")
    asset(tmp_path, "star_gold", rendered_at="2026-09-24T12:00:00Z")
    families = {
        "stars": [
            {
                "name": name,
                "spec": f"docs/accept/{name}.accept.toml",
                "new": f"docs/renders/{name}.png",
            }
            for name in loop.pending(tmp_path)["pending"]
        ]
    }
    found = verdict.sitting(families, out="review", root=tmp_path)
    assert (tmp_path / "review" / "stars.png").is_file()
    assert [m["name"] for m in found["sheets"]["stars"]["members"]] == [
        "star_dim",
        "star_gold",
    ]
    assert "1 family to look at in one sitting" in found["says"]
