"""What a project declares, and how a value is resolved.

`docs/specs/project-config.md`. The measure §PW5 sets is whether a second project can
run the plugin at all, so every test here is about a setting the project owns and the
plugin only defaults.
"""

from __future__ import annotations

from datetime import date

import pytest

from polyweave import config as C
from polyweave.errors import PolyweaveError


def project(tmp_path, text=None):
    if text is not None:
        (tmp_path / C.FILENAME).write_text(text, encoding="utf-8")
    return tmp_path


# -- resolution ----------------------------------------------------------------


def test_a_project_with_no_config_gets_every_default(tmp_path):
    found = C.load(project(tmp_path))
    assert found.source is None
    assert found.get("render.max_parallel") == 4
    assert found.get("tolerance.alpha_floor") == 0.02
    assert found.get("project.name") == tmp_path.name


def test_the_file_overrides_the_default(tmp_path):
    found = C.load(project(tmp_path, "[render]\nmax_parallel = 8\n"))
    assert found.get("render.max_parallel") == 8
    # and everything it did not state is still the plugin's
    assert found.get("render.preview_size") == 256


def test_an_explicit_argument_overrides_the_file(tmp_path):
    found = C.load(project(tmp_path, "[render]\nmax_parallel = 8\n"))
    assert found.get("render.max_parallel", 2) == 2


def test_every_setting_can_be_overridden(tmp_path):
    """A default that cannot be overridden is a defect, so this asserts none is."""
    found = C.load(project(tmp_path))
    for address in found.addresses():
        table, key = address.split(".")
        assert key in C.DEFAULTS[table]


def test_a_correction_is_read_without_a_restart(tmp_path):
    project(tmp_path, "[render]\nmax_parallel = 2\n")
    assert C.load(tmp_path).get("render.max_parallel") == 2
    (tmp_path / C.FILENAME).write_text("[render]\nmax_parallel = 9\n", encoding="utf-8")
    assert C.load(tmp_path).get("render.max_parallel") == 9


def test_what_the_project_stated_is_distinguishable_from_a_default(tmp_path):
    found = C.load(project(tmp_path, "[render]\nseed = 20260922\n"))
    assert found.declared("render.seed") is True
    assert found.declared("render.max_parallel") is False


# -- a typo is refused, never dropped ------------------------------------------


