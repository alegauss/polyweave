import { describe, expect, it } from 'vitest'

import type { Item } from '@pw/core'

import { offered, viewer } from './ItemView'
import { kept } from './Project'

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
})
