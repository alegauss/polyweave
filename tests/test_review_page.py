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


# -- an answer the agent can wait on (§PW173) ----------------------------------------


def test_an_answer_on_the_page_is_an_event_on_disk(page):
    base, where = page
    post(base + "/api/judge", judged(choice="accept", why="that is the star"))
    lines = (where / ".polyweave" / "answers.jsonl").read_text(encoding="utf-8")
    one = json.loads(lines.splitlines()[-1])
    assert one["family"] == "stars" and one["why"] == "that is the star"
    assert one["members"][0]["person_accepted"] is True


def test_the_agent_resumes_from_what_was_said_and_carries_it_into_its_run(page):
    from polyweave import loop

    base, where = page
    first = verdict.answers(root=where)
    assert first["answers"] == []
    post(base + "/api/judge", judged())
    run = loop.start("star_dim", "after", root=where)
    found = verdict.answers(first["latest"], run=run, root=where)
    assert [one["choice"] for one in found["answers"]] == ["number"]
    carried = found["run"]["verdicts"][0]
    assert carried["tool_passed"] is False and carried["person_accepted"] is True
    assert carried["predicates"][0]["id"] == "no-hot-facet"
    # a later read from `latest` hands back nothing already acted on
    assert verdict.answers(found["latest"], root=where)["answers"] == []


def test_the_page_is_given_the_answers_to_show_beside_the_family(page):
    base, _ = page
    post(base + "/api/judge", judged(choice="accept", why="yes"))
    _, body, _ = get(base + "/api/state")
    assert json.loads(body)["answers"][0]["why"] == "yes"


# -- a mark says where (§PW174) ------------------------------------------------------


def marked(box):
    return [{"member": "star_dim", "shapes": [{"box": box}]}]


def test_a_mark_is_kept_as_a_mask_the_size_of_the_picture_it_was_drawn_on(page):
    base, where = page
    status, said = post(
        base + "/api/judge",
        judged(
            choice="look",
            why="the left point is too long",
            marks=marked([2, 4, 10, 12]),
        ),
    )
    assert status == 200
    mark = said["answer"]["marks"][0]
    assert mark["picture"] == "renders/star_dim.png"
    with Image.open(where / mark["mask"]) as mask:
        assert mask.size == (24, 24)
        assert mask.getpixel((5, 8)) == 0 and mask.getpixel((20, 20)) == 255
    from polyweave import provenance

    assert mark["sha256"] == provenance.sha256_of(where / "renders" / "star_dim.png")[0]


def test_a_mark_on_a_member_the_family_does_not_have_is_refused_before_the_verdict(
    page,
):
    base, where = page
    status, said = post(
        base + "/api/judge",
        judged(marks=[{"member": "star_gold", "shapes": [{"box": [0, 0, 4, 4]}]}]),
    )
    assert status == 400 and said["code"] == "loop.unknown-sitting"
    spec = (where / "accept" / "star_dim.accept.toml").read_text(encoding="utf-8")
    assert "same star at size" not in spec


