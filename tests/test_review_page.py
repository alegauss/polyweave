"""One local page to look at, and one call to answer from it (§PW172)."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

import pytest
from PIL import Image

from polyweave import review, verdict

SPEC = """asset = "{name}"

[[predicate]]
id      = "no-hot-facet"
measure = "luma_p99"
region  = "frame"
max     = {{ value = 0.37, origin = "margin", measured = 0.3438 }}
"""


def member(tmp_path, name, byte):
    (tmp_path / "accept").mkdir(exist_ok=True)
    (tmp_path / "renders").mkdir(exist_ok=True)
    (tmp_path / "accept" / f"{name}.accept.toml").write_text(
        SPEC.format(name=name), encoding="utf-8"
    )
    Image.new("RGBA", (24, 24), (byte, byte, byte, 255)).save(
        tmp_path / "renders" / f"{name}.png"
    )
    return {
        "name": name,
        "spec": f"accept/{name}.accept.toml",
        "new": f"renders/{name}.png",
    }


@pytest.fixture
def page(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    verdict.sitting(
        {"stars": [member(tmp_path, "star_dim", 200)]}, out="review", root=tmp_path
    )
    serving = review.server(tmp_path)
    threading.Thread(target=serving.serve_forever, daemon=True).start()
    host, port = serving.server_address[:2]
    yield f"http://{host}:{port}", tmp_path
    serving.shutdown()
    serving.server_close()


def get(url):
    with urllib.request.urlopen(url, timeout=10) as answer:
        return answer.status, answer.read(), answer.headers.get("Content-Type")


def post(url, body, asked=True):
    headers = {"Content-Type": "application/json"}
    if asked:
        headers[review.ASKED] = "1"
    request = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as answer:
            return answer.status, json.loads(answer.read())
    except urllib.error.HTTPError as refused:
        return refused.code, json.loads(refused.read())


def judged(**over):
    body = {
        "sitting": "review/sitting.json",
        "family": "stars",
        "choice": "number",
        "why": "same star at size",
    }
    return {**body, **over}


def test_it_listens_on_this_machine_alone(page):
    base, _ = page
    assert base.startswith("http://127.0.0.1:")


def test_the_page_and_its_script_ship_with_the_plugin(page):
    base, _ = page
    status, body, kind = get(base + "/")
    assert status == 200 and b"polyweave review" in body and kind == "text/html"
    assert get(base + "/page.js")[0] == 200


def test_the_state_is_what_is_on_disk(page):
    base, _ = page
    _, body, _ = get(base + "/api/state")
    found = json.loads(body)
    sitting = found["sittings"][0]
    assert sitting["manifest"] == "review/sitting.json"
    assert sitting["families"]["stars"]["sheet"] == "review/stars.png"
    assert sitting["families"]["stars"]["said"][0]["passed"] is False
    assert "says" in found["pending"]


def test_a_picture_is_served_and_nothing_outside_the_project_is(page):
    base, _ = page
    status, _, kind = get(base + "/file?path=review/stars.png")
    assert status == 200 and kind == "image/png"
    for outside in ("../../etc/passwd", "polyweave.toml"):
        with pytest.raises(urllib.error.HTTPError) as caught:
            get(base + "/file?path=" + outside)
        assert caught.value.code == 404


def test_the_one_write_is_a_verdict_and_it_moves_the_bound(page):
    base, where = page
    status, said = post(base + "/api/judge", judged())
    assert status == 200
    assert said["members"][0]["rewritten"] == ["no-hot-facet:max"]
    spec = (where / "accept" / "star_dim.accept.toml").read_text(encoding="utf-8")
    assert "same star at size" in spec


def test_a_post_another_site_could_make_is_refused(page):
    base, where = page
    status, _ = post(base + "/api/judge", judged(why="forged"), asked=False)
    assert status == 403
    spec = (where / "accept" / "star_dim.accept.toml").read_text(encoding="utf-8")
    assert "forged" not in spec


def test_an_answer_for_a_sitting_never_laid_out_is_refused(page):
    base, _ = page
    status, said = post(
        base + "/api/judge", judged(sitting="elsewhere/sitting.json", choice="accept")
    )
    assert status == 400 and said["code"] == "loop.unknown-sitting"


def test_the_command_line_has_the_verb():
    from polyweave.cli import command_line

    stated = command_line().parse_args(["review", "--port", "8765"])
    assert stated.command == "review" and stated.port == 8765
