shader_type spatial;
// The cube `VoxelDraw` gives each cell unless a game names its own shader (§PW235).
// INSTANCE_CUSTOM carries the cell's palette colour, and its material's `glow` in alpha;
// `wash` and `fade` are the node's own, set by `VoxelDraw.wash` and `.fade`, since the
// MultiMesh under every node drawing one file is shared. A game's shader reading the
// same three inputs replaces this one whole.

// a colour laid over every cell, its alpha how far
instance uniform vec4 wash : source_color = vec4(0.0);
// 0 whole, 1 gone; dithered, so a faded model stays in the opaque pass
instance uniform float fade = 0.0;

varying vec4 tint;

void vertex() {
	tint = INSTANCE_CUSTOM;
}

void fragment() {
	vec3 color = mix(tint.rgb, wash.rgb, wash.a);
	ALBEDO = color;
	EMISSION = color * tint.a;
	ALPHA = 1.0 - fade;
	ALPHA_HASH_SCALE = 1.0;
}
