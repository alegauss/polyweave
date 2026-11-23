"""Music from stock, brought in with its own licence and the credit it asks (§PW705).

Jamendo is never reached: `client.send` and `client.download` are replaced, so a test
says what would have been asked and what the record keeps.
"""

from __future__ import annotations

import json
import urllib.parse

import pytest

from polyweave.kernel import provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.picture import stock
from polyweave.services import client

TRACK = {
    "id": 1214935, "name": "Open Fields", "duration": 214, "artist_id": 7,
    "artist_name": "Ana Lua", "shareurl": "https://www.jamendo.com/track/1214935",
    "audio": "https://prod-1.storage.jamendo.com/?trackid=1214935&format=mp31",
    "audiodownload": "https://prod-1.storage.jamendo.com/download/track/1214935/mp32/",
    "audiodownload_allowed": True,
    "license_ccurl": "http://creativecommons.org/licenses/by/3.0/",
    "musicinfo": {"tags": {"genres": ["ambient"], "vartags": ["calm"]}},
}


class Service:
    def __init__(self, track):
        self.asked, self.track = [], track

    def send(self, url, **_):
        self.asked.append((urllib.parse.urlsplit(url).path,
                           dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))))
        body = {"headers": {"results_count": 1}, "results": [self.track]}
        return client.Answer(200, json.dumps(body).encode(), {})


@pytest.fixture
def jamendo(tmp_path, monkeypatch):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    monkeypatch.setenv("JAMENDO_CLIENT_ID", "jm-id")
    fake = Service(dict(TRACK))
    monkeypatch.setattr(client, "send", fake.send)
    monkeypatch.setattr(client, "download", lambda link: b"ID3mp3")
    return fake


def test_music_is_searched_by_words_tags_and_length(tmp_path, jamendo):
    found = stock.find("open calm bed", kind="music", service="jamendo",
                       filters={"tags": "ambient", "durationbetween": "120_600"},
                       root=str(tmp_path))
    path, asked = jamendo.asked[0]
    assert path.endswith("/v3.0/tracks/")
    assert asked["client_id"] == "jm-id" and asked["search"] == "open calm bed"
    assert asked["durationbetween"] == "120_600"
    [hit] = found["hits"]
    assert hit["title"] == "Open Fields" and hit["licence"] == "CC BY 3.0"
    assert hit["duration"] == 214 and found["total"] == 1


def test_a_track_is_recorded_with_its_own_licence_and_owes_its_credit(
    tmp_path, jamendo
):
    said = stock.fetch(1214935, "music/bed.mp3", kind="music", service="jamendo",
                       root=str(tmp_path))
    assert (tmp_path / "music" / "bed.mp3").read_bytes() == b"ID3mp3"
    record = provenance.read("music/bed.mp3", root=tmp_path)
    assert record["licence"] == "CC BY 3.0"
    assert record["licence_url"] == TRACK["license_ccurl"]
    assert "“Open Fields” by Ana Lua" in record["credit"]
    assert record["measurements"]["seconds"] == 214
    assert "jm-id" not in json.dumps(record)
    owed = provenance.credits(root=str(tmp_path))["owed"]
    assert owed[0]["files"] == ["music/bed.mp3"]
    assert said["credit"] == record["credit"]


def test_a_licence_the_project_does_not_ship_under_is_refused(tmp_path, jamendo):
    (tmp_path / "polyweave.toml").write_text(
        '[service.jamendo]\nlicences = ["CC BY 4.0"]\n', encoding="utf-8")
    jamendo.track["license_ccurl"] = "http://creativecommons.org/licenses/by-nc-sa/3.0/"
    with pytest.raises(PolyweaveError) as refused:
        stock.fetch(1214935, "music/x.mp3", kind="music", service="jamendo",
                    root=str(tmp_path))
    assert refused.value.code == "stock.licence-refused"
    assert "CC BY-NC-SA 3.0" in refused.value.message
    assert not (tmp_path / "music" / "x.mp3").exists()


@pytest.mark.parametrize(("kind", "service"), [("music", "pixabay"),
                                               ("picture", "jamendo")])
def test_a_kind_the_service_does_not_sell_is_refused(tmp_path, jamendo, kind, service):
    with pytest.raises(PolyweaveError) as refused:
        stock.find("x", kind=kind, service=service, root=str(tmp_path))
    assert refused.value.code == "stock.bad-kind"
    assert jamendo.asked == []
