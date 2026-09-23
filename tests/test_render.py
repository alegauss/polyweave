"""The ladder against a real renderer.

These start Blender, so they are the slow half of the suite and they skip where bpy is
not installed. What they are for is the claim the arithmetic cannot make: that the cheap
rung really is cheap, really shares the rig, and really says which rung it came from.
"""

from __future__ import annotations

import numpy as np
import pytest

from polyweave import config as C
from polyweave import provenance, render
from polyweave.errors import PolyweaveError

bpy = pytest.importorskip("bpy", reason="Blender is not importable in this interpreter")


@pytest.fixture
def project(tmp_path):
    """A project whose rungs are small enough to render inside a test."""
    (tmp_path / C.FILENAME).write_text(
        "[render]\n"
        "preview_size = 48\n"
        "final_size = 64\n"
        "samples = { sphere = 4, preview = 4, final = 8 }\n"
        "seed = 11\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def mesh(project):
    """A mesh on disk, exported by the renderer that will read it back."""
    import bpy

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cone_add(radius1=1.0, depth=2.0, vertices=64)
    out = project / "assets" / "cone.glb"
    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(out), export_format="GLB")
    return "assets/cone.glb"


class Reported:
    """Stands in for the job's report, and remembers what it was told."""

    def __init__(self):
        self.stages = []

    def stage(self, stage, *, progress=None, note=None):
        self.stages.append((stage, note))

    def progress(self, value, *, note=None):
        pass

    def note(self, text):
        pass


# -- the cheap rung ------------------------------------------------------------------


def test_the_sphere_rung_renders_without_a_mesh(project):
    report = Reported()
    out = render.bake(
        report,
        out="sphere.png",
        rung="sphere",
        material={"base_color": [0.8, 0.2, 0.2, 1.0], "roughness": 0.3},
        root=project,
    )
    assert out["rung"] == "sphere"
    assert (project / "sphere.png").is_file()
    assert out["size"] == 48
    assert out["samples"] == 4
    # building, then rendering — reported more than once as the work moves through it.
    assert list(dict.fromkeys(s for s, _ in report.stages)) == ["building", "rendering"]


def test_the_answer_says_which_rung_it_came_from(project, mesh):
    """A verdict taken at the sphere is never mistaken for one taken at the top."""
    cheap = render.bake(
        Reported(), out="a.png", asking=["saturation_p99"], root=project
    )
    dear = render.bake(
        Reported(), out="b.png", asking=["silhouette_iou"], model=mesh, root=project
    )
    assert cheap["rung"] == "sphere"
    assert dear["rung"] == "preview"
    assert provenance.read("a.png", root=project)["rung"] == "sphere"
    assert provenance.read("b.png", root=project)["rung"] == "preview"


def test_the_cheap_rung_reads_no_mesh_at_all(project, mesh):
    """The structural saving: the sphere rung never opens the file the final one needs.

    The wall-clock ratio §PW7 rests on — three seconds against two minutes — is a
    production-size claim, and what a test can hold honestly is the lever behind it. The
    sample-and-pixel half of that lever is asserted in test_ladder.py, which needs no
    renderer to state it.
    """
    out = render.bake(Reported(), out="cheap.png", rung="sphere", root=project)
    assert provenance.read("cheap.png", root=project)["inputs"] == []
    assert out["rung"] == "sphere"

    render.bake(Reported(), out="dear.png", rung="final", model=mesh, root=project)
    assert provenance.read("dear.png", root=project)["inputs"][0]["role"] == "mesh"


# -- what the render is held to -------------------------------------------------------


def test_the_render_is_asserted_before_it_is_returned(project):
    """§2: a blank render is an error here, not a file somebody opens later."""
    out = render.bake(
        Reported(),
        out="lit.png",
        rung="sphere",
        material={"base_color": [0.9, 0.7, 0.2, 1.0]},
        root=project,
    )
    assert out["asserted"]["size"] == [48, 48]
    assert 0.0 < out["asserted"]["alpha_coverage"] < 1.0


