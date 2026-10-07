import { describe, expect, it } from 'vitest'

import { engine, type Probe } from './engine'

const probe = (present: string[]): Probe => ({
  exists: async (path) => present.includes(path),
  join: (...parts) => parts.join('/'),
})

describe('which polyweave serves a project', () => {
  it("prefers the project's own environment", async () => {
    const found = await engine(probe(['/g/starship/.venv/bin/python']), '/g/starship')
    expect(found).toEqual({
      command: '/g/starship/.venv/bin/python',
      args: ['-m', 'polyweave', 'serve'],
      from: 'project',
    })
  })

  it('falls back to the PATH, and says so', async () => {
    const found = await engine(probe([]), '/g/starship')
    expect(found.command).toBe('python')
    expect(found.from).toBe('path')
  })
})
