// The project the window's live tests open: a line, a picture with its last gate, a loop
// made the real way and an open revision, under a root of its own.

import { spawnSync } from 'node:child_process'
import { mkdir, writeFile } from 'node:fs/promises'
import { join } from 'node:path'

import { expect } from 'vitest'

/** A 2x2 picture, the smallest the window has to carry across and draw. */
export const PNG =
  'iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAABytg0kAAAAFklEQVR4nGP4z8DwnwEJMGHjEcEFABQ7Av8bS6RhAAAAAElFTkSuQmCC'

/** Lay the project out at `root/starship`, and return its folder. */
export async function starship(root: string): Promise<string> {
  const game = join(root, 'starship')
  await mkdir(join(game, 'text'), { recursive: true })
  await writeFile(
    join(game, 'polyweave.toml'),
    '[words]\ntable = "text/strings.csv"\n\n[paths]\naudio = "audio"\n\n' +
      '[sound.music]\nkind = "loop"\nformat = "wav"\ncues = ["calm"]\n',
  )
  await writeFile(join(game, 'text', 'strings.csv'), 'keys,en\nTITLE,Starship\nSTART,Go\n')
  // A picture where the project keeps its renders, with no record: listed, and shown.
  await mkdir(join(game, 'docs', 'renders'), { recursive: true })
  await writeFile(join(game, 'docs', 'renders', 'icon.png'), Buffer.from(PNG, 'base64'))
  // The last gate that weighed it, the icon kept and another refused.
  await mkdir(join(game, '.polyweave'), { recursive: true })
  await writeFile(
    join(game, '.polyweave', 'gates.jsonl'),
    JSON.stringify({
      id: 'g1',
      candidates: [
        { picture: 'docs/renders/icon.png', passed: true, failed: [] },
        { picture: 'docs/renders/other.png', passed: false, failed: ['edge drifted'] },
      ],
    }) + '\n',
  )
  // A loop, made the real way: an effect named as a cue a loop family declares.
  await mkdir(join(game, 'audio'), { recursive: true })
  await writeFile(join(game, 'audio', 'fx.sfx.toml'), '[effect.calm]\ngenerator = "pickup"\n')
  const made = spawnSync('python', ['-m', 'polyweave', 'sound.synth', '--source', 'audio/fx.sfx.toml', '--root', game])
  expect(made.status, made.stderr?.toString()).toBe(0)
  // A change a person asked for, still open.
  const asked = spawnSync('python', ['-m', 'polyweave', 'revision.ask', '--item', 'line:TITLE', '--words', 'shorter', '--root', game])
  expect(asked.status, asked.stderr?.toString()).toBe(0)
  return game
}