def test_a_persons_mark_outranks_the_described_region_for_an_edit(page, monkeypatch):
    from polyweave import picture, variation

    base, where = page
    post(
        base + "/api/judge",
        judged(choice="look", why="this corner", marks=marked([0, 0, 6, 6])),
    )
    (where / "polyweave.toml").write_text(
        '[service]\nbase = "https://api.ideogram.ai"\nkey_env = "POLYWEAVE_TEST_I"\n'
        'prices = { "edit" = 0.06 }\n\n'
        '[budget]\ncredits = 60\nexpires = "2099-12-31"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("POLYWEAVE_TEST_I", "sk")
    sent = {}

    def send(endpoint, key, payload, files=None):
        sent["files"] = files
        return 200, json.dumps(
            {"created": "t", "data": [{"seed": 1, "url": "https://p/x.png"}]}
        ).encode()

    monkeypatch.setattr(picture, "_send", send)
    monkeypatch.setattr(
        picture,
        "_download",
        lambda link: (where / "renders" / "star_dim.png").read_bytes(),
    )
    variation.vary(
        "renders/star_dim.png", "renders/v.png", "fix it", region="anything", root=where
    )
    from polyweave import provenance

    record = provenance.read("renders/v.png", root=where)
    assert record["details"]["mask_from"] == "person"
    assert record["details"]["mask"].startswith(".polyweave/marks/")


# -- the refused beside the kept (§PW175) --------------------------------------------


@pytest.fixture
def gated(page):
    from PIL import ImageDraw

    from polyweave import picture

    base, where = page

    def drawn(name, box):
        image = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        ImageDraw.Draw(image).ellipse(box, fill=(242, 193, 78, 255))
        image.save(where / name)

    drawn("outline.png", (14, 44, 114, 84))
    drawn("wide.png", (15, 44, 115, 84))
    drawn("dome.png", (44, 8, 84, 120))
    ran = picture.gate(["wide.png", "dome.png"], "outline.png", root=where)
    return base, where, ran


def test_the_page_shows_what_the_gate_refused_with_its_numbers(gated):
    base, _, ran = gated
    _, body, _ = get(base + "/api/state")
    run = json.loads(body)["gates"][-1]
    assert run["id"] == ran["id"] and run["chosen"] == "wide.png"
    refused = [one for one in run["candidates"] if not one["passed"]]
    assert [one["picture"] for one in refused] == ["dome.png"]
    assert "centroid" in refused[0]["failed"][0]
    assert refused[0]["silhouette_iou"] < 0.97


def test_a_person_may_promote_a_refused_picture_and_it_is_an_overruling(gated):
    from polyweave import verdict

    base, where, ran = gated
    status, said = post(
        base + "/api/judge",
        {
            "gate": ran["id"],
            "picture": "dome.png",
            "choice": "accept",
            "why": "the dome is what I wanted after all",
        },
    )
    assert status == 200
    one = verdict.answers(root=where)["answers"][-1]
    assert one["sitting"] == f"gate:{ran['id']}" and one["family"] == "dome"
    member = one["members"][0]
    assert member["tool_passed"] is False and member["person_accepted"] is True


def test_a_promotion_the_gate_never_saw_is_refused(gated):
    base, _, ran = gated
    status, said = post(
        base + "/api/judge",
        {"gate": ran["id"], "picture": "other.png", "choice": "accept", "why": "x"},
    )
    assert status == 400 and said["code"] == "loop.unknown-sitting"


def test_there_is_no_bound_to_move_on_a_picture_with_no_spec(gated):
    base, _, ran = gated
    status, said = post(
        base + "/api/judge",
        {"gate": ran["id"], "picture": "dome.png", "choice": "number", "why": "x"},
    )
    assert status == 400 and said["code"] == "loop.no-failed-bound"


# -- comparing in one place (§PW176) -------------------------------------------------


def test_the_difference_map_lights_only_what_is_above_the_noise_floor(page):
    base, where = page
    Image.new("RGBA", (64, 64), (120, 120, 120, 255)).save(where / "a.png")
    moved = Image.new("RGBA", (64, 64), (120, 120, 120, 255))
    moved.paste((200, 60, 60, 255), (0, 0, 16, 16))
    moved.save(where / "b.png")
    _, body, _ = get(base + "/api/compare?old=a.png&new=b.png")
    found = json.loads(body)
    assert found["changed_patches"] == 4  # the one 16-pixel square, in 8-pixel patches
    with Image.open(where / found["map"]) as shown:
        assert shown.getpixel((4, 4))[:3] == (255, 59, 48)
        assert shown.getpixel((40, 40))[0] < 100
    _, body, _ = get(base + "/api/compare?old=a.png&new=a.png")
    assert json.loads(body)["changed_patches"] == 0


def test_nothing_outside_the_project_is_compared(page):
    base, _ = page
    with pytest.raises(urllib.error.HTTPError) as caught:
        get(base + "/api/compare?old=../x.png&new=review/stars.png")
    assert caught.value.code == 404


def test_a_refused_picture_is_compared_with_the_canon_as_a_difference_map(page):
    from PIL import ImageDraw

    from polyweave import picture

    base, where = page
    (where / "polyweave.toml").write_text('[style]\ncanon = "canon"\n', "utf-8")
    (where / "canon").mkdir()

    def drawn(path, box):
        image = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        ImageDraw.Draw(image).ellipse(box, fill=(242, 193, 78, 255))
        image.save(path)

    drawn(where / "canon" / "c0.png", (14, 44, 114, 84))
    (where / "canon" / "canon.json").write_text(
        json.dumps([{"picture": "c0.png", "sha256": "0"}]), "utf-8"
    )
    drawn(where / "outline.png", (14, 44, 114, 84))
    drawn(where / "dome.png", (44, 8, 84, 120))
    picture.gate(["dome.png"], "outline.png", root=where)
    _, body, _ = get(base + "/api/state")
    one = json.loads(body)["gates"][-1]["candidates"][0]
    assert one["compare"] == {"old": "canon/c0.png", "mode": "difference", "mask": None}


def test_a_mesh_is_turned_at_the_rigs_own_camera_and_listed_for_the_page(page):
    from polyweave import shape
    from polyweave.render.rig import Rig

    base, where = page
    asked = []

    def bake(report, *, out, model, rung, root, inline, azimuth, elevation):
        asked.append((azimuth, elevation))
        Image.new("RGBA", (16, 16), (100, 100, 100, 255)).save(out)
        return {"artefact": out}

    (where / "m.glb").write_bytes(b"glTF")
    for _ in range(2):
        shape.turntable(
            "m.glb",
            out="turns/m",
            against="review/stars.png",
            root=where,
            frames=4,
            bake=bake,
        )
    rig = Rig()
    assert asked[:4] == [
        ((rig.azimuth + step * 90.0) % 360.0, rig.elevation) for step in range(4)
    ]
    assert asked[4] == (0.0, 0.0)  # the front view, the one the shape check scores
    _, body, _ = get(base + "/api/state")
    turned = json.loads(body)["turntables"]
    assert len(turned) == 1  # one folder, listed once however often it is redone
    assert turned[0]["asset"] == "m"
    assert [f["picture"] for f in turned[0]["frames"]][0] == "turns/m/turn_00.png"
    assert turned[0]["against"] == "review/stars.png"