def test_the_rig_is_what_puts_light_on_the_subject(project):
    """Turn the lights off and the same subject comes back black, so they do it."""
    lit = render.bake(
        Reported(),
        out="lit2.png",
        rung="sphere",
        material={"base_color": [0.9, 0.7, 0.2, 1.0]},
        root=project,
    )
    dark = render.bake(
        Reported(),
        out="dark.png",
        rung="sphere",
        material={"base_color": [0.9, 0.7, 0.2, 1.0]},
        key=0.0,
        fill=0.0,
        rim=0.0,
        ambient=0.0,
        # Which is now refused unless it is asked for: a black render is what §PW42's
        # check exists to catch, and this test wants one on purpose.
        allow_uniform=True,
        root=project,
    )
    # The same silhouette either way; only what reaches the film differs.
    assert dark["asserted"]["alpha_coverage"] == pytest.approx(
        lit["asserted"]["alpha_coverage"], abs=0.02
    )
    assert _mean_luma(project / "dark.png") < _mean_luma(project / "lit2.png") / 10


def test_a_render_that_is_black_to_any_observer_is_refused(project):
    """§PW42, proved against a real render rather than a constructed array.

    An unlit sphere through Cycles at four samples comes back with two distinct
    colours: (0,0,0) across the subject and (1,1,1) at the antialiased edge. So the
    assertion that asked whether every visible pixel was *exactly* one colour passed a
    picture that is black to any observer, on one least significant bit.
    """
    with pytest.raises(PolyweaveError) as caught:
        render.bake(
            Reported(),
            out="unlit.png",
            rung="sphere",
            key=0.0,
            fill=0.0,
            rim=0.0,
            ambient=0.0,
            root=project,
        )
    assert caught.value.code == "post.render-uniform"
    assert "allow_uniform" in caught.value.remedy


def test_the_edge_noise_that_used_to_get_through_is_what_the_floor_is_set_at(project):
    """1/255 is 0.0039, and a floor of 0.0040 is why it is caught at all."""
    from polyweave import config, post
    from polyweave.image import Image

    # The flatness check is about a byte of edge noise, not about sampler noise, so it
    # states its own bar rather than reading the rung's (§PW44).
    floor = 0.004
    assert config.load(project).tolerances("final").render_noise > floor

    def two_values(low, high):
        rgba = np.zeros((8, 8, 4), dtype=np.uint8)
        rgba[:, :, 3] = 255
        rgba[:, :, :3] = low
        rgba[0, 0, :3] = high
        return Image(path=None, rgba=rgba, had_alpha=True)

    with pytest.raises(PolyweaveError):
        post.check(
            "render",
            two_values(0, 1),
            alpha_floor=0.0,
            render_noise=floor,
            subject_extent=0.0,
        )
    # And two steps apart is a picture, not noise, so it is left alone.
    assert post.check(
        "render",
        two_values(0, 2),
        alpha_floor=0.0,
        render_noise=floor,
        subject_extent=0.0,
    )["size"] == [8, 8]


def _mean_luma(path) -> float:
    import numpy as np
    from PIL import Image

    rgba = np.asarray(Image.open(path).convert("RGBA"))
    visible = rgba[rgba[:, :, 3] > 5][:, :3]
    return float(visible.mean()) if len(visible) else 0.0


def test_a_record_is_written_beside_the_picture(project):
    out = render.bake(Reported(), out="deep/shot.png", rung="sphere", root=project)
    record = provenance.read("deep/shot.png", root=project)
    assert record["kind"] == "render"
    assert record["seed"] == 11
    assert record["samples"] == 4
    assert record["engine"]["name"] == "cycles"
    assert record["engine"]["version"]
    assert record["params"]["focal_mm"] == 50.0
    assert out["cache_key"] == provenance.cache_key(record)


def test_the_colour_pipeline_is_recorded_rather_than_assumed(project):
    """A render that moved because its view transform moved is otherwise a mystery."""
    render.bake(Reported(), out="cm.png", rung="sphere", root=project)
    engine = provenance.read("cm.png", root=project)["engine"]
    assert "view_transform" in engine
    assert "display_device" in engine


# -- the rungs share the rig -----------------------------------------------------------


def test_every_rung_records_the_same_rig(project, mesh):
    """A cheap answer describing a different scene is worse than no answer."""
    render.bake(Reported(), out="r1.png", rung="sphere", azimuth=12.0, root=project)
    render.bake(
        Reported(), out="r2.png", rung="final", azimuth=12.0, model=mesh, root=project
    )
    one = provenance.read("r1.png", root=project)["params"]
    two = provenance.read("r2.png", root=project)["params"]
    assert one == two


