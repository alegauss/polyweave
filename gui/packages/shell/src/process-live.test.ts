// The pipe itself, against a node process standing in for the server.

import { describe, expect, it } from 'vitest'

import { served } from './process'

const node = (script: string) => ({ command: process.execPath, args: ['-e', script], from: 'path' as const })

describe('a served process', () => {
  it('splits what it writes into lines, however the chunks fall', async () => {
    const echo = served(
      node("process.stdout.write('one\\ntw'); setTimeout(() => process.stdout.write('o\\r\\nthree\\n'), 50)"),
      '.',
    )
    const lines: string[] = []
    echo.onLine((line) => lines.push(line))
    await echo.exited
    expect(lines).toEqual(['one', 'two', 'three'])
  })

  it('keeps what it wrote to stderr and says how it exited', async () => {
    const dying = served(node("process.stderr.write('Traceback: boom'); process.exit(3)"), '.')
    expect(await dying.exited).toBe(3)
    expect(dying.stderr()).toContain('boom')
  })
})
