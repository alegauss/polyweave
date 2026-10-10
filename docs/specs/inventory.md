# The inventory

Binds **PW299**, and the lines of Block U that read it: the desktop window's tree,
`asset.brief` and the revision record. One read lists every item a project governs, by
kind, so neither an agent nor a window has to walk the tree to find out what is there.

`project.inventory(root, kind="", offset=0, limit=200)`, and `python -m polyweave
project.inventory` on the command line. It writes nothing and is never refused over what
the project holds. A kind the project does not use is simply absent.

## The answer

```json
{
  "items": [
    {
      "id": "assets/barrel.glb",
      "kind": "mesh",
      "declaration": "shapes/barrel.toml",
      "artefact": "assets/barrel.glb",
      "record": "sound",
      "pending": false,
      "digest": "4f1c0a9e2b7d3c61"
    }
  ],
  "total": 41,
  "kinds": {"mesh": 12, "picture": 20, "line": 9},
  "next": 200
}
```

`items` is one page of the rows the filter selects, sorted by kind in the order below
and then by id. `total` counts what the filter selects, and `kinds` counts the whole
project whatever the filter, so one read says what else is there. `next` is the `offset`
that reads the following page, and `null` on the last one.

## A row

**`id`** is stable while the item is the same item. It is the artefact's path, relative to
the project with forward slashes. For a declaration not built yet it is the declaration's
path, and for a line it is `line:<key>`, the key the string table gives it.

**`kind`** is one of `mesh`, `picture`, `sound`, `music`, `vfx`, `clip`, `line` and
`capture`, in that order. It is read from what made the artefact: the record's own kind,
`music` where `music.render` made the sound, `clip` where the mesh carries an animation
or the scene is a camera clip `clip.camera` built.
It is read from the file's suffix only where the record does not settle it.

**`declaration`** is the file the item was declared by, where it has one: the first of
the record's inputs whose role is `declaration`, `effects`, `score`, `script` or `world`,
or the string table for a line. Otherwise it is `null`.

**`artefact`** is the file the game uses, or `null` where there is none yet.

**`record`** says where the provenance record stands:

| Value | Means |
|---|---|
| `sound` | the artefact is what its record says it is, and nothing it was made from has moved |
| `changed` | the artefact's bytes are not the ones its record names |
| `missing` | the record names an artefact that is not on disk |
| `outdated` | the artefact holds, and a file it was made from has changed since |
| `unrecorded` | a produced file under `[paths] meshes` or `renders` with no record |
| `unbuilt` | a geometry declaration nothing has been built from yet |
| `null` | a line, which has no record of its own |

**`pending`** is true where the item waits on a person's verdict. For an artefact that is
`loop.pending`'s answer, where it is the newest render of an asset waiting on a look. For
a line it is true while the canon holds no verdict on the line as it now reads, and it is
false where the project names no canon, because then a verdict has nowhere to be kept.

**`digest`** is the first sixteen hex digits of a hash that moves when the item does: the
artefact's SHA-256 as its record states it (as found on disk, for an unrecorded file), or
the digest of the line's text in every locale. It is `null` for an unbuilt declaration.

## Who reads it

`asset.brief` takes a row's `id` as well as an asset's name (§PW300). It answers with
the row as `item`, the artefact against its record, and the declaration read back in the
words its kind uses:

- a geometry declaration as the lines its parts read as;
- a line as its text in each locale, its speaker and the canon's latest verdict, with
  `on_this_text` false once the text has moved;
- a music cue as `music.validate` answers its score;
- an sfx or vfx effect as its own `[effect.<name>]` table, and a built vfx effect with
  what it measures. A sound's record names its effect, and one written before it did is
  matched by its file's name;
- a picture as the style family it is held to (the family it was bought for, or the
  project's only one): palette, skeleton, cell, filter, canon and how many pictures the
  canon admits.

Every brief names the artefacts made from the item as `dependents`, because a change to
it reaches them.

## What is not listed

Records under a hidden folder, such as the cache in `.polyweave/`, which hold the
project's work and not its items. A record that does not read is left out, not raised:
`provenance.verify` is the read that reports it.