def test_the_same_render_twice_has_the_same_key(project):
    render.bake(Reported(), out="k1.png", rung="sphere", root=project)
    render.bake(Reported(), out="k2.png", rung="sphere", root=project)
    assert provenance.cache_key(
        provenance.read("k1.png", root=project)
    ) == provenance.cache_key(provenance.read("k2.png", root=project))


def test_a_rig_that_moved_has_a_different_key(project):
    render.bake(Reported(), out="m1.png", rung="sphere", azimuth=10.0, root=project)
    render.bake(Reported(), out="m2.png", rung="sphere", azimuth=80.0, root=project)
    assert provenance.cache_key(
        provenance.read("m1.png", root=project)
    ) != provenance.cache_key(provenance.read("m2.png", root=project))


# -- the mesh rungs -------------------------------------------------------------------


def test_a_rung_that_needs_a_mesh_says_so_when_there_is_none(project):
    with pytest.raises(PolyweaveError) as caught:
        render.bake(Reported(), out="x.png", rung="final", root=project)
    assert caught.value.code == "render.no-mesh"
    assert "sphere rung" in caught.value.remedy


def test_the_mesh_is_recorded_as_an_input_by_hash(project, mesh):
    render.bake(Reported(), out="cone.png", rung="final", model=mesh, root=project)
    inputs = provenance.read("cone.png", root=project)["inputs"]
    assert inputs[0]["role"] == "mesh"
    assert inputs[0]["path"] == "assets/cone.glb"
    assert len(inputs[0]["sha256"]) == 64


def test_a_mesh_that_is_not_there_names_the_path(project):
    with pytest.raises(PolyweaveError) as caught:
        render.bake(
            Reported(), out="x.png", rung="final", model="nope.glb", root=project
        )
    assert caught.value.code == "render.no-mesh"


def test_a_colour_written_as_hex_renders_as_that_colour(project):
    """§PW83: the socket is linear, and `#FFC43F` put on it raw came back pale.

    Emission with every light off, so what reaches the film is the declared colour and
    nothing the rig added, and the Standard transform hands it back as the same sRGB.
    """
    from polyweave import measure

    render.bake(
        Reported(),
        out="gold.png",
        rung="sphere",
        material={
            "colour": "#000000",
            "emission_color": "#FFC43F",
            "emission_strength": 1.0,
        },
        key=0.0,
        fill=0.0,
        rim=0.0,
        ambient=0.0,
        inline=False,
        allow_uniform=True,
        root=project,
    )
    found = measure.measure(
        project / "gold.png", ["delta_e"], region="subject", target="#FFC43F"
    )
    assert found[0]["value"] < 2.0


def test_a_material_field_the_shader_lacks_is_refused_rather_than_dropped(project):
    with pytest.raises(PolyweaveError) as caught:
        render.bake(
            Reported(),
            out="x.png",
            rung="sphere",
            material={"rougness": 0.5},
            root=project,
        )
    assert caught.value.code == "render.unknown-material-field"
    assert "roughness" in caught.value.remedy


# -- the picture and the numbers are one answer ---------------------------------------


def test_one_call_returns_the_picture_and_the_numbers(project):
    """§PW8: the verdict is formed in a single turn, not a render then two reads."""
    import base64

    out = render.bake(Reported(), out="both.png", rung="sphere", root=project)
    assert out["image"]["media_type"] == "image/png"
    assert (out["image"]["width"], out["image"]["height"]) == (48, 48)
    assert (
        base64.b64decode(out["image"]["base64"]) == (project / "both.png").read_bytes()
    )
    names = [m["measure"] for m in out["measurements"]]
    assert "saturation_p99" in names and "alpha_coverage" in names
    assert all(m["rung"] == "sphere" for m in out["measurements"])


def test_the_measurements_asked_for_come_back_with_the_render(project):
    out = render.bake(
        Reported(),
        out="asked.png",
        rung="sphere",
        measures=["alpha_coverage"],
        region="frame",
        root=project,
    )
    assert out["measurements"][0]["region"] == "frame"
    assert 0.0 < out["measurements"][0]["value"] < 1.0


