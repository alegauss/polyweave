// How `npm start` opens the window (§PW438). VS Code exports ELECTRON_RUN_AS_NODE=1 to
// every process it starts, and Electron given it runs main.js as plain Node, where
// `electron` is a binary's path with no exports: the window failed with "does not provide
// an export named 'BrowserWindow'", which names nothing of the cause. So the variable is
// taken out of the window's environment here, as the live test always took it out of its
// own, and nobody starting the window has to know it exists.

import { spawn } from 'node:child_process'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
/** Under plain Node, the electron package answers the path of its binary. */
const binary = require('electron')

const env = { ...process.env }
delete env['ELECTRON_RUN_AS_NODE']

const given = process.argv.slice(2)
const child = spawn(binary, given.length ? given : ['.'], { env, stdio: 'inherit', windowsHide: false })
child.on('exit', (code, signal) => process.exit(code ?? (signal ? 1 : 0)))
