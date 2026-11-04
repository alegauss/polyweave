import { describe, expect, it } from 'vitest'

import type { Item } from '@pw/core'

import { offered, shown, viewer } from './ItemView'
import { kept, LIST, matching, NARROWEST, resized, ROW, tabs, windowed } from './Project'

const item = (over: Partial<Item>): Item => ({
  id: 'x',
  kind: 'mesh',
  declaration: null,
  artefact: null,
  record: 'sound',
  pending: false,
  digest: null,
  ...over,
})

describe('an item seen', () => {
  it('draws a picture, a sound and a line itself', () => {
    expect(viewer(item({ kind: 'picture', artefact: 'a/b.png' }))).toBe('picture')
    expect(viewer(item({ kind: 'sound', artefact: 'a/hit.wav' }))).toBe('sound')
    expect(viewer(item({ kind: 'line', id: 'line:TITLE' }))).toBe('line')
  })

  it('offers the operation that would draw what it does not, never runs it', () => {
    const mesh = item({ kind: 'mesh', id: 'a.glb', artefact: 'a.glb' })
    expect(viewer(mesh)).toBe('operation')
    expect(offered(mesh)).toBe('shape.turntable --mesh a.glb --out review/a.glb.turntable')
    expect(offered(item({ kind: 'mesh', id: 's.toml', declaration: 's.toml' }))).toBe(
      'geometry.build --source s.toml',
    )
    expect(offered(item({ kind: 'clip', declaration: 'walk.clip.toml' }))).toBe(
      'clip.read --path walk.clip.toml',
    )
  })

  it('narrows the list to what waits on a person or needs attention', () => {
    const rows = [
      item({ id: 'a', pending: true }),
      item({ id: 'b', record: 'outdated' }),
      item({ id: 'c' }),
    ]
    expect(kept(rows, 'pending').map((r) => r.id)).toEqual(['a'])
    expect(kept(rows, 'attention').map((r) => r.id)).toEqual(['b'])
    expect(kept(rows, 'all')).toHaveLength(3)
    expect(kept(rows, 'revision', ['c']).map((r) => r.id)).toEqual(['c'])
  })

  it('draws a tab per kind the payload counts, summing to the inventory before every page is read', () => {
    const read = [item({ id: 'a.glb' }), item({ id: 'b.glb' })]
    const kinds = { mesh: 156, picture: 1500, line: 363 }
    const drawn = tabs(read, kinds, false)
    expect(drawn.map((tab) => tab.kind)).toEqual(['mesh', 'picture', 'line'])
    expect(drawn.reduce((sum, tab) => sum + tab.count, 0)).toBe(2019)
  })

  it('counts what is left once narrowed, and draws no tab for a kind with none', () => {
    const rows = [
      item({ id: 'art/ship.glb' }),
      item({ id: 'art/ship.png', kind: 'picture' }),
      item({ id: 'line:SHIP', kind: 'line' }),
    ]
    const found = matching(rows, ' SHIP.png ')
    expect(found.map((r) => r.id)).toEqual(['art/ship.png'])
    expect(tabs(found, { mesh: 1, picture: 1, line: 1 }, true)).toEqual([{ kind: 'picture', count: 1 }])
    expect(matching(rows, '')).toBe(rows)
  })

  it('draws a screenful of a long kind, not every row', () => {
    expect(windowed(2019, 0, 720)).toEqual({ from: 0, to: 720 / ROW + 10 })
    const deep = windowed(2019, 100 * ROW, 720)
    expect(deep.from).toBe(90)
    expect(deep.to).toBe(100 + 720 / ROW + 10)
    expect(windowed(5, 0, 720)).toEqual({ from: 0, to: 5 })
    expect(windowed(5, 9999, 720).to - windowed(5, 9999, 720).from).toBeGreaterThanOrEqual(0)
    // A view not measured yet is taken as one screen, never as none.
    expect(windowed(2019, 0, 0).to).toBeGreaterThan(0)
  })

  it('fits a picture inside the panel unless its real size is asked for', () => {
    expect(shown(false)).toContain('max-w-full')
    expect(shown(false)).toContain('max-h-[50vh]')
    expect(shown(true)).toBe('max-w-none')
  })

  it('lets the list be dragged wider or narrower, never past what leaves the item room', () => {
    expect(resized(LIST, 3840)).toBe(LIST)
    expect(resized(10, 3840)).toBe(NARROWEST)
    expect(resized(5000, 3840)).toBe(Math.floor(3840 * 0.6))
    // A window too narrow to share still gives the list its narrowest.
    expect(resized(5000, 300)).toBe(NARROWEST)
  })
})
