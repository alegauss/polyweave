// The colourblind filter over the whole screen (polyweave kit "access", §PW355). Its
// rows come from filters.gd, so what the proof sums is what this draws.
shader_type canvas_item;

uniform sampler2D screen : hint_screen_texture, filter_nearest;
uniform vec3 sim0;
uniform vec3 sim1;
uniform vec3 sim2;
uniform vec3 shift0;
uniform vec3 shift1;
uniform vec3 shift2;
uniform bool correcting = true;

vec3 linear(vec3 c) {
	return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(0.04045, c));
}

vec3 encoded(vec3 c) {
	return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(0.0031308, c));
}

vec3 rows(vec3 r0, vec3 r1, vec3 r2, vec3 c) {
	return vec3(dot(r0, c), dot(r1, c), dot(r2, c));
}

void fragment() {
	vec3 c = linear(texture(screen, SCREEN_UV).rgb);
	vec3 seen = rows(sim0, sim1, sim2, c);
	vec3 shown = correcting ? c + rows(shift0, shift1, shift2, c - seen) : seen;
	COLOR = vec4(encoded(clamp(shown, 0.0, 1.0)), 1.0);
}
