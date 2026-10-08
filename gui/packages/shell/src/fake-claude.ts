// A `claude` that is not Claude, for testing the half of a session the window owns.
//
// A real session costs the person's usage and does work, so no test starts one. This is a
// Node script that speaks the stream-json the Agent SDK speaks to Claude Code: it answers
// `initialize`, says each message back, asks one permission, and ends each turn with a
// result naming the answer it was given. It exits only when its input closes, as a real
// one does. What it cannot prove is that Claude Code still speaks this way.

import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

export interface FakeClaude {
  /** As POLYWEAVE_AGENT takes it: this Node, then the script. */
  argv: string[]
  dispose(): void
}

const SCRIPT = String.raw`
import { createInterface } from 'node:readline'
const write = (value) => process.stdout.write(JSON.stringify(value) + '\n')
let asked = false
const input = createInterface({ input: process.stdin })
input.on('line', (line) => {
  const message = JSON.parse(line)
  if (message.type === 'control_request' && message.request.subtype === 'initialize') {
    write({ type: 'control_response', response: { subtype: 'success', request_id: message.request_id, response: {} } })
    return
  }
  if (message.type === 'user') {
    const content = message.message.content
    const text = typeof content === 'string' ? content : content.map((p) => p.text ?? '').join('')
    if (!asked) write({ type: 'system', subtype: 'init', cwd: process.cwd(), session_id: 'fake-1', tools: ['Write'] })
    write({ type: 'assistant', message: { role: 'assistant', content: [{ type: 'text', text }] }, session_id: 'fake-1' })
    if (!asked) {
      asked = true
      write({ type: 'control_request', request_id: 'ask-1', request: { subtype: 'can_use_tool', tool_name: 'Write', input: { file_path: 'art/icon.png' }, tool_use_id: 'use-1' } })
    } else {
      // Says back what it was started under, so a test sees the harness arrive.
      const flag = (name) => { const at = process.argv.indexOf(name); return at < 0 ? null : process.argv[at + 1] }
      const heard = 'heard' + (flag('--settings') ? ' with settings' : '') + (flag('--disallowedTools') ? ' denying ' + flag('--disallowedTools') : '')
      write({ type: 'result', subtype: 'success', is_error: false, result: heard, num_turns: 2, duration_ms: 1, session_id: 'fake-1' })
    }
    return
  }
  if (message.type === 'control_response') {
    const answer = message.response.response
    write({ type: 'result', subtype: 'success', is_error: false, result: answer.behavior, num_turns: 1, duration_ms: 1, session_id: 'fake-1' })
  }
})
input.on('close', () => process.exit(0))
`

export function fakeClaude(): FakeClaude {
  const home = mkdtempSync(join(tmpdir(), 'pw-fake-claude-'))
  const file = join(home, 'claude.mjs')
  writeFileSync(file, SCRIPT, 'utf8')
  return {
    argv: [process.execPath, file],
    dispose: () => rmSync(home, { recursive: true, force: true }),
  }
}
