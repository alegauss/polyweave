"""Editorial labels held against each other and the footage under them (§PW709)."""

from __future__ import annotations

import pytest

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.store.labels import labels

SAID = [
    {"id": "cap-3", "kind": "caption", "text": "30 mil merges por dia", "start": 4.0,
     "end": 7.0, "beat": "b3"},
    {"id": "hi-3", "kind": "highlight", "text": "30 mil merges por dia!", "start": 6.0,
     "end": 8.0, "take": "intro", "entities": ["event:monorepo"]},
    {"id": "hi-4", "kind": "highlight", "text": "Linus Torvalds", "start": 9.0,
     "end": 11.0, "entities": ["person:linus"]},
    {"id": "cap-5", "kind": "caption", "text": "Outra coisa", "start": 12.0,
     "end": 13.0},
]

SHOWN = [
    {"id": "stock-7", "source": "stock/office.mp4", "start": 5.0, "end": 9.0,
     "entities": ["event:monorepo"]},
    {"id": "stock-8", "source": "stock/typing.mp4", "start": 9.0, "end": 14.0},
]


def test_overlapping_labels_and_unshown_entities_are_each_named():
    said = labels(SAID, SHOWN)
    assert said["passed"] is False
    [overlap] = said["overlaps"]
    assert [one["id"] for one in overlap["labels"]] == ["cap-3", "hi-3"]
    assert (overlap["from"], overlap["to"]) == (6.0, 7.0)
    assert overlap["same"] == "duplicate"
    [unshown] = said["unverified"]
    assert unshown["label"]["id"] == "hi-4"
    assert unshown["footage"]["id"] == "stock-8"
    assert unshown["entities"] == ["person:linus"]


def test_differing_words_on_screen_at_once_are_versions():
    one = dict(SAID[1], text="31 mil merges por dia")
    said = labels([SAID[0], one])
    assert said["overlaps"][0]["same"] == "versions"
    assert said["unverified"] == []


def test_labels_that_never_meet_pass():
    assert labels([SAID[0], SAID[3]], SHOWN)["passed"] is True


def test_a_label_running_backwards_is_refused():
    with pytest.raises(PolyweaveError) as refused:
        labels([{"id": "x", "start": 3, "end": 1}])
    assert refused.value.code == "video.bad-labels"