def test_a_measure_outside_the_vocabulary_refuses_the_whole_call(project):
    """A short answer that looks complete is worse than a refusal naming the door."""
    with pytest.raises(PolyweaveError) as caught:
        render.bake(
            Reported(), out="x.png", rung="sphere", measures=["vibes"], root=project
        )
    assert caught.value.code == "spec.unknown-measure"


def test_the_picture_can_be_left_on_disk(project):
    """A sweep that only wants the numbers should not carry a megabyte of base64."""
    out = render.bake(
        Reported(), out="quiet.png", rung="sphere", inline=False, root=project
    )
    assert "image" not in out
    assert (project / "quiet.png").is_file()


def test_the_measurements_are_in_the_record_too(project):
    render.bake(Reported(), out="rec.png", rung="sphere", root=project)
    record = provenance.read("rec.png", root=project)
    assert "alpha_coverage" in record["measurements"]


# -- a path tracer's own noise, against a real change ----------------------------------


def test_a_path_tracers_own_noise_is_far_below_a_real_change(project):
    """The separation `measurements.md` demands, on noise this machine actually made.

    The tolerance is stated here rather than taken from the default, because the default
    is calibrated for a full-size final render and these are 48 pixels across. That the
    floor moves with the rung is §PW44; what this test holds is the separation, which is
    what makes any threshold between them findable at all.
    """
    from polyweave import measure

    red = {"base_color": [0.8, 0.2, 0.2, 1.0]}
    blue = {"base_color": [0.2, 0.2, 0.9, 1.0]}

    render.bake(Reported(), out="s1.png", rung="sphere", material=red, root=project)
    render.bake(Reported(), out="s3.png", rung="sphere", material=blue, root=project)
    (project / C.FILENAME).write_text(
        (project / C.FILENAME)
        .read_text(encoding="utf-8")
        .replace("seed = 11", "seed = 12"),
        encoding="utf-8",
    )
    render.bake(Reported(), out="s2.png", rung="sphere", material=red, root=project)

    at = {"root": project, "region": "frame", "tolerance": 0.1}
    twins = measure.same(project / "s1.png", project / "s2.png", **at)
    changed = measure.same(project / "s1.png", project / "s3.png", **at)

    assert twins["same"] is True, twins
    assert changed["same"] is False, changed
    assert changed["distance"] > twins["distance"] * 10


# -- through a job, which is how a caller actually reaches it -------------------------


def test_a_bake_runs_as_a_job_and_reports_its_stages(project, mesh):
    """§1 and §PW7 together: a render is a handle, and the handle names the rung."""
    from polyweave.jobs import JobStore

    store = JobStore.for_project(project, heartbeat_s=0.2)
    handle = store.start(
        "polyweave.render:bake",
        kind="bake",
        args={"out": "job.png", "rung": "sphere", "root": str(project)},
    )
    done = store.result(handle["job"], wait=True, timeout=300)
    assert done["status"] == "done", done["error"]
    assert done["result"]["rung"] == "sphere"
    assert (project / "job.png").is_file()


# -- four samples as four handles (§PW45) ---------------------------------------------


def test_a_pass_renders_through_job_handles_rather_than_one_at_a_time(project):
    """The job system was built for this and the search was not using it."""
    from polyweave import accept, search

    (project / "m.accept.toml").write_text(
        "asset = 'mascot'\n"
        "rung = 'sphere'\n"
        "[[predicate]]\n"
        "id = 'lit'\n"
        "measure = 'luma_p50'\n"
        "min = 0.0\n"
        "[search.key]\n"
        "min = 200.0\n"
        "max = 600.0\n",
        encoding="utf-8",
    )
    spec = accept.read(project / "m.accept.toml")
    every = search.in_parallel(spec, out="s.png", root=project)

    found = every([{"key": 200.0}, {"key": 400.0}, {"key": 600.0}])
    assert len(found) == 3, "one result per sample, in the order they were given"
    assert all(one["predicates"] for one in found)
    # Each sample wrote its own picture, since they were in flight together.
    assert sorted(p.name for p in project.glob("s-*.png")) == [
        "s-000.png",
        "s-001.png",
        "s-002.png",
    ]


