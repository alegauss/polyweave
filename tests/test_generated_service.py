"""A generated file's service, named even where an older record left it out (§PW454).

Spinhold's five Meshy meshes were recorded by polyweave 0.1.0 as `engine: {"name":
"service"}`, and provenance.generated answered `"service": "service"` for each, where
naming the generator is the one thing a disclosure reads it for.
"""

from __future__ import annotations

import json

from polyweave.kernel import provenance

TWO = """[service.meshy]
base = "https://api.meshy.ai"

[service.ideogram]
base = "https://api.ideogram.ai"
"""


def project(tmp_path, ledger=()):
    (tmp_path / "polyweave.toml").write_text(TWO, encoding="utf-8")
    (tmp_path / "polyweave.purchases.json").write_text(json.dumps(list(ledger)),
                                                       encoding="utf-8")
    return tmp_path


def bought(root, path, *, task_id="01a0d058", engine=None, **extra):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(path.encode("utf-8"))
    provenance.write(provenance.build(
        "fetch", target, engine=engine or {"name": "service"},
        extra={"task_id": task_id, **extra}, root=root), root=root)


def said(root, path):
    found = provenance.generated(paths=[path], root=str(root))["generated"]
    assert len(found) == 1
    return found[0]


def test_a_named_record_is_answered_as_it_says(tmp_path):
    root = project(tmp_path)
    bought(root, "art/a.glb", engine={"name": "meshy"}, service="meshy")
    one = said(root, "art/a.glb")
    assert one["service"] == "meshy" and "inferred" not in one


def test_the_ledger_entry_for_the_file_names_its_service(tmp_path):
    root = project(tmp_path, [{"artefact": "art/drone.glb", "service": "meshy",
                               "task_id": "01a0d058"}])
    bought(root, "art/drone.glb")
    one = said(root, "art/drone.glb")
    assert one["service"] == "meshy" and one["inferred"] == "ledger"


def test_a_task_id_prefix_names_a_declared_service(tmp_path):
    root = project(tmp_path)
    bought(root, "art/brand/study.jpg", task_id="ideogram:cbgSSDJ", engine={})
    one = said(root, "art/brand/study.jpg")
    assert one["service"] == "ideogram" and one["inferred"] == "task_id"


def test_a_folder_named_for_a_declared_service_names_it(tmp_path):
    root = project(tmp_path)
    bought(root, "tools/art/meshy/ship.glb")
    one = said(root, "tools/art/meshy/ship.glb")
    assert one["service"] == "meshy" and one["inferred"] == "folder"


def test_nothing_to_go_on_is_null_with_the_remedy(tmp_path):
    root = project(tmp_path)
    bought(root, "art/ship.glb")
    one = said(root, "art/ship.glb")
    assert one["service"] is None
    assert "names no service" in one["why"]
    assert "art/ship.glb.prov.json" in one["fix"]
