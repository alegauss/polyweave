"""The clean product instance a web visit films, declared, reset and proved (§PW710).

Docker and the ready URL are stood in for: what is held is which docker calls each
action makes, that each names only the declared project, and what a visit records.
"""

from __future__ import annotations

import json

import pytest

from polyweave.kernel.errors import PolyweaveError
from polyweave.layers.store import instance, web
from test_web_capture import _install, _Site

FIXTURE = """[instance]
compose = "docker/wp.compose.yml"
project = "pw-wordpress"
ready = "http://localhost:8080/wp-login.php"
ready_seconds = 5

[[seed]]
service = "cli"
run = ["wp", "core", "install", "--title=Demo"]
"""

PS = json.dumps({"Service": "wordpress", "ID": "c0ffee", "Image": "wordpress:6.7",
                 "State": "running"})


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / "polyweave.toml").write_text("", encoding="utf-8")
    (tmp_path / "docker").mkdir()
    (tmp_path / "docker" / "wp.compose.yml").write_text("services: {}\n", "utf-8")
    (tmp_path / "wp.instance.toml").write_text(FIXTURE, encoding="utf-8")
    calls = []

    def docker(argv):
        calls.append(argv)
        return PS + "\n" if "ps" in argv else ""

    monkeypatch.setattr(instance, "_docker", docker)
    monkeypatch.setattr(instance, "_answers", lambda url: True)
    return tmp_path, calls


def test_a_plan_runs_nothing_and_every_call_names_the_declared_project(project):
    root, calls = project
    said = instance.instance("wp.instance.toml", root=str(root))
    assert calls == []
    reset = said["plan"]["reset"]
    assert reset[0][:6] == ["docker", "compose", "-p", "pw-wordpress", "-f",
                            str(root / "docker" / "wp.compose.yml")]
    assert "--volumes" in reset[0]
    assert reset[-1][-4:] == ["wp", "core", "install", "--title=Demo"]
    assert all(one[2:4] == ["-p", "pw-wordpress"] for name in said["plan"]
               for one in said["plan"][name])


def test_a_reset_downs_its_own_volumes_waits_and_seeds(project):
    root, calls = project
    said = instance.instance("wp.instance.toml", action="reset", root=str(root))
    assert [call[4:6] for call in calls[:3]] == [
        [str(root / "docker" / "wp.compose.yml"), "down"],
        [str(root / "docker" / "wp.compose.yml"), "up"],
        [str(root / "docker" / "wp.compose.yml"), "exec"]]
    assert said["containers"] == [{"service": "wordpress", "container": "c0ffee",
                                   "image": "wordpress:6.7", "state": "running"}]


def test_an_instance_that_never_answers_is_refused(project, monkeypatch):
    root, _ = project
    monkeypatch.setattr(instance, "_answers", lambda url: False)
    monkeypatch.setattr(instance.time, "sleep", lambda s: None)
    clock = iter(range(0, 100, 3))
    monkeypatch.setattr(instance.time, "monotonic", lambda: float(next(clock)))
    with pytest.raises(PolyweaveError) as refused:
        instance.instance("wp.instance.toml", action="up", root=str(root))
    assert refused.value.code == "web.instance-not-ready"


def test_a_visit_records_the_instance_it_filmed(project, monkeypatch):
    root, calls = project
    (root / "scene.web.toml").write_text(
        '[web]\nurl = "http://localhost:8080/"\ninstance = "wp.instance.toml"\n'
        '[[step]]\ngo = "/"\n', encoding="utf-8")
    _install(monkeypatch, _Site())
    said = web.web("scene.web.toml", root=str(root))
    record = json.loads((root / said["record"]).read_text(encoding="utf-8"))
    filmed = record["params"]["instance"]
    assert filmed["project"] == "pw-wordpress"
    assert filmed["containers"][0]["image"] == "wordpress:6.7"
    assert {one["role"] for one in record["inputs"]} == {"visit", "instance", "compose"}
    # Filming never resets: only ps was asked of docker.
    assert all("ps" in call for call in calls)


def test_a_fixture_naming_another_s_compose_or_a_bad_project_is_refused(project):
    root, _ = project
    (root / "wp.instance.toml").write_text(
        FIXTURE.replace("pw-wordpress", "pw wordpress; rm"), encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        instance.instance("wp.instance.toml", root=str(root))
    assert refused.value.code == "web.bad-instance"
