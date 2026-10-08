// Which `claude` runs a session (§PW306): the person's own, so the session signs in as
// them and loads their settings. Never one bundled with the window or the SDK.

import { existsSync } from 'node:fs'
import { homedir } from 'node:os'
import { delimiter, join } from 'node:path'

/** How a session is started: a command and what goes before the SDK's own flags. */
export interface Agent {
  command: string
  prefix: string[]
  /** Where it was found, which the screen names. */
  from: 'override' | 'path' | 'install'
}

/** An agent a developer names for an unpackaged window, as a JSON argv (the live test). */
export const AGENT_VAR = 'POLYWEAVE_AGENT'

/**
 * The person's `claude`: on PATH first, as their own shell would run it, then where Claude
 * Code installs itself, for a windowed app that did not inherit PATH. A JSON argv in
 * POLYWEAVE_AGENT goes before both, and only unpackaged: a shipped window never runs an
 * agent a variable chose. Null where there is none on this machine.
 */
export function agent(
  env: NodeJS.ProcessEnv = process.env,
  packaged = false,
  home: string = homedir(),
  exists: (path: string) => boolean = existsSync,
): Agent | null {
  const named = env[AGENT_VAR]
  if (!packaged && named) {
    try {
      const argv = JSON.parse(named) as unknown
      if (Array.isArray(argv) && argv.length && argv.every((a) => typeof a === 'string' && a)) {
        return { command: argv[0], prefix: argv.slice(1), from: 'override' }
      }
    } catch {
      // Not a JSON argv: ignored rather than guessed at.
    }
  }
  const windows = process.platform === 'win32'
  const names = windows ? ['claude.exe', 'claude.cmd', 'claude'] : ['claude']
  for (const folder of (env['PATH'] ?? env['Path'] ?? '').split(delimiter).filter(Boolean)) {
    for (const name of names) {
      const found = join(folder, name)
      if (exists(found)) return { command: found, prefix: [], from: 'path' }
    }
  }
  const installed = [
    join(home, '.local', 'bin', windows ? 'claude.exe' : 'claude'),
    join(home, '.claude', 'local', windows ? 'claude.exe' : 'claude'),
    ...(windows ? [join(env['APPDATA'] ?? join(home, 'AppData', 'Roaming'), 'npm', 'claude.cmd')] : []),
  ]
  const found = installed.find((one) => exists(one))
  return found ? { command: found, prefix: [], from: 'install' } : null
}
