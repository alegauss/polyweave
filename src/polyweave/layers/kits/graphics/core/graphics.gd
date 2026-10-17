class_name PolyweaveGraphics
extends Node
## Graphics presets, and a renderer that falls back (polyweave kit "graphics", §PW366).
## Godot carries the upscalers, the anti-aliasing and the renderers; what a game rewrote
## was choosing among them and surviving a driver that refuses.
##
## A preset touches only what the game uses. For a 3D game it sets the root viewport's
## render scale and upscaler (bilinear, FSR or FSR 2, Godot's own), MSAA, TAA, FXAA and
## positional shadow atlas, the frame cap, and switches the costly effects (SDFGI, SSAO,
## volumetric fog) off or back on, but only those an environment of the game switched on.
## For a 2D game it sets the stretch mode and integer scaling. The first launch picks a
## preset from the video adapter (an integrated or software one gets the lightest); the
## options kit's graphics row keeps the player's from then on.
##
## Vulkan failing to start is Godot's to survive: the project keeps
## rendering/rendering_device/fallback_to_opengl3 on, which the proof holds it to. Vendor
## SDKs (DLSS, Reflex, XeSS) stay out; Godot builds in none of them.
##
## The project's res://polyweave_graphics.gd may declare PRESETS (a name to its settings)
## and FIRST, the preset an unknown adapter starts on.

signal applied(preset: String)

const HERE := "res://addons/polyweave/graphics/graphics.gd"
const PROJECT := "res://polyweave_graphics.gd"
const FALLBACK := "rendering/rendering_device/fallback_to_opengl3"
const EFFECTS := ["sdfgi_enabled", "ssao_enabled", "volumetric_fog_enabled"]
const PRESETS_3D := {
	"low": {"scale": 0.5, "scaler": "fsr", "msaa": 0, "taa": false, "fxaa": true,
		"shadows": 1024, "effects": false, "max_fps": 60},
	"medium": {"scale": 0.75, "scaler": "fsr", "msaa": 0, "taa": false, "fxaa": true,
		"shadows": 2048, "effects": true, "max_fps": 0},
	"high": {"scale": 1.0, "scaler": "bilinear", "msaa": 2, "taa": false, "fxaa": false,
		"shadows": 4096, "effects": true, "max_fps": 0},
	"ultra": {"scale": 1.0, "scaler": "bilinear", "msaa": 4, "taa": true, "fxaa": false,
		"shadows": 8192, "effects": true, "max_fps": 0},
}
const PRESETS_2D := {
	"pixel": {"stretch": "viewport", "integer": true, "max_fps": 0},
	"smooth": {"stretch": "canvas_items", "integer": false, "max_fps": 0},
}
const SCALERS := {"bilinear": Viewport.SCALING_3D_MODE_BILINEAR,
	"fsr": Viewport.SCALING_3D_MODE_FSR, "fsr2": Viewport.SCALING_3D_MODE_FSR2}
const MSAA := {0: Viewport.MSAA_DISABLED, 2: Viewport.MSAA_2X, 4: Viewport.MSAA_4X,
	8: Viewport.MSAA_8X}
const STRETCH := {"disabled": Window.CONTENT_SCALE_MODE_DISABLED,
	"canvas_items": Window.CONTENT_SCALE_MODE_CANVAS_ITEMS,
	"viewport": Window.CONTENT_SCALE_MODE_VIEWPORT}

var three_d := true
var presets := {}
var preset := ""
var _environments: Array[Environment] = []
## each effect an environment of the game switched on, as it was found
var _used := {}

static var _shared: Node


static func shared() -> Node:
	if _shared == null or not is_instance_valid(_shared):
		_shared = load(HERE).new()
		_shared.name = "PolyweaveGraphics"
		var tree := Engine.get_main_loop() as SceneTree
		if tree != null and tree.root != null:
			tree.root.add_child.call_deferred(_shared)
	return _shared


static func declaration(project := PROJECT) -> Dictionary:
	if not ResourceLoader.exists(project):
		return {}
	return (load(project) as GDScript).get_script_constant_map()