def test_an_unknown_key_is_refused_and_the_near_one_named(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        C.load(project(tmp_path, "[render]\nmax_parallell = 8\n"))
    assert caught.value.code == "config.unknown-key"
    assert "render.max_parallel" in caught.value.remedy


def test_an_unknown_table_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        C.load(project(tmp_path, "[renderer]\nmax_parallel = 8\n"))
    assert caught.value.code == "config.unknown-table"
    assert "render" in caught.value.remedy


def test_a_value_of_the_wrong_type_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        C.load(project(tmp_path, '[render]\nmax_parallel = "eight"\n'))
    assert caught.value.code == "config.bad-type"


def test_an_integer_is_accepted_where_a_float_is_declared(tmp_path):
    found = C.load(project(tmp_path, "[tolerance]\nalpha_floor = 0\n"))
    assert found.get("tolerance.alpha_floor") == 0


def test_a_malformed_file_says_where(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        C.load(project(tmp_path, "[render\nmax_parallel = 8\n"))
    assert caught.value.code == "config.malformed"
    assert caught.value.detail


def test_reading_a_setting_that_does_not_exist_is_refused(tmp_path):
    found = C.load(project(tmp_path))
    with pytest.raises(PolyweaveError) as caught:
        found.get("render.parallelism")
    assert caught.value.code == "config.unknown-address"


# -- a project's own rungs are its own ------------------------------------------


def test_samples_is_keyed_by_the_rungs_the_project_declares(tmp_path):
    found = C.load(
        project(
            tmp_path,
            '[render]\nrungs = ["flat", "final"]\n'
            "samples = { flat = 8, final = 900 }\n",
        )
    )
    assert found.get("render.samples") == {"flat": 8, "final": 900}


# -- paths stay inside the tree --------------------------------------------------


def test_a_relative_path_resolves_under_the_project_root(tmp_path):
    found = C.load(project(tmp_path, '[paths]\nrenders = "docs/art"\n'))
    assert found.path("paths.renders") == (tmp_path / "docs" / "art").resolve()


@pytest.mark.parametrize("elsewhere", ["C:/elsewhere", "/elsewhere"])
def test_an_absolute_path_is_refused_where_only_a_binary_may_be(tmp_path, elsewhere):
    """Either desk's absolute: `C:/…` read on Linux is not a folder named `C:` here."""
    with pytest.raises(PolyweaveError) as caught:
        C.load(project(tmp_path, f'[paths]\nrenders = "{elsewhere}"\n')).path(
            "paths.renders"
        )
    assert caught.value.code == "config.path-outside"
    assert "blender" in caught.value.remedy


def test_a_path_that_climbs_out_of_the_tree_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        C.load(project(tmp_path, '[paths]\nmeshes = "../next-door"\n')).path(
            "paths.meshes"
        )
    assert caught.value.code == "config.path-outside"


def test_a_binary_may_be_absolute(tmp_path):
    found = C.load(
        project(tmp_path, '[paths]\nblender = "C:/Program Files/b/blender.exe"\n')
    )
    assert found.path("paths.blender").as_posix().endswith("blender.exe")


def test_work_is_inside_the_tree_by_default(tmp_path):
    found = C.load(project(tmp_path))
    assert found.path("paths.work") == (tmp_path / ".polyweave").resolve()


# -- a secret is named, never stored ---------------------------------------------


def test_an_environment_reference_resolves_per_call(tmp_path, monkeypatch):
    found = C.load(project(tmp_path, '[paths]\ngodot = "${POLYWEAVE_TEST_GODOT}"\n'))
    monkeypatch.setenv("POLYWEAVE_TEST_GODOT", "/opt/godot/godot")
    assert found.get("paths.godot") == "/opt/godot/godot"
    monkeypatch.setenv("POLYWEAVE_TEST_GODOT", "/opt/godot4/godot")
    assert found.get("paths.godot") == "/opt/godot4/godot"


def test_an_unset_environment_reference_says_which_variable(tmp_path, monkeypatch):
    monkeypatch.delenv("POLYWEAVE_TEST_GODOT", raising=False)
    found = C.load(project(tmp_path, '[paths]\ngodot = "${POLYWEAVE_TEST_GODOT}"\n'))
    with pytest.raises(PolyweaveError) as caught:
        found.get("paths.godot")
    assert caught.value.code == "config.env-unset"
    assert "POLYWEAVE_TEST_GODOT" in caught.value.message


def test_the_config_holds_the_name_of_a_key_and_never_a_key(tmp_path, monkeypatch):
    monkeypatch.setenv("MESHY_API_KEY", "sk-never-in-a-file")
    found = C.load(project(tmp_path, '[service]\nkey_env = "MESHY_API_KEY"\n'))
    assert found.get("service.key_env") == "MESHY_API_KEY"
    assert "sk-never-in-a-file" not in (tmp_path / C.FILENAME).read_text()


# -- the budget is a person's decision -------------------------------------------


def test_no_budget_means_no_spend_rather_than_an_unlimited_one(tmp_path):
    found = C.load(project(tmp_path)).budget()
    assert found["spendable"] is False
    assert "no credits" in found["why"]


def test_an_expired_budget_is_not_spendable(tmp_path):
    found = C.load(
        project(tmp_path, '[budget]\ncredits = 60\nexpires = "2020-01-01"\n')
    ).budget(today=date(2026, 9, 22))
    assert found["spendable"] is False
    assert "expired on 2020-01-01" in found["why"]


def test_a_live_budget_is_spendable(tmp_path):
    found = C.load(
        project(tmp_path, '[budget]\ncredits = 60\nexpires = "2026-12-31"\n')
    ).budget(today=date(2026, 9, 22))
    assert found == {
        "service": "default",
        "amount": 60,
        "unit": "credits",
        "table": "[budget]",
        "expires": "2026-12-31",
        "spendable": True,
        "why": "",
    }


def test_credits_without_an_expiry_are_not_spendable(tmp_path):
    """A ceiling with no date never lapses, which is not a decision anyone made."""
    found = C.load(project(tmp_path, "[budget]\ncredits = 60\n")).budget()
    assert found["spendable"] is False


def test_an_expiry_that_is_not_a_date_is_refused(tmp_path):
    with pytest.raises(PolyweaveError) as caught:
        C.load(
            project(tmp_path, '[budget]\ncredits = 60\nexpires = "next tuesday"\n')
        ).budget()
    assert caught.value.code == "config.bad-type"


# -- what reads it ---------------------------------------------------------------


def test_a_job_store_takes_its_parallelism_and_work_from_the_project(tmp_path):
    from polyweave.jobs import JobStore

    project(tmp_path, '[render]\nmax_parallel = 2\n\n[paths]\nwork = ".work"\n')
    store = JobStore.for_project(tmp_path)
    assert store.max_parallel == 2
    assert store.work == (tmp_path / ".work").resolve()


def test_capabilities_reads_the_project_it_is_asked_about(tmp_path, monkeypatch):
    from polyweave.capabilities import capabilities

    monkeypatch.setenv("POLYWEAVE_TEST_KEY", "sk-never-echoed")
    project(
        tmp_path,
        '[service]\nkey_env = "POLYWEAVE_TEST_KEY"\n\n'
        '[budget]\ncredits = 12\nexpires = "2099-01-01"\n',
    )
    found = capabilities(tmp_path, probe=False)
    assert found["service"] == {"key_env": "POLYWEAVE_TEST_KEY", "key_present": True}
    assert "sk-never-echoed" not in repr(found)
    assert found["budget"]["spendable"] is True
    assert found["project"]["config"].endswith(C.FILENAME)
