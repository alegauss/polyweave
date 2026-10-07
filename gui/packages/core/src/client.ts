// The window's one way to a project: a held `python -m polyweave serve`, spoken to over
// newline-delimited JSON-RPC (§PW303). Every fact on screen is an operation's payload,
// so the window never parses a TOML, a sidecar or a JSONL itself, and a kind added in
// Python appears here without a change on this side.

/** One line out, one line in: what the shell's child process is to this package. */
export interface Transport {
  send(line: string): void
  /** Called with every line the server writes, in order. */
  onLine(listener: (line: string) => void): void
  close(): void
}

/** A refusal exactly as polyweave writes one: code, message, remedy and the rest. */
export interface Refusal {
  code: string
  message: string
  remedy: string
  [field: string]: unknown
}

/** An operation answered with a refusal; the screen shows it, it is not a crash. */
export class Refused extends Error {
  readonly refusal: Refusal
  constructor(refusal: Refusal) {
    super(`${refusal.code}: ${refusal.message}`)
    this.name = 'Refused'
    this.refusal = refusal
  }
}

/** The connection itself failed: the server said no to the protocol, or went away. */
export class Broken extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'Broken'
  }
}

/** Who answered: the name and version `initialize` reported. */
export interface Server {
  name: string
  version: string
}

const PROTOCOL = '2025-06-18'

interface Pending {
  resolve(value: unknown): void
  reject(reason: Error): void
}

/** An MCP client over a transport, holding every call in flight by its id. */
export class Client {
  private readonly transport: Transport
  private readonly pending = new Map<number, Pending>()
  private next = 1
  private closed = false

  constructor(transport: Transport) {
    this.transport = transport
    transport.onLine((line) => this.received(line))
  }

  /** Open the session; the answer names the copy of polyweave that is serving. */
  async initialize(): Promise<Server> {
    const result = (await this.request('initialize', {
      protocolVersion: PROTOCOL,
      capabilities: {},
      clientInfo: { name: 'polyweave-gui', version: '0.0.0' },
    })) as { serverInfo?: Partial<Server> }
    this.transport.send(JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }))
    const info = result.serverInfo ?? {}
    return { name: String(info.name ?? ''), version: String(info.version ?? '') }
  }

  /**
   * Call one operation by its dotted name, as `describe` spells it, and answer its
   * payload. A refusal rejects with `Refused`, carrying polyweave's own fields.
   */
  async call(operation: string, args: Record<string, unknown> = {}): Promise<unknown> {
    const result = (await this.request('tools/call', {
      name: operation.replaceAll('.', '_'),
      arguments: args,
    })) as { structuredContent?: Record<string, unknown>; isError?: boolean }
    const payload = result.structuredContent ?? {}
    if (result.isError) {
      throw new Refused(payload['refused'] as Refusal)
    }
    // A list comes back wrapped, since structured content has to be an object.
    const keys = Object.keys(payload)
    return keys.length === 1 && keys[0] === 'result' ? payload['result'] : payload
  }

  close(): void {
    this.closed = true
    this.transport.close()
    for (const waiting of this.pending.values()) {
      waiting.reject(new Broken('the connection was closed with a call in flight'))
    }
    this.pending.clear()
  }

  private request(method: string, params: Record<string, unknown>): Promise<unknown> {
    if (this.closed) {
      return Promise.reject(new Broken('the connection is closed'))
    }
    const id = this.next++
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject })
      this.transport.send(JSON.stringify({ jsonrpc: '2.0', id, method, params }))
    })
  }

  private received(line: string): void {
    if (!line.trim()) {
      return
    }
    let message: { id?: unknown; result?: unknown; error?: { message?: string } }
    try {
      message = JSON.parse(line)
    } catch {
      // A line that is not JSON is the server printing where the protocol is; it
      // answers no call, and the call it interrupted still gets its own reply.
      return
    }
    if (typeof message.id !== 'number') {
      return
    }
    const waiting = this.pending.get(message.id)
    if (!waiting) {
      return
    }
    this.pending.delete(message.id)
    if (message.error) {
      waiting.reject(new Broken(String(message.error.message ?? 'the server refused the call')))
    } else {
      waiting.resolve(message.result)
    }
  }
}
