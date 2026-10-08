// A Claude Code session opened on one item (§PW306): what it is handed first, and how
// the window reads what it says. Pure: the process that runs it is the shell's.

/** One open revision, as `revision.open` lists it. */
export interface Revision {
  revision: string
  item: string
  digest: string | null
  words: string
  mask?: string
  span?: number[]
  moved?: boolean
}

/** The predicates `asset.brief` reads back, each with its bounds. */
interface Predicate {
  id: string
  measure: string
  min?: unknown
  max?: unknown
}

function bound(side: unknown): string {
  if (side === null || side === undefined) return ''
  if (typeof side === 'object') {
    const value = (side as Record<string, unknown>)['value']
    const origin = (side as Record<string, unknown>)['origin']
    return origin ? `${String(value)} (${String(origin)})` : String(value)
  }
  return String(side)
}

/**
 * The session's first message, built from the revision and the item's brief and never
 * written freehand: the item, the digest the person saw, their words, where they marked,
 * the bar it is held to, and what depends on it.
 */
export function opening(revision: Revision, brief: Record<string, unknown>): string {
  const lines = [
    `A person asked for a change to one item of this polyweave project, and this session ` +
      `makes it. Revision ${revision.revision} holds the request; close it with ` +
      `revision.close once a run and a sitting answer it, never with a verdict of your own.`,
    '',
    `Item: ${revision.item}`,
    `What they were looking at: digest ${revision.digest ?? 'none'}${
      revision.moved ? ' (the item has changed since)' : ''
    }`,
    `What they said: ${revision.words}`,
  ]
  if (revision.mask) lines.push(`Where: the mask ${revision.mask}, black where the change is wanted`)
  if (revision.span?.length === 2) {
    lines.push(`When: from ${revision.span[0]} s to ${revision.span[1]} s`)
  }
  const spec = brief['spec'] as { path?: string; predicates?: Predicate[] } | null | undefined
  if (spec?.predicates?.length) {
    lines.push('', `The bar it is held to (${spec.path ?? 'its spec'}):`)
    for (const p of spec.predicates) {
      const sides = [p.min !== undefined ? `>= ${bound(p.min)}` : '', p.max !== undefined ? `<= ${bound(p.max)}` : '']
      lines.push(`- ${p.id}: ${p.measure} ${sides.filter(Boolean).join(', ')}`.trimEnd())
    }
  } else {
    lines.push('', 'No spec holds it yet.')
  }
  const dependents = (brief['dependents'] as { artefact: string }[] | undefined) ?? []
  if (dependents.length) {
    lines.push('', 'Made from it, so a change reaches these too:')
    for (const one of dependents) lines.push(`- ${one.artefact}`)
  }
  lines.push('', `Start with asset.brief --asset ${revision.item}, then make the change.`)
  return lines.join('\n')
}

/** One line of a session, read for the screen; the raw line always travels beside it. */
export type Said =
  | { kind: 'started'; session: string }
  | { kind: 'text'; text: string }
  | { kind: 'tool'; tool: string; input: unknown }
  | { kind: 'ask'; requestId: string; tool: string; input: unknown }
  | { kind: 'withdrawn'; requestId: string }
  | { kind: 'result'; ok: boolean; text: string }
  | { kind: 'check'; passed: boolean | null; said: string }
  | { kind: 'answered'; said: string }
  | { kind: 'closed'; sitting: string }
  | { kind: 'other' }

/** A session's line as the screen draws it. A line that is not JSON reads as `other`. */
export function said(line: string): Said {
  let message: Record<string, any>
  try {
    message = JSON.parse(line)
  } catch {
    return { kind: 'other' }
  }
  switch (message['type']) {
    case 'system':
      return message['subtype'] === 'init'
        ? { kind: 'started', session: String(message['session_id'] ?? '') }
        : { kind: 'other' }
    case 'assistant': {
      const parts = (message['message']?.['content'] ?? []) as Record<string, any>[]
      const text = parts.filter((p) => p['type'] === 'text').map((p) => p['text']).join('')
      if (text) return { kind: 'text', text }
      const used = parts.find((p) => p['type'] === 'tool_use')
      return used ? { kind: 'tool', tool: String(used['name']), input: used['input'] } : { kind: 'other' }
    }
    case 'control_request':
      return message['request']?.['subtype'] === 'can_use_tool'
        ? {
            kind: 'ask',
            requestId: String(message['request_id']),
            tool: String(message['request']['tool_name']),
            input: message['request']['input'],
          }
        : { kind: 'other' }
    case 'control_cancel_request':
      return { kind: 'withdrawn', requestId: String(message['request_id']) }
    case 'result':
      return { kind: 'result', ok: message['is_error'] !== true, text: String(message['result'] ?? '') }
    case 'polyweave_answer':
      return { kind: 'answered', said: String(message['said'] ?? '') }
    case 'polyweave_closed':
      return { kind: 'closed', sitting: String(message['sitting'] ?? '') }
    case 'polyweave_check':
      // The window's own line: the item's checks after a change (§PW307).
      return {
        kind: 'check',
        passed: message['passed'] === null ? null : message['passed'] === true,
        said: String(message['said'] ?? ''),
      }
    default:
      return { kind: 'other' }
  }
}

/** The person's answer on the sitting a revision ended in, as `revision.open` reads it. */
export interface Answer {
  choice: string
  why?: string | null
  at?: string | null
}

/**
 * What a revision does with the person's answer (§PW307): an accept closes it with its
 * run and sitting; anything else, a look or a number, goes back to the same session as
 * its next turn, in the person's own words.
 */
export function followUp(answer: Answer): { close: true } | { close: false; say: string } {
  if (answer.choice === 'accept') return { close: true }
  const why = answer.why?.trim()
  return {
    close: false,
    say:
      `The person answered "${answer.choice}" on the sitting` +
      (why ? `: ${why}` : ', with no comment') +
      '. Change the item again from there, run its checks, and lay a new sitting out.',
  }
}
