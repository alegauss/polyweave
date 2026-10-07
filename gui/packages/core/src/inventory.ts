// Everything a project governs, read through `project.inventory` (§PW299). The row
// format is docs/specs/inventory.md; this side checks a row has it and adds nothing.

import type { Client } from './client'

export const KINDS = ['mesh', 'picture', 'sound', 'music', 'vfx', 'clip', 'line', 'capture'] as const
export type Kind = (typeof KINDS)[number]

export type RecordState =
  | 'sound'
  | 'changed'
  | 'missing'
  | 'outdated'
  | 'unrecorded'
  | 'unbuilt'
  | null

export interface Item {
  id: string
  kind: Kind
  declaration: string | null
  artefact: string | null
  record: RecordState
  pending: boolean
  digest: string | null
}

export interface Page {
  items: Item[]
  total: number
  kinds: Partial<Record<Kind, number>>
  next: number | null
}

/** The payload was not the shape the spec says; a server older or newer than this. */
export class Unreadable extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'Unreadable'
  }
}

function item(row: unknown, at: number): Item {
  const r = row as Record<string, unknown>
  const text = (key: string) => {
    const value = r[key]
    if (value !== null && typeof value !== 'string') {
      throw new Unreadable(`item ${at} has a ${key} that is neither text nor null`)
    }
    return value as string | null
  }
  if (typeof r['id'] !== 'string' || !KINDS.includes(r['kind'] as Kind)) {
    throw new Unreadable(`item ${at} has no id, or a kind this window does not know`)
  }
  return {
    id: r['id'],
    kind: r['kind'] as Kind,
    declaration: text('declaration'),
    artefact: text('artefact'),
    record: text('record') as RecordState,
    pending: r['pending'] === true,
    digest: text('digest'),
  }
}

/** One page of the inventory, checked against the row format. */
export async function page(
  client: Client,
  root: string,
  ask: { kind?: Kind; offset?: number; limit?: number } = {},
): Promise<Page> {
  const answer = (await client.call('project.inventory', { root, ...ask })) as Record<string, unknown>
  if (!Array.isArray(answer['items']) || typeof answer['total'] !== 'number') {
    throw new Unreadable('project.inventory answered without items and a total')
  }
  const next = answer['next']
  return {
    items: answer['items'].map(item),
    total: answer['total'],
    kinds: (answer['kinds'] ?? {}) as Page['kinds'],
    next: typeof next === 'number' ? next : null,
  }
}

/** Every item, page after page, until the server says there is no next. */
export async function all(client: Client, root: string, kind?: Kind): Promise<Item[]> {
  const items: Item[] = []
  let offset: number | null = 0
  while (offset !== null) {
    const read: Page = await page(client, root, { ...(kind ? { kind } : {}), offset })
    items.push(...read.items)
    offset = read.next
  }
  return items
}
