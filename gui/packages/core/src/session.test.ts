import { describe, expect, it } from 'vitest'

import { opening, said } from './session'

const revision = {
  revision: 'r1',
  item: 'art/icon.png',
  digest: '0123456789abcdef',
  words: 'a warmer rim',
  mask: '.polyweave/marks/rim.png',
}

describe('a session on one item', () => {
  it('opens with the revision and the brief, never a freehand prompt', () => {
    const first = opening(revision, {
      spec: {
        path: 'specs/icon.accept.toml',
        predicates: [{ id: 'warm', measure: 'hue_p50', min: { value: 20, origin: 'person' }, max: 40 }],
      },
      dependents: [{ artefact: 'docs/renders/sheet.png' }],
    })
    expect(first).toContain('Revision r1')
    expect(first).toContain('Item: art/icon.png')
    expect(first).toContain('digest 0123456789abcdef')
    expect(first).toContain('What they said: a warmer rim')
    expect(first).toContain('the mask .polyweave/marks/rim.png')
    expect(first).toContain('- warm: hue_p50 >= 20 (person), <= 40')
    expect(first).toContain('- docs/renders/sheet.png')
    expect(first).toContain('never with a verdict of your own')
  })

  it('says so when no spec holds the item, or it moved since the request', () => {
    const first = opening({ ...revision, moved: true }, { spec: null, dependents: [] })
    expect(first).toContain('No spec holds it yet.')
    expect(first).toContain('the item has changed since')
  })

  it('reads each line the screen draws, and anything else as other', () => {
    expect(said('{"type":"system","subtype":"init","session_id":"s1"}')).toEqual({ kind: 'started', session: 's1' })
    expect(said('{"type":"assistant","message":{"content":[{"type":"text","text":"On it."}]}}')).toEqual({
      kind: 'text',
      text: 'On it.',
    })
    expect(
      said('{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Bash","input":{"command":"ls"}}]}}'),
    ).toEqual({ kind: 'tool', tool: 'Bash', input: { command: 'ls' } })
    expect(
      said('{"type":"control_request","request_id":"q1","request":{"subtype":"can_use_tool","tool_name":"Write","input":{}}}'),
    ).toEqual({ kind: 'ask', requestId: 'q1', tool: 'Write', input: {} })
    expect(said('{"type":"result","is_error":false,"result":"done"}')).toEqual({ kind: 'result', ok: true, text: 'done' })
    expect(said('not json')).toEqual({ kind: 'other' })
  })
})
