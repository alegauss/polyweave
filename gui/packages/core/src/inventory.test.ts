import { describe, expect, it } from 'vitest'

import type { Client } from './client'
import { all, page, Unreadable } from './inventory'

const row = (id: string, kind = 'mesh') => ({
  id,
  kind,
  declaration: null,
  artefact: id,
  record: 'sound',
  pending: false,
  digest: '0123456789abcdef',
})

/** A client whose project.inventory pages through `rows`, `limit` at a time. */
function holding(rows: unknown[], limit = 2) {
  const asked: Record<string, unknown>[] = []
  const client = {
    async call(operation: string, args: Record<string, unknown>) {
      expect(operation).toBe('project.inventory')
      asked.push(args)
      const offset = Number(args['offset'] ?? 0)
      const items = rows.slice(offset, offset + limit)
      const more = offset + items.length < rows.length
      return { items, total: rows.length, kinds: { mesh: rows.length }, next: more ? offset + items.length : null }
    },
  } as unknown as Client
  return { client, asked }
}

describe('the inventory', () => {
  it('reads a page as the row format says', async () => {
    const { client, asked } = holding([row('a.glb'), row('b.glb'), row('c.glb')])
    const read = await page(client, '/g', { kind: 'mesh' })
    expect(read.items.map((i) => i.id)).toEqual(['a.glb', 'b.glb'])
    expect(read.next).toBe(2)
    expect(asked[0]).toEqual({ root: '/g', kind: 'mesh' })
  })

  it('reads every page until there is no next', async () => {
    const { client } = holding([row('a.glb'), row('b.glb'), row('c.glb')])
    expect((await all(client, '/g')).map((i) => i.id)).toEqual(['a.glb', 'b.glb', 'c.glb'])
  })

  it('refuses a row of a kind it does not know rather than drawing it wrong', async () => {
    const { client } = holding([row('a.glb', 'hologram')])
    await expect(page(client, '/g')).rejects.toBeInstanceOf(Unreadable)
  })

  it('refuses an answer with no items', async () => {
    const client = { call: async () => ({ rows: [] }) } as unknown as Client
    await expect(page(client, '/g')).rejects.toBeInstanceOf(Unreadable)
  })

  it('keeps the rows that did not move, and names the ones whose digest did', async () => {
    const { merged } = await import('./inventory')
    const a = { ...row('a.glb'), digest: '1' }
    const b = { ...row('b.glb'), digest: '1' }
    const fresh = [{ ...a }, { ...b, digest: '2' }, row('c.glb')]
    const folded = merged([a as never, b as never], fresh as never)
    expect(folded.items[0]).toBe(a)
    expect(folded.items[1]).not.toBe(b)
    expect(folded.moved).toEqual(['b.glb'])
    expect(folded.items.map((i) => i.id)).toEqual(['a.glb', 'b.glb', 'c.glb'])
  })
})
