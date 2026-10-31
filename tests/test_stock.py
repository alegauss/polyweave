"""Stock pictures from Pixabay, brought in with their licence (§PW673).

The service is never reached: `client.send` and `client.download` are replaced, so a
test says what would have been asked and what the record keeps.
"""

from __future__ import annotations

import json
import urllib.parse

import pytest

from polyweave.kernel import provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.picture import stock
from polyweave.services import client

HIT = {
    "id": 195893, "pageURL": "https://pixabay.com/photos/harbour-195893/",
    "tags": "harbour, dawn", "previewURL": "https://cdn.pixabay.com/p_150.jpg",
    "largeImageURL": "https://cdn.pixabay.com/p_1280.jpg", "imageWidth": 4000,
    "imageHeight": 2250, "user": "Ana", "user_id": 42,
}


class Service:
    def __init__(self, status=200):
        self.asked, self.status = [], status

    def send(self, url, **_):
        self.asked.append(dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query)))
        body = json.dumps({"totalHits": 1, "hits": [HIT]}).encode()
        return client.Answer(self.status, body, {})


@pytest.fixture
def service(tmp_path, monkeypatch):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    monkeypatch.setenv("PIXABAY_API_KEY", "px-key")
    fake = Service()
    monkeypatch.setattr(client, "send", fake.send)
    monkeypatch.setattr(client, "download", lambda link: b"\xff\xd8jpeg")
    return fake


def test_a_search_downloads_nothing_and_is_kept_for_a_day(tmp_path, service):
    found = stock.find("harbour at dawn", filters={"image_type": "photo"},
                       root=str(tmp_path))
    assert found["hits"][0]["author"] == "Ana"
    assert service.asked[0]["q"] == "harbour at dawn"
    assert service.asked[0]["image_type"] == "photo"
    assert service.asked[0]["safesearch"] == "true"
    stock.find("harbour at dawn", filters={"image_type": "photo"}, root=str(tmp_path))
    assert len(service.asked) == 1


def test_a_fetched_picture_is_recorded_with_its_page_author_and_licence(
    tmp_path, service
):
    said = stock.fetch(195893, "art/harbour.jpg", root=str(tmp_path))
    assert (tmp_path / "art" / "harbour.jpg").read_bytes() == b"\xff\xd8jpeg"
    record = provenance.read("art/harbour.jpg", root=tmp_path)
    assert record["kind"] == "fetch"
    assert record["licence"] == "Pixabay Content License"
    assert record["source_page"] == HIT["pageURL"]
    assert record["author"] == "Ana"
    assert record["credits"] == 0.0
    assert "px-key" not in json.dumps(record)
    listed = provenance.credits(root=str(tmp_path), all=True)
    assert listed["owed"] == []
    assert "unstated" not in listed
    assert said["licence"] == "Pixabay Content License"


def test_a_filter_the_service_does_not_take_is_refused_before_asking(
    tmp_path, service
):
    with pytest.raises(PolyweaveError) as refused:
        stock.find("harbour", filters={"colour": "blue"}, root=str(tmp_path))
    assert refused.value.code == "stock.bad-filter"
    assert service.asked == []


# -- footage by length and resolution (§PW674) ---------------------------------------

CLIP = {
    "id": 31377, "pageURL": "https://pixabay.com/videos/trail-31377/", "tags": "trail",
    "duration": 18, "user": "Ana", "user_id": 42,
    "videos": {
        "large": {"url": "", "width": 0, "height": 0, "size": 0},
        "medium": {"url": "https://cdn.pixabay.com/v_medium.mp4", "width": 1920,
                   "height": 1080, "size": 20_000_000},
        "small": {"url": "https://cdn.pixabay.com/v_small.mp4", "width": 1280,
                  "height": 720, "size": 9_000_000},
        "tiny": {"url": "https://cdn.pixabay.com/v_tiny.mp4", "width": 640,
                 "height": 360, "size": 2_000_000},
    },
}


@pytest.fixture
def footage(tmp_path, monkeypatch):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    monkeypatch.setenv("PIXABAY_API_KEY", "px-key")
    asked = []

    def send(url, **_):
        asked.append(url)
        body = json.dumps({"totalHits": 1, "hits": [CLIP]}).encode()
        return client.Answer(200, body, {})

    fetched = []
    monkeypatch.setattr(client, "send", send)
    monkeypatch.setattr(client, "download",
                        lambda link: fetched.append(link) or b"\x00\x00\x00\x18ftyp")
    return asked, fetched


def test_a_video_search_answers_every_rendition_without_a_download(tmp_path, footage):
    asked, fetched = footage
    found = stock.find("mountain trail", kind="video",
                       filters={"video_type": "film", "min_height": 720},
                       root=str(tmp_path))
    assert "/api/videos/" in asked[0]
    [hit] = found["hits"]
    assert hit["duration"] == 18
    assert set(hit["renditions"]) == {"medium", "small", "tiny"}
    assert hit["renditions"]["small"]["height"] == 720
    assert fetched == []


def test_a_height_takes_the_smallest_rendition_tall_enough(tmp_path, footage):
    _, fetched = footage
    said = stock.fetch(31377, "broll/trail.mp4", kind="video", height=700,
                       root=str(tmp_path))
    assert said["rendition"] == "small"
    assert fetched == ["https://cdn.pixabay.com/v_small.mp4"]
    assert "fell" not in said


def test_an_empty_rendition_falls_to_the_next_one_down_and_says_so(tmp_path, footage):
    said = stock.fetch(31377, "broll/trail.mp4", kind="video", root=str(tmp_path))
    assert said["rendition"] == "medium"
    assert "large is empty" in said["fell"]
    record = provenance.read("broll/trail.mp4", root=tmp_path)
    assert record["licence"] == "Pixabay Content License"
    assert record["params"]["rendition"] == "medium"
