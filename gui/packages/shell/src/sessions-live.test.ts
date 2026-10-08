// A session started through the Agent SDK, against a fake `claude` (§PW306).

import { tmpdir } from 'node:os'

import { afterEach, describe, expect, it } from 'vitest'

import { said, type Said } from '@pw/core'

import { agent, AGENT_VAR } from './agent'
import { fakeClaude, type FakeClaude } from './fake-claude'
import { start } from './sessions'

describe('a session on one item', () => {
  let fake: FakeClaude
  afterEach(() => fake?.dispose())

  it('opens with its first message, asks in the window, and hears a follow-up', async () => {
    fake = fakeClaude()
    const runs = agent({ [AGENT_VAR]: JSON.stringify(fake.argv), PATH: '' })!
    expect(runs.from).toBe('override')
    const read: Said[] = []
    let session: ReturnType<typeof start> | null = null
    const results: string[] = []
    const done = new Promise<void>((resolve) => {
      session = start(runs, tmpdir(), 'Item: art/icon.png', (line) => {
        const one = said(line)
        read.push(one)
        if (one.kind === 'ask') session!.answer(one.requestId, true)
        if (one.kind === 'result') {
          results.push(one.text)
          if (results.length === 1) session!.say('and keep the outline')
          else resolve()
        }
      })
    })
    await done
    session!.stop()
    await session!.finished
    expect(read.find((r) => r.kind === 'started')).toEqual({ kind: 'started', session: 'fake-1' })
    const texts = read.filter((r) => r.kind === 'text').map((r) => (r as { text: string }).text)
    expect(texts).toEqual(['Item: art/icon.png', 'and keep the outline'])
    expect(read.some((r) => r.kind === 'ask' && r.tool === 'Write')).toBe(true)
    expect(results).toEqual(['allow', 'heard'])
  })

  it('runs under the revision harness: its settings, and no verdict tool', async () => {
    fake = fakeClaude()
    const runs = agent({ [AGENT_VAR]: JSON.stringify(fake.argv), PATH: '' })!
    let session: ReturnType<typeof start> | null = null
    const result = await new Promise<string>((resolve) => {
      session = start(
        runs,
        tmpdir(),
        'first',
        (line) => {
          const one = said(line)
          if (one.kind === 'ask') {
            session!.answer(one.requestId, true)
            session!.say('then')
          }
          if (one.kind === 'result' && one.text.startsWith('heard')) resolve(one.text)
        },
        process.env,
        { settings: { hooks: {} }, disallowed: ['mcp__polyweave__verdict_judge'] },
      )
    })
    session!.stop()
    await session!.finished
    expect(result).toContain('with settings')
    expect(result).toContain('denying mcp__polyweave__verdict_judge')
  })
})

describe('the claude a session runs', () => {
  it("is the person's on PATH, ignoring a variable once the window is packaged", () => {
    const exists = (path: string) => path.replace(/\\/g, '/').endsWith('/bin/claude') || path.endsWith('claude.exe')
    const found = agent({ PATH: '/usr/local/bin', [AGENT_VAR]: '["/x/fake"]' }, true, '/home/p', exists)
    expect(found?.from).toBe('path')
  })

  it('is none where the machine has no claude at all', () => {
    expect(agent({ PATH: '' }, false, '/nowhere', () => false)).toBeNull()
  })
})