def test_an_empty_pass_starts_no_jobs(project):
    from polyweave import accept, search

    spec = accept.parse(
        {
            "asset": "m",
            "rung": "sphere",
            "predicate": [{"id": "lit", "measure": "luma_p50", "min": 0.0}],
            "search": {"key": {"min": 200.0, "max": 600.0}},
        }
    )
    assert search.in_parallel(spec, out="s.png", root=project)([]) == []


# -- the bar a render is judged at is its own rung's (§PW62) ---------------------------


def test_the_strictest_floor_is_the_one_that_lets_a_flat_sphere_through():
    """Why naming no rung is the wrong default for this bar, and not a safe one.

    `render_noise` is the floor below which a picture counts as flat, so a *lower* bar
    refuses less. Final's 0.013 is the strictest number in the table and the most
    permissive answer to "is this blank", which is backwards on the rung that has the
    most sampler noise in it.
    """
    import numpy as np

    from polyweave import post
    from polyweave.image import Image

    # Two values, about 0.02 apart: sampler noise at four samples, on a picture that is
    # one colour to any observer.
    rgba = np.zeros((8, 8, 4), dtype=np.uint8)
    rgba[:, :, 3] = 255
    rgba[0, 0, :3] = 5
    speckled = Image(path=None, rgba=rgba, had_alpha=True)
    assert post.check(
        "render", speckled, alpha_floor=0.0, render_noise=0.013, subject_extent=0.0
    )["size"]
    with pytest.raises(PolyweaveError) as caught:
        post.check(
            "render", speckled, alpha_floor=0.0, render_noise=0.025, subject_extent=0.0
        )
    assert caught.value.code == "post.render-uniform"


def test_a_render_is_judged_at_its_own_rungs_floor(tmp_path):
    """The record PW51 writes is what makes this checkable at all."""
    pytest.importorskip("bpy", reason="Blender is not importable in this interpreter")
    from polyweave import config as C
    from polyweave import provenance, render

    (tmp_path / C.FILENAME).write_text(
        "[render]\npreview_size = 32\nfinal_size = 32\n"
        "samples = { sphere = 4, preview = 4, final = 4 }\nseed = 11\n",
        encoding="utf-8",
    )

    class Quiet:
        def stage(self, *a, **k):
            pass

        def progress(self, *a, **k):
            pass

        def note(self, *a, **k):
            pass

    settings = C.load(tmp_path)
    # The three rungs really are three different floors, or the check below proves
    # nothing: 0.025 at four samples, 0.020 at the preview, 0.013 at five hundred.
    floors = {
        r: settings.tolerances(r).render_noise for r in ("sphere", "preview", "final")
    }
    assert len(set(floors.values())) == 3
    assert settings.tolerances().render_noise == min(floors.values())

    # The sphere rung is the one that renders without a mesh, and the one that was
    # wrong: it has the most sampler noise and was judged at the strictest bar.
    render.bake(
        Quiet(),
        out="sphere.png",
        rung="sphere",
        root=tmp_path,
        inline=False,
        cached=False,
    )
    written = provenance.read("sphere.png", root=tmp_path)
    assert written["rung"] == "sphere"
    assert written["tolerances"]["render_noise"] == floors["sphere"]
    assert written["tolerances"]["render_noise"] != settings.tolerances().render_noise


# -- two materials on one object (§PW67) ----------------------------------------------


def test_one_rig_lights_one_shape_the_same_at_every_size(project):
    """§PW84: a rig fitted to the 96 px star went dark on the 192 px one.

    The same cube at two sizes. The camera is framed off the subject's own radius, so
    both fill the same picture and the only thing that differs is how big the subject is
    in the world the lights stand in.
    """
    from polyweave import measure
    from polyweave.geometry import build as B

    stated = {
        "name": "cube",
        "version": 1,
        "output": "cube",
        "params": {"size": 1.0},
        "materials": {},
        "nodes": [{"id": "cube", "op": "primitive", "kind": "cube", "size": "size"}],
    }
    tones = []
    for size in (1.0, 4.0):
        B.write(stated, project / f"cube-{size:g}.glb", root=project, size=size)
        render.bake(
            Reported(),
            out=f"cube-{size:g}.png",
            model=f"cube-{size:g}.glb",
            rung="final",
            inline=False,
            root=project,
        )
        taken = measure.measure(
            project / f"cube-{size:g}.png", ["luma_p50"], region="subject"
        )
        tones.append(taken[0]["value"])
    assert tones[1] == pytest.approx(tones[0], abs=0.02)