func _init() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	var declared := declaration()
	three_d = _is_3d(str(ProjectSettings.get_setting("application/run/main_scene", "")))
	presets = declared.get("PRESETS", PRESETS_3D if three_d else PRESETS_2D)


static func _is_3d(scene: String) -> bool:
	if scene == "" or not ResourceLoader.exists(scene):
		return true
	var state := (load(scene) as PackedScene).get_state()
	for i in state.get_node_count():
		var kind := str(state.get_node_type(i))
		if ClassDB.class_exists(kind) and ClassDB.is_parent_class(kind, "Node3D"):
			return true
	return false


## the preset a first launch starts on, from the video adapter
func first() -> String:
	var said := (RenderingServer.get_video_adapter_vendor() + " "
		+ RenderingServer.get_video_adapter_name()).to_lower()
	var names: Array = presets.keys()
	if said.strip_edges() == "":
		return str(declaration().get("FIRST", names[names.size() / 2]))
	for weak in ["intel", "llvmpipe", "swiftshader", "microsoft basic", "software"]:
		if weak in said:
			return names[0]
	return names[mini(2, names.size() - 1)]


## the game's environments: their costly effects are the ones a preset may switch
func watch(node: Node) -> void:
	for found in node.find_children("*", "WorldEnvironment", true, false):
		var env := (found as WorldEnvironment).environment
		if env != null and not _environments.has(env):
			_environments.append(env)
			_used[env] = EFFECTS.filter(func(e: String) -> bool: return env.get(e))


func apply(named: String) -> void:
	var settings: Dictionary = presets.get(named, {})
	if settings.is_empty():
		return
	preset = named
	var view := get_tree().root if is_inside_tree() else (Engine.get_main_loop() as SceneTree).root
	Engine.max_fps = int(settings.get("max_fps", 0))
	if three_d:
		view.scaling_3d_mode = SCALERS.get(settings.get("scaler", "bilinear"), 0)
		view.scaling_3d_scale = float(settings.get("scale", 1.0))
		view.msaa_3d = MSAA.get(int(settings.get("msaa", 0)), Viewport.MSAA_DISABLED)
		view.use_taa = bool(settings.get("taa", false))
		view.screen_space_aa = Viewport.SCREEN_SPACE_AA_FXAA if settings.get("fxaa", false) \
			else Viewport.SCREEN_SPACE_AA_DISABLED
		view.positional_shadow_atlas_size = int(settings.get("shadows", 4096))
		for env in _environments:
			for effect in _used[env]:
				env.set(effect, bool(settings.get("effects", true)))
	else:
		view.content_scale_mode = STRETCH.get(settings.get("stretch", "disabled"), 0)
		view.content_scale_stretch = Window.CONTENT_SCALE_STRETCH_INTEGER \
			if settings.get("integer", false) else Window.CONTENT_SCALE_STRETCH_FRACTIONAL
	applied.emit(named)


## what is in force now, read back from the viewport and the environments, in the terms
## a preset declares
func in_force() -> Dictionary:
	var view := get_tree().root if is_inside_tree() else (Engine.get_main_loop() as SceneTree).root
	var out := {"max_fps": Engine.max_fps}
	if three_d:
		out["scaler"] = SCALERS.find_key(view.scaling_3d_mode)
		out["scale"] = snappedf(view.scaling_3d_scale, 0.001)
		out["msaa"] = MSAA.find_key(view.msaa_3d)
		out["taa"] = view.use_taa
		out["fxaa"] = view.screen_space_aa == Viewport.SCREEN_SPACE_AA_FXAA
		out["shadows"] = view.positional_shadow_atlas_size
		var on := []
		for env in _environments:
			for effect in _used[env]:
				on.append(env.get(effect))
		if not on.is_empty():
			out["effects"] = on.all(func(v: bool) -> bool: return v)
	else:
		out["stretch"] = STRETCH.find_key(view.content_scale_mode)
		out["integer"] = view.content_scale_stretch == Window.CONTENT_SCALE_STRETCH_INTEGER
	return out
