import { defineProject } from 'vitest/config'

// Everything that starts a process is named `*-live.test.ts`. They run here too, one
// file at a time and with room to start a Python, because the gate runs every test.
// A hook gets the same room as a test: the window's setup starts two Pythons, and
// under the gate's load that outran vitest's 10 s default (PW389).
export default defineProject({
  test: {
    name: 'shell',
    environment: 'node',
    include: ['src/**/*.test.ts'],
    testTimeout: 60_000,
    hookTimeout: 60_000,
    fileParallelism: false,
  },
})
