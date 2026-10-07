// One server per open project, held while it is open (§PW303). Opening a project twice
// answers the server already held; closing it ends that server.

import { Broken, Client, engine, type Engine, type Server } from '@pw/core'

import { disk } from './disk'
import { served, type Served } from './process'

/** An open project: its client, who answered, and which engine was started. */
export interface Open {
  project: string
  client: Client
  server: Server
  engine: Engine
  /** Resolves once the server process has gone, which closing waits for. */
  exited: Promise<number | null>
}

export class Held {
  private readonly open = new Map<string, Promise<Open>>()

  /** The project's server, started and initialised on the first call. */
  async opened(project: string): Promise<Open> {
    let held = this.open.get(project)
    if (!held) {
      held = this.start(project)
      this.open.set(project, held)
      held.catch(() => this.open.delete(project))
    }
    return held
  }

  /**
   * End one project's server, where one is held, and wait for it to go: a process
   * still running in the project's folder holds that folder on Windows.
   */
  async close(project: string): Promise<void> {
    const held = this.open.get(project)
    this.open.delete(project)
    const open = held && (await held.catch(() => undefined))
    if (open) {
      open.client.close()
      await open.exited
    }
  }

  async closeAll(): Promise<void> {
    await Promise.all([...this.open.keys()].map((project) => this.close(project)))
  }

  private async start(project: string): Promise<Open> {
    const chosen = await engine(disk, project)
    const child: Served = served(chosen, project)
    const client = new Client(child)
    // A server that dies before it answers would leave `initialize` waiting forever,
    // so its exit fails the open with what it wrote to stderr.
    const died = child.exited.then((code) => {
      throw new Broken(
        `${chosen.command} ${chosen.args.join(' ')} exited with ${code} before it ` +
          `answered: ${child.stderr().trim().split('\n').slice(-3).join(' | ')}`,
      )
    })
    const server = await Promise.race([client.initialize(), died])
    died.catch(() => undefined) // its exit once closed is expected, not a failure
    return { project, client, server, engine: chosen, exited: child.exited }
  }
}
