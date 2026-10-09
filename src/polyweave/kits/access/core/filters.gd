extends RefCounted
## The colourblind filters (polyweave kit "access", §PW355): Machado, Oliveira and
## Fernandes (2009) at full severity for what a protanope, deuteranope and tritanope
## see, and Daltonize's correction, which moves the colour error a deficiency hides into
## the channels it leaves. Both act in linear light. The screen shader, filter.gdshader,
## is given these rows as uniforms, so the proof's sums and the screen are one set of
## numbers.

const DEFICIENCIES := ["protanopia", "deuteranopia", "tritanopia"]
## what each deficiency sees, a row per output channel
const SIMULATE := {
	"protanopia": [Vector3(0.152286, 1.052583, -0.204868), Vector3(0.114503, 0.786281, 0.099216),
		Vector3(-0.003882, -0.048116, 1.051998)],
	"deuteranopia": [Vector3(0.367322, 0.860646, -0.227968), Vector3(0.280085, 0.672501, 0.047413),
		Vector3(-0.011820, 0.042940, 0.968881)],
	"tritanopia": [Vector3(1.255528, -0.076749, -0.178779), Vector3(-0.078411, 0.930809, 0.147602),
		Vector3(0.004733, 0.691367, 0.303900)],
}
## where the hidden error goes: none to red, into green and blue
const SHIFT := [Vector3(0, 0, 0), Vector3(0.7, 1, 0), Vector3(0.7, 0, 1)]
const SHADER := "res://addons/polyweave/access/filter.gdshader"


static func _rows(rows: Array, c: Vector3) -> Vector3:
	return Vector3(rows[0].dot(c), rows[1].dot(c), rows[2].dot(c))


static func _linear(c: Color) -> Vector3:
	var lin := c.srgb_to_linear()
	return Vector3(lin.r, lin.g, lin.b)


static func _colour(v: Vector3) -> Color:
	return Color(clampf(v.x, 0, 1), clampf(v.y, 0, 1), clampf(v.z, 0, 1)).linear_to_srgb()


## what a player with this deficiency sees of a colour
static func simulate(c: Color, deficiency: String) -> Color:
	return _colour(_rows(SIMULATE[deficiency], _linear(c)))


## the colour the correction for this deficiency puts on screen
static func correct(c: Color, deficiency: String) -> Color:
	var lin := _linear(c)
	var error := lin - _rows(SIMULATE[deficiency], lin)
	return _colour(lin + _rows(SHIFT, error))


## what a player with this deficiency sees with its correction on
static func seen(c: Color, deficiency: String) -> Color:
	return simulate(correct(c, deficiency), deficiency)


## the screen filter for a deficiency: its correction, or with `simulating`, what the
## deficiency sees, for a person previewing the game as such a player would
static func material(deficiency: String, simulating := false) -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = load(SHADER)
	var rows: Array = SIMULATE[deficiency]
	for i in 3:
		made.set_shader_parameter("sim%d" % i, rows[i])
		made.set_shader_parameter("shift%d" % i, SHIFT[i])
	made.set_shader_parameter("correcting", not simulating)
	return made
