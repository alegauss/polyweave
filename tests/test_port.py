"""A family stated, not scripted (§PW120)."""

from __future__ import annotations

import json

import pytest
from PIL import Image

from polyweave import loop, port
from polyweave.errors import PolyweaveError

SPEC = """asset = "{name}"

[[predicate]]
id      = "tone"
measure = "luma_p99"
region  = "frame"
{bound}
"""

FAMILY = """family = "stars"
rig    = "{rig}"
budget = 12

[search.exposure]
min = -1.0
max = 1.0

[given]
exposure = {given}

[[member]]
name  = "star_dim"
spec  = "accept/star_dim.accept.toml"
model = "assets/star.glb"
fixes = {{ key = 300.0 }}
out   = "work/star_dim.png"
bake  = "sprites/star_dim.png"

[[member]]
name  = "star_gold"
spec  = "accept/star_gold.accept.toml"
model = "assets/star.glb"
out   = "work/star_gold.png"
bake  = "sprites/star_gold.png"
"""


def project(
    tmp_path, *, rig="searched", given=0.0, dim="max = 0.37", gold="min = 0.05"
):
    (tmp_path / "accept").mkdir()
    for name, bound in (("star_dim", dim), ("star_gold", gold)):
        (tmp_path / "accept" / f"{name}.accept.toml").write_text(
            SPEC.format(name=name, bound=bound), encoding="utf-8"
        )
    (tmp_path / "family.toml").write_text(
        FAMILY.format(rig=rig, given=given), encoding="utf-8"
    )
    return tmp_path


class Baker:
    """A renderer whose grey follows the exposure, remembering every call."""

    def __init__(self, root):
        self.root, self.calls = root, []

    def __call__(self, report, *, out, exposure=0.0, **how):
        self.calls.append({"out": out, "exposure": exposure, **how})
        grey = int(max(0, min(255, 150 + 60 * exposure)))
        where = self.root / out
        where.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGBA", (8, 8), (grey, grey, grey, 255)).save(where)
        answer = {"cached": False, "elapsed_s": 0.1, "artefact": out}
        loop.bake_seen(answer)  # what render.bake does on its way out
        return answer


def test_a_family_file_is_searched_as_one_and_baked_when_all_pass(tmp_path):
    root = project(tmp_path)
    baker = Baker(root)
    run = loop.start("stars", "after", root=root)
    found = port.port(root / "family.toml", root=root, run=run, bake=baker)
    assert found["passed"]
    assert found["values"]["exposure"] < 0.4  # dark enough for the dim star's ceiling
    assert [b["name"] for b in found["baked"]] == ["star_dim", "star_gold"]
    assert all(b["passed"] for b in found["baked"])
    finals = [c for c in baker.calls if c.get("rung") == "final"]
    assert [c["out"] for c in finals] == [
        "sprites/star_dim.png",
        "sprites/star_gold.png",
    ]
    assert finals[0]["key"] == 300.0 and finals[0]["model"] == "assets/star.glb"
    # Every render the port made counted itself into the run, finals included.
    assert run["renders"] == len(baker.calls)


def test_nothing_is_baked_when_a_member_cannot_pass(tmp_path):
    root = project(tmp_path, dim="max = 0.01")
    baker = Baker(root)
    found = port.port(root / "family.toml", root=root, bake=baker)
    assert not found["passed"]
    assert found["baked"] == []
    assert not any(c.get("rung") == "final" for c in baker.calls)
    assert "nothing was baked" in found["says"]


def test_a_given_rig_is_rendered_once_per_member(tmp_path):
    root = project(tmp_path, rig="given", given=-0.5)
    baker = Baker(root)
    found = port.port(root / "family.toml", root=root, bake=baker)
    assert found["values"] == {"exposure": -0.5}
    assert found["passed"]
    assert len([c for c in baker.calls if c.get("rung") != "final"]) == 2