def _blend(where, *, text=False):
    """A `.blend` holding one cube in a material of its own, or one line of text."""
    import bpy

    from polyweave.render import blender

    blender.reset()
    if text:
        curve = bpy.data.curves.new("words", "FONT")
        curve.body = "Cottony"
        made = bpy.data.objects.new("words", curve)
        blocks = {made, curve}
    else:
        bpy.ops.mesh.primitive_cube_add()
        made = bpy.context.active_object
        paint = bpy.data.materials.new("candy_gold")
        made.data.materials.append(paint)
        blocks = {made, made.data, paint}
    bpy.data.libraries.write(str(where), blocks)
    blender.reset()
    return where


def test_a_blend_is_read_as_it_is(project):
    """§PW89: the brand marks are built in Blender, and an export would lose them."""
    from polyweave.render import blender

    obj = blender.load_mesh(_blend(project / "mark.blend"))
    assert obj.type == "MESH"
    assert [m.name for m in obj.data.materials] == ["candy_gold"]


def test_a_blend_with_no_mesh_in_it_says_what_it_holds(project):
    from polyweave.render import blender

    with pytest.raises(PolyweaveError) as caught:
        blender.load_mesh(_blend(project / "words.blend", text=True))
    assert caught.value.code == "render.no-mesh"
    assert "only font" in caught.value.message
    assert "convert" in caught.value.remedy


def test_a_blend_bakes_like_any_other_mesh(project):
    _blend(project / "mark.blend")
    out = render.bake(
        Reported(), out="mark.png", model="mark.blend", rung="preview", root=project
    )
    assert out["rung"] == "preview"
    assert out["asserted"]["size"] == [48, 48]


def _two_cubes(project):
    """One mesh of twelve faces: the first six wear one material, the rest another."""
    from polyweave.geometry import build as B

    stated = {
        "name": "pair",
        "version": 1,
        "params": {},
        "materials": {},
        "nodes": [
            {
                "id": "a",
                "op": "primitive",
                "kind": "cube",
                "size": 2.0,
                "material": "rope",
            },
            {
                "id": "b",
                "op": "primitive",
                "kind": "cube",
                "size": 2.0,
                "at": [4, 0, 0],
                "material": "cushion",
            },
            {"id": "it", "op": "union", "inputs": ["a", "b"]},
        ],
        "output": "it",
    }
    return B.build(stated, root=project)["output"]


def _as_object(made):
    """That mesh in an emptied scene, which is all these three need a renderer for."""
    import bpy

    bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh = bpy.data.meshes.new("pair")
    mesh.from_pydata(
        [tuple(v) for v in made["vertices"]], [], [tuple(f) for f in made["faces"]]
    )
    mesh.update()
    obj = bpy.data.objects.new("pair", mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def test_a_mesh_in_two_materials_gets_a_slot_for_each(project):
    """The renderer could always do this; nothing was handing it the groups."""
    from polyweave.render import blender

    made = _two_cubes(project)
    obj = _as_object(made)
    blender.apply_material(
        obj,
        {
            "rope": {"base_color": [1, 1, 1, 1]},
            "cushion": {"base_color": [1, 0.9, 0.8, 1]},
        },
        groups=made["groups"],
    )
    assert [m.name for m in obj.data.materials] == ["rope", "cushion"]
    slots = {p.material_index for p in obj.data.polygons}
    assert slots == {0, 1}, "both slots are actually used"
    first = [p.material_index for p in obj.data.polygons][:6]
    assert set(first) == {0}, "the first cube wears the first material"


def test_a_material_the_mesh_names_and_nobody_gave_is_refused(project):
    from polyweave.render import blender

    made = _two_cubes(project)
    obj = _as_object(made)
    with pytest.raises(PolyweaveError) as caught:
        blender.apply_material(obj, {"rope": {}}, groups=made["groups"])
    assert caught.value.code == "render.unknown-material-field"
    assert "cushion" in caught.value.message


def test_one_material_and_no_groups_still_means_one_slot(project):
    import bpy

    from polyweave.render import blender

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.active_object
    blender.apply_material(obj, {"base_color": [0.9, 0.2, 0.2, 1.0]})
    assert len(obj.data.materials) == 1
