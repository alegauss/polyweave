// Which polyweave serves a project (§PW303). A project may pin its own copy, in its own
// environment, and that is the one its agent's sessions run, so the window asks it
// first and the PATH's last. The choice is shown on screen, never made silently.

/** How to start one server, and where that choice came from. */
export interface Engine {
  command: string
  args: string[]
  /** `project` for the project's own environment, `path` for whatever PATH finds. */
  from: 'project' | 'path'
}

/** What the shell answers about a path; `core` cannot look for itself. */
export interface Probe {
  exists(path: string): Promise<boolean>
  join(...parts: string[]): string
}

/** The interpreters a project's own environment may hold, in the order they are tried. */
const OWN = [
  ['.venv', 'Scripts', 'python.exe'],
  ['.venv', 'bin', 'python'],
  ['venv', 'Scripts', 'python.exe'],
  ['venv', 'bin', 'python'],
]

/** The server for a project: its own environment's python first, PATH's last. */
export async function engine(probe: Probe, project: string): Promise<Engine> {
  for (const parts of OWN) {
    const python = probe.join(project, ...parts)
    if (await probe.exists(python)) {
      return { command: python, args: ['-m', 'polyweave', 'serve'], from: 'project' }
    }
  }
  return { command: 'python', args: ['-m', 'polyweave', 'serve'], from: 'path' }
}
