"""A video's published description, from the credits its records hold (§PW711)."""

from __future__ import annotations

import pytest

from polyweave.kernel import provenance
from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.store.description import description


def _made(root, name, **extra):
    path = root / "media" / name
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(name.encode())
    engine = extra.pop("engine", {"name": "pixabay"})
    provenance.write(provenance.build("fetch", path, engine=engine, extra=extra,
                                      root=root), root)
    return f"media/{name}"


@pytest.fixture
def project(tmp_path):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    used = [
        _made(tmp_path, "wp.mp4", engine={"name": "youtube"},
              licence="CC BY 3.0", author="WordPress",
              credit="“WordPress at 20”, WordPress, CC BY 3.0: "
                     "https://www.youtube.com/watch?v=FC9wfK1_F8c"),
        _made(tmp_path, "a.jpg", licence="Pixabay Content License", author="Ana"),
        _made(tmp_path, "b.jpg", licence="Pixabay Content License", author="Bo"),
        _made(tmp_path, "c.jpg", licence="Pixabay Content License", author="Ana"),
        _made(tmp_path, "mystery.png", engine={"name": "hand"}),
    ]
    return tmp_path, used


def test_required_credits_stay_whole_and_the_rest_are_grouped(project):
    root, used = project
    said = description(used, summary="How Git broke at scale.",
                       chapters=[{"at": 0, "title": "Abertura"},
                                 {"at": 75, "title": "O monorepo"}],
                       out="publish/description.txt", root=str(root))
    text = said["text"]
    assert text.startswith("How Git broke at scale.\n\n0:00 Abertura\n1:15 O monorepo")
    assert "https://youtu.be/FC9wfK1_F8c" in text and "watch?v=" not in text
    assert "pixabay (Pixabay Content License): Ana, Bo" in text
    assert said["unstated"] == ["media/mystery.png"]
    assert "mystery" not in text
    assert (root / "publish" / "description.txt").read_text("utf-8") == text


def test_a_text_past_the_limit_is_refused_never_cut(project):
    root, used = project
    with pytest.raises(PolyweaveError) as refused:
        description(used, summary="x" * 200, limit=150, root=str(root))
    assert refused.value.code == "store.description-long"
    assert "credits a licence requires" in refused.value.message


def test_chapters_must_start_at_zero_and_rise(project):
    root, used = project
    with pytest.raises(PolyweaveError) as refused:
        description(used, chapters=[{"at": 5, "title": "x"}], root=str(root))
    assert refused.value.code == "store.bad-chapters"
