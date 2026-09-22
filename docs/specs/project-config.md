# The project config

Binds **PW5**, and is read by every other spec here.

`polyweave.toml` at the project root. Everything the plugin would otherwise have to know
about a particular repository lives in this one file, and the plugin ships a default for all
of it. **A default that cannot be overridden is a defect.**

## Resolution order

Explicit call argument, then `polyweave.toml`, then the plugin default — evaluated **on every
call**, never cached at startup, so correcting this file does not need a session restart. The
file is read on each resolution rather than held; it is a few hundred bytes of TOML, and the
read is cheaper than the round trip a stale value costs.

**An unknown table or key is refused, never ignored**, with the near match named. A setting
that is silently dropped is one the caller believes is in effect and is not, which is the
same defect as a dropped argument (§3 of [tool-surface.md](tool-surface.md)). A value of the
wrong type is refused the same way.

**A table keyed by names the project chooses replaces the default rather than merging with
it.** `[render] samples` is keyed by `rungs`, so a project that renames its rungs would
otherwise inherit sample counts for rungs it does not have.

## The file

```toml
[project]
name = "cottony"
root = "."                      # everything below is relative to this

[paths]
blender  = "C:/Program Files/Blender Foundation/Blender 4.2/blender.exe"
godot    = "${GODOT}"           # an env var reference, resolved per call
meshes   = "tools/art/3d"
renders  = "docs/design/art"
specs    = "docs/design/accept"
work     = ".polyweave"

[render]
rungs        = ["sphere", "preview", "final"]
preview_size = 256
final_size   = 1024
samples      = { sphere = 32, preview = 64, final = 512 }
seed         = 20260922
max_parallel = 4

[tolerance]
alpha_floor      = 0.02        # what counts as a subject pixel
render_noise     = 0.004       # below this, two renders are the same picture
silhouette_iou   = 0.97
delta_e          = 2.0

[cache]
max_bytes = 8_000_000_000

[service]
base    = "https://api.meshy.ai"
key_env = "MESHY_API_KEY"      # the NAME of the variable, never the value

[budget]
credits = 60
expires = "2026-12-31"

[capture]
locale     = "pt_BR"
resolution = [1920, 1080]
declared   = ["locale", "resolution", "theme"]

[geometry]
outlines = "tools/art/outlines.py"   # where named shape generators come from
```

## Rules that are not defaults

**A secret is named, never stored.** `key_env` holds the name of an environment variable. A
config file carrying an API key is a config file that gets committed.

**Only a binary path may be absolute.** Everything else resolves under `[project] root`,
because a path pointing outside the tree is state a colleague cannot reproduce.

**Nothing is written outside the tree.** `[paths] work` is the only writable location the
plugin chooses for itself, and it belongs in `.gitignore`.

**`[budget]` is a person's decision, written down.** The plugin spends against it without
asking and refuses the call that would exceed it (§PW18). An expired or absent budget means
no spend at all, not an unlimited one — the absence of a ceiling is never read as permission.
**Credits without an expiry are not spendable either**, for the same reason: a ceiling with
no date is one nobody revisits, and an unbounded-in-time budget is not a decision anybody
made. Both halves are stated or nothing is spent.

**`[capture] declared` is the list that matters.** Every name in it is an environment setting
a capture must state explicitly, and a capture leaving one to chance is refused. §PW25 is why:
the same script on two machines produced two different images because the game read its
language from the machine and nothing said which language the picture was in.

## Adding a key

A new key here is the cheap answer to "Cottony needs X and no other project would". The
expensive answer is a change inside the plugin, and PW36 is the line that measures how often
the cheap one was enough. The list of keys that had to be added during that adoption is the
plugin's real interface, discovered rather than designed.