def test_a_declared_member_is_built_first(tmp_path):
    root = project(tmp_path)
    text = (root / "family.toml").read_text(encoding="utf-8")
    (root / "family.toml").write_text(
        text.replace('model = "assets/star.glb"', 'declaration = "shapes/star.toml"'),
        encoding="utf-8",
    )
    built = []

    def build(source, **how):
        built.append(source)
        return {"status": "built", "outputs": [str(root / "shapes" / "star.glb")]}

    baker = Baker(root)
    port.port(root / "family.toml", root=root, bake=baker, build=build)
    assert built == ["shapes/star.toml", "shapes/star.toml"]
    assert baker.calls[0]["model"] == "shapes/star.glb"


@pytest.mark.parametrize(
    ("edit", "says"),
    [
        (('rig    = "searched"', 'rig = "placed"'), "neither of"),
        (("budget = 12", "budget = 12\nturns = 3"), "has no turns"),
        (('out   = "work/star_gold.png"\n', ""), "does not say out"),
        (
            (
                'model = "assets/star.glb"\nout   = "work/star_gold.png"',
                'model = "a"\ndeclaration = "b"\nout = "c"',
            ),
            "exactly one of model and declaration",
        ),
    ],
)
def test_a_family_that_cannot_be_ported_is_refused(tmp_path, edit, says):
    root = project(tmp_path)
    text = (root / "family.toml").read_text(encoding="utf-8")
    (root / "family.toml").write_text(text.replace(*edit), encoding="utf-8")
    with pytest.raises(PolyweaveError) as refused:
        port.read(root / "family.toml")
    assert refused.value.code == "search.bad-family"
    assert says in refused.value.message


# -- the rig a search found is kept (§PW144) -------------------------------------------


def searches(baker):
    return len([c for c in baker.calls if c.get("rung") != "final"])


def test_a_found_rig_is_kept_and_the_next_port_starts_from_it(tmp_path):
    root = project(tmp_path)
    first = port.port(root / "family.toml", root=root, bake=Baker(root))
    kept = json.loads((root / "family.rig.json").read_text(encoding="utf-8"))
    assert kept["values"] == first["values"]
    assert kept["fixed"]["star_dim"] == {"key": 300.0}
    assert first["rig_from"] == "searched"

    baker = Baker(root)
    again = port.port(root / "family.toml", root=root, bake=baker)
    assert again["rig_from"] == "kept"
    assert again["values"] == first["values"]
    assert again["passed"]
    assert searches(baker) == 2  # one render per member, no search


def test_a_kept_rig_that_no_longer_passes_is_searched_again(tmp_path):
    root = project(tmp_path)
    port.port(root / "family.toml", root=root, bake=Baker(root))
    (root / "family.rig.json").write_text(
        json.dumps({"values": {"exposure": 0.9}}), encoding="utf-8"
    )
    baker = Baker(root)
    found = port.port(root / "family.toml", root=root, bake=baker)
    assert found["rig_from"] == "searched"
    assert found["passed"]
    assert searches(baker) > 2


def test_fresh_searches_even_where_the_kept_rig_passes(tmp_path):
    root = project(tmp_path)
    port.port(root / "family.toml", root=root, bake=Baker(root))
    found = port.port(root / "family.toml", root=root, bake=Baker(root), fresh=True)
    assert found["rig_from"] == "searched"


def test_a_rig_kept_outside_the_familys_axes_is_not_a_guess_it_may_make(tmp_path):
    root = project(tmp_path)
    (root / "family.rig.json").write_text(
        json.dumps({"values": {"exposure": -3.0}}), encoding="utf-8"
    )
    found = port.port(root / "family.toml", root=root, bake=Baker(root))
    assert found["rig_from"] == "searched"


def test_another_family_starts_from_a_kept_rig(tmp_path):
    root = project(tmp_path)
    port.port(root / "family.toml", root=root, bake=Baker(root))
    text = (root / "family.toml").read_text(encoding="utf-8")
    (root / "moons.toml").write_text(
        text.replace('family = "stars"', 'family = "moons"\nstart = "family.rig.json"'),
        encoding="utf-8",
    )
    baker = Baker(root)
    found = port.port(root / "moons.toml", root=root, bake=baker)
    assert found["rig_from"] == "started"
    assert searches(baker) == 2
