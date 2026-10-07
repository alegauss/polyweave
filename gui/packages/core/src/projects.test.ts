import { describe, expect, it } from 'vitest'

import { find, type Lister } from './projects'

/** A disk in memory: each folder's entries, a trailing slash marking a folder. */
function disk(tree: Record<string, string[]>, locked: string[] = []): Lister {
  return {
    async list(path) {
      if (locked.includes(path)) {
        throw new Error('EACCES')
      }
      return (tree[path] ?? []).map((name) => ({
        name: name.replace(/\/$/, ''),
        directory: name.endsWith('/'),
      }))
    },
    join: (...parts) => parts.join('/'),
  }
}

describe('finding projects', () => {
  const tree = {
    '/g': ['starship/', 'cottony/', 'notes.txt', '.hidden/', 'node_modules/', 'deep/'],
    '/g/starship': ['polyweave.toml', 'tools/'],
    '/g/starship/tools': ['inner/'],
    '/g/starship/tools/inner': ['polyweave.toml'],
    '/g/cottony': ['polyweave.toml'],
    '/g/.hidden': ['polyweave.toml'],
    '/g/node_modules': ['polyweave.toml'],
    '/g/deep': ['er/'],
    '/g/deep/er': ['polyweave.toml'],
  }

  it('finds each folder holding polyweave.toml, within the depth named', async () => {
    expect(await find(disk(tree), '/g', 1)).toEqual(['/g/cottony', '/g/starship'])
    expect(await find(disk(tree), '/g', 2)).toEqual(['/g/cottony', '/g/deep/er', '/g/starship'])
  })

  it('looks at the root alone at depth zero', async () => {
    expect(await find(disk(tree), '/g', 0)).toEqual([])
    expect(await find(disk(tree), '/g/cottony', 0)).toEqual(['/g/cottony'])
  })

  it('passes over a folder it cannot read and goes on', async () => {
    expect(await find(disk(tree, ['/g/cottony']), '/g', 1)).toEqual(['/g/starship'])
  })
})
