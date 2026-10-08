// The review page, hosted rather than rebuilt (§PW305). The page already lays a sitting
// out, takes a verdict through `verdict.judge` and keeps `answers.jsonl`; a second
// implementation would have to find every defect it fixed again. So the window starts
// `python -m polyweave review` for the open project, with the engine it serves the
// project with, and shows the page it serves.

import { spawn, type ChildProcess } from 'node:child_process'

import type { Engine } from '@pw/core'

/** The line the review command prints once it is listening. */
const LISTENING = /polyweave review: (http:\/\/127\.0\.0\.1:\d+\/)/

interface Serving {
  child: ChildProcess
  url: Promise<string>
  exited: Promise<void>
}

/** The review server's arguments, from the engine that serves the project. */
export function reviewArgs(engine: Engine, project: string): string[] {
  const at = engine.args.indexOf('polyweave')
  const before = at >= 0 ? engine.args.slice(0, at + 1) : ['-m', 'polyweave']
  return [...before, 'review', '--root', project, '--port', '0']
}

export class Reviews {
  private readonly serving = new Map<string, Serving>()

  /** The page's address for a project, starting its server on the first call. */
  url(project: string, engine: Engine): Promise<string> {
    let held = this.serving.get(project)
    if (!held) {
      held = this.start(project, engine)
      this.serving.set(project, held)
      held.url.catch(() => this.serving.delete(project))
    }
    return held.url
  }

  /** End a project's review server, and wait for it to go. */
  async close(project: string): Promise<void> {
    const held = this.serving.get(project)
    this.serving.delete(project)
    if (held) {
      held.child.kill()
      await held.exited
    }
  }

  async closeAll(): Promise<void> {
    await Promise.all([...this.serving.keys()].map((project) => this.close(project)))
  }

  private start(project: string, engine: Engine): Serving {
    const child = spawn(engine.command, reviewArgs(engine, project), {
      cwd: project,
      windowsHide: true,
      env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' },
    })
    let said = ''
    const exited = new Promise<void>((resolve) => child.on('exit', () => resolve()))
    const url = new Promise<string>((resolve, reject) => {
      child.stdout?.setEncoding('utf8')
      child.stdout?.on('data', (chunk: string) => {
        said += chunk
        const found = LISTENING.exec(said)
        if (found) resolve(found[1]!)
      })
      child.stderr?.setEncoding('utf8')
      child.stderr?.on('data', (chunk: string) => (said += chunk))
      child.on('error', (failed) => reject(failed))
      child.on('exit', (code) =>
        reject(new Error(`the review page for ${project} exited with ${code}: ${said.trim()}`)),
      )
    })
    return { child, url, exited }
  }
}
