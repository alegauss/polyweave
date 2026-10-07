import { describe, expect, it } from 'vitest'

import { Broken, Client, Refused, type Transport } from './client'

/** A server in memory, answering each request with what `reply` makes of it. */
function serving(reply: (message: Record<string, unknown>) => unknown) {
  const sent: Record<string, unknown>[] = []
  let listener: (line: string) => void = () => {}
  const transport: Transport = {
    send(line) {
      const message = JSON.parse(line)
      sent.push(message)
      if ('id' in message) {
        const answer = reply(message)
        if (answer !== undefined) {
          // Answered later, as a process would, not inside the send.
          queueMicrotask(() => listener(JSON.stringify(answer)))
        }
      }
    },
    onLine(on) {
      listener = on
    },
    close() {},
  }
  return { transport, sent, push: (line: string) => listener(line) }
}

const result = (id: unknown, value: unknown) => ({ jsonrpc: '2.0', id, result: value })

describe('the client', () => {
  it('opens the session and names who answered', async () => {
    const { transport, sent } = serving((m) =>
      result(m['id'], { serverInfo: { name: 'polyweave', version: '0.9.1' } }),
    )
    const server = await new Client(transport).initialize()
    expect(server).toEqual({ name: 'polyweave', version: '0.9.1' })
    expect(sent.map((m) => m['method'])).toEqual(['initialize', 'notifications/initialized'])
  })

  it('calls an operation by its dotted name and answers its payload', async () => {
    const { transport, sent } = serving((m) =>
      result(m['id'], { structuredContent: { total: 3 }, isError: false }),
    )
    const answer = await new Client(transport).call('project.inventory', { root: '/g' })
    expect(answer).toEqual({ total: 3 })
    expect(sent[0]!['params']).toEqual({ name: 'project_inventory', arguments: { root: '/g' } })
  })

  it('unwraps a list the server had to wrap', async () => {
    const { transport } = serving((m) =>
      result(m['id'], { structuredContent: { result: ['a', 'b'] }, isError: false }),
    )
    expect(await new Client(transport).call('loop.assets')).toEqual(['a', 'b'])
  })

  it("rejects a refusal with polyweave's own fields", async () => {
    const refusal = { code: 'op.unknown', message: 'no such tool', remedy: 'list them' }
    const { transport } = serving((m) =>
      result(m['id'], { structuredContent: { refused: refusal }, isError: true }),
    )
    const failed = new Client(transport).call('nothing.here')
    await expect(failed).rejects.toBeInstanceOf(Refused)
    await expect(failed).rejects.toMatchObject({ refusal })
  })

  it('keeps calls in flight apart by id, whatever order they are answered in', async () => {
    const held: Record<string, unknown>[] = []
    const { transport, push } = serving((m) => {
      held.push(m)
      return undefined
    })
    const client = new Client(transport)
    const first = client.call('a.one')
    const second = client.call('b.two')
    const [one, two] = held
    push(JSON.stringify(result(two!['id'], { structuredContent: { said: 2 } })))
    push('a line the server printed where the protocol is')
    push(JSON.stringify(result(one!['id'], { structuredContent: { said: 1 } })))
    expect(await first).toEqual({ said: 1 })
    expect(await second).toEqual({ said: 2 })
  })

  it('fails what is in flight when the connection closes', async () => {
    const { transport } = serving(() => undefined)
    const client = new Client(transport)
    const waiting = client.call('a.one')
    client.close()
    await expect(waiting).rejects.toBeInstanceOf(Broken)
    await expect(client.call('a.two')).rejects.toBeInstanceOf(Broken)
  })

  it('reports a protocol error as a broken call, not a refusal', async () => {
    const { transport } = serving((m) => ({
      jsonrpc: '2.0',
      id: m['id'],
      error: { code: -32601, message: "no method 'x'" },
    }))
    await expect(new Client(transport).call('a.one')).rejects.toBeInstanceOf(Broken)
  })
})
