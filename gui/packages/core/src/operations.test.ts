import { describe, expect, it } from 'vitest'

import { Client, type Transport } from './client'
import { call, OPERATIONS, type Operations } from './operations.generated'

/** A server in memory that answers every call with an empty payload. */
function serving() {
  const sent: Record<string, unknown>[] = []
  let listener: (line: string) => void = () => {}
  const transport: Transport = {
    send(line) {
      const message = JSON.parse(line)
      sent.push(message)
      if ('id' in message) {
        queueMicrotask(() =>
          listener(JSON.stringify({ jsonrpc: '2.0', id: message.id, result: { structuredContent: {} } })),
        )
      }
    },
    onLine(on) {
      listener = on
    },
    close() {},
  }
  return { client: new Client(transport), sent }
}

describe('the typed operations', () => {
  it('list every operation describe answered, the decision screen among them', () => {
    expect(OPERATIONS).toContain('review.state')
    expect(OPERATIONS).toContain('verdict.answer')
  })

  it('call an operation with the arguments describe says it takes', async () => {
    const { client, sent } = serving()
    const args: Operations['verdict.answer'] = { sitting: 'art/review/title', choice: 'accept', why: 'ok' }
    await call(client, 'verdict.answer', args)
    expect(sent[0]!['params']).toEqual({ name: 'verdict_answer', arguments: args })
  })

  it('call an operation whose every argument may be left out with none', async () => {
    const { client, sent } = serving()
    await call(client, 'review.state')
    expect(sent[0]!['params']).toEqual({ name: 'review_state', arguments: {} })
  })
})
