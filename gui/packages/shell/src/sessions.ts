// Claude Code sessions the window owns, carried by the Agent SDK (§PW306). The mechanics
// are roadkeep's (RG273): the person's own `claude` spawned with the SDK's flags after
// its command line, Claude Code's own system prompt and the user, project and local
// settings, so CLAUDE.md, the polyweave skill and its MCP server are the ones a terminal
// session has. Every message is offered as the line it was; a permission the session
// asks for becomes a `control_request` line the window answers.

import { spawn, type ChildProcess } from 'node:child_process'

import {
  query,
  type CanUseTool,
  type PermissionResult,
  type SDKUserMessage,
  type SpawnedProcess,
  type SpawnOptions,
} from '@anthropic-ai/claude-agent-sdk'

import type { Agent } from './agent'

/** What the agent reads for a question nobody answered before the session moved on. */
const UNANSWERED = 'The question was withdrawn before the person watching answered it.'

/** Messages the person sends, queued for the SDK's streaming input. */
class Inbox implements AsyncIterable<SDKUserMessage> {
  private readonly queued: SDKUserMessage[] = []
  private waiting: ((next: IteratorResult<SDKUserMessage>) => void) | null = null
  private closed = false

  put(text: string): void {
    const message: SDKUserMessage = {
      type: 'user',
      message: { role: 'user', content: text },
      parent_tool_use_id: null,
    }
    if (this.waiting) {
      const give = this.waiting
      this.waiting = null
      give({ value: message, done: false })
    } else {
      this.queued.push(message)
    }
  }

  close(): void {
    this.closed = true
    this.waiting?.({ value: undefined, done: true })
    this.waiting = null
  }

  [Symbol.asyncIterator](): AsyncIterator<SDKUserMessage> {
    return {
      next: () => {
        const next = this.queued.shift()
        if (next) return Promise.resolve({ value: next, done: false })
        if (this.closed) return Promise.resolve({ value: undefined, done: true })
        return new Promise((resolve) => (this.waiting = resolve))
      },
    }
  }
}

/** One running session: say more to it, answer what it asks, or stop it. */
export interface Session {
  say(text: string): void
  /** Answer a permission it is waiting on; false where nothing by that id waits. */
  answer(requestId: string, allow: boolean, why?: string): boolean
  stop(): void
  /** Resolves once the process is gone, with what it said on stderr. */
  readonly finished: Promise<{ code: number | null; said: string }>
}

/** What a session runs under besides its prompt: the revision's hooks and refusals. */
export interface Harness {
  settings?: Record<string, unknown>
  disallowed?: string[]
}

export function start(
  agent: Agent,
  cwd: string,
  first: string,
  onLine: (line: string) => void,
  env: NodeJS.ProcessEnv = process.env,
  harness: Harness = {},
): Session {
  const inbox = new Inbox()
  inbox.put(first)
  const abort = new AbortController()
  const waiting = new Map<string, (answer: PermissionResult) => void>()
  let child: ChildProcess | null = null
  let stderr = ''
  let code: number | null = null
  let exited: Promise<void> = Promise.resolve()

  // The person's command line, then the SDK's flags (it names the executable first).
  const spawnAgent = (options: SpawnOptions): SpawnedProcess => {
    const at = options.args.indexOf(agent.command)
    const flags = options.command === agent.command ? options.args : options.args.slice(at + 1)
    const spawned = spawn(agent.command, [...agent.prefix, ...flags], {
      cwd: options.cwd,
      env: options.env,
      windowsHide: true,
      stdio: ['pipe', 'pipe', 'pipe'],
    })
    child = spawned
    exited = new Promise((resolve) => {
      spawned.once('close', (exit: number | null) => {
        code = exit
        resolve()
      })
      spawned.once('error', (cause: Error) => {
        stderr += cause.message
        abort.abort()
        resolve()
      })
    })
    spawned.stdin!.on('error', () => undefined)
    spawned.stderr!.setEncoding('utf8')
    spawned.stderr!.on('data', (chunk: string) => (stderr += chunk))
    options.signal.addEventListener('abort', () => spawned.kill(), { once: true })
    return Object.assign(spawned, { stdin: spawned.stdin!, stdout: spawned.stdout! })
  }

  const canUseTool: CanUseTool = (tool, input, asked) =>
    new Promise((resolve) => {
      const id = asked.toolUseID ?? `ask-${waiting.size + 1}`
      waiting.set(id, resolve)
      asked.signal.addEventListener(
        'abort',
        () => {
          if (!waiting.delete(id)) return
          onLine(JSON.stringify({ type: 'control_cancel_request', request_id: id }))
          resolve({ behavior: 'deny', message: UNANSWERED })
        },
        { once: true },
      )
      setImmediate(() => {
        if (!waiting.has(id)) return
        onLine(
          JSON.stringify({
            type: 'control_request',
            request_id: id,
            request: {
              subtype: 'can_use_tool',
              tool_name: tool,
              input,
              description: asked.description,
              // Why it is asked, where a hook said so: a write outside the item (§PW309).
              ...(asked.decisionReason ? { reason: asked.decisionReason } : {}),
            },
          }),
        )
      })
    })

  const finished = (async () => {
    try {
      for await (const message of query({
        prompt: inbox,
        options: {
          abortController: abort,
          cwd,
          env: { ...env },
          pathToClaudeCodeExecutable: agent.command,
          spawnClaudeCodeProcess: spawnAgent,
          canUseTool,
          settingSources: ['user', 'project', 'local'],
          systemPrompt: { type: 'preset', preset: 'claude_code' },
          // The revision's harness (§PW307): checks after every write, no verdict tool.
          ...(harness.settings ? { settings: harness.settings as never } : {}),
          ...(harness.disallowed?.length ? { disallowedTools: harness.disallowed } : {}),
        },
      })) {
        onLine(JSON.stringify(message))
      }
    } catch (cause) {
      if (!stderr) stderr = cause instanceof Error ? cause.message : String(cause)
    }
    for (const give of waiting.values()) give({ behavior: 'deny', message: UNANSWERED })
    waiting.clear()
    inbox.close()
    await exited
    return { code, said: stderr.trim() }
  })()

  return {
    say: (text) => inbox.put(text),
    answer(requestId, allow, why) {
      const give = waiting.get(requestId)
      if (!give) return false
      waiting.delete(requestId)
      give(allow ? { behavior: 'allow' } : { behavior: 'deny', message: why || 'The person said no.' })
      return true
    },
    stop() {
      inbox.close()
      abort.abort()
      ;(child as ChildProcess | null)?.kill()
    },
    finished,
  }
}
