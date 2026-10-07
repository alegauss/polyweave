// A held `polyweave serve`, as the transport `core`'s client speaks over (§PW303).

import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process'

import type { Engine, Transport } from '@pw/core'

/** How much of the server's stderr is kept, for saying why it went away. */
const KEPT = 64 * 1024

/** A server process, its stdout split into lines and its stderr kept for a failure. */
export interface Served extends Transport {
  /** The tail of what the server wrote to stderr: the traceback, when it dies. */
  stderr(): string
  /** Resolves with the exit code once the process has gone. */
  readonly exited: Promise<number | null>
}

/** Start one server for a project, in the project's folder. */
export function served(engine: Engine, project: string): Served {
  const child: ChildProcessWithoutNullStreams = spawn(engine.command, engine.args, {
    cwd: project,
    stdio: ['pipe', 'pipe', 'pipe'],
    windowsHide: true,
    // Python's own output encoding, so a path with an accent survives the pipe.
    env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' },
  })
  const listeners: ((line: string) => void)[] = []
  let partial = ''
  let errors = ''
  child.stdout.setEncoding('utf8')
  child.stdout.on('data', (chunk: string) => {
    partial += chunk
    let end = partial.indexOf('\n')
    while (end >= 0) {
      const line = partial.slice(0, end).replace(/\r$/, '')
      partial = partial.slice(end + 1)
      for (const listener of listeners) {
        listener(line)
      }
      end = partial.indexOf('\n')
    }
  })
  child.stderr.setEncoding('utf8')
  child.stderr.on('data', (chunk: string) => {
    errors = (errors + chunk).slice(-KEPT)
  })
  const exited = new Promise<number | null>((resolve) => {
    child.on('exit', (code) => resolve(code))
    child.on('error', (failed) => {
      errors += `\n${failed.message}`
      resolve(null)
    })
  })
  return {
    send(line) {
      if (child.stdin.writable) {
        child.stdin.write(`${line}\n`)
      }
    },
    onLine(listener) {
      listeners.push(listener)
    },
    close() {
      child.stdin.end()
      child.kill()
    },
    stderr: () => errors,
    exited,
  }
}
