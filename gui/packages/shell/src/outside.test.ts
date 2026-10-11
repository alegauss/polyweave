import { describe, expect, it } from 'vitest'

import { said } from '@pw/core'

import { Strays, type Stray } from './outside'

const used = (id: string, name = 'Bash') =>
  JSON.stringify({ type: 'assistant', message: { content: [{ type: 'tool_use', id, name, input: {} }] } })
const result = (id: string) =>
  JSON.stringify({ type: 'user', message: { content: [{ type: 'tool_result', tool_use_id: id, content: '' }] } })

describe('a shell write outside the item', () => {
  it('is shown once, after the Bash call that made it, in the window’s own line', async () => {
    const found: Stray[] = []
    let asked = 0
    const strays = new Strays(async () => {
      asked++
      return found
    })
    expect(await strays.after(used('b1'))).toEqual([])
    found.push({ file: 'polyweave.toml', outside: "polyweave.toml is the project's config", at: 't1' })
    const lines = await strays.after(result('b1'))
    expect(lines.map(said)).toEqual([
      { kind: 'outside', file: 'polyweave.toml', why: "polyweave.toml is the project's config" },
    ])
    // The next command's result shows only what is new.
    await strays.after(used('b2'))
    expect(await strays.after(result('b2'))).toEqual([])
    expect(asked).toBe(2)
  })

  it('is never asked for after a tool that is not the shell', async () => {
    let asked = 0
    const strays = new Strays(async () => {
      asked++
      return []
    })
    await strays.after(used('w1', 'Write'))
    expect(await strays.after(result('w1'))).toEqual([])
    expect(asked).toBe(0)
  })
})
