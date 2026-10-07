import { defineProject } from 'vitest/config'

// Everything that starts a process is named `*-live.test.ts`. They run here too, one
// file at a time and with room to start a Python, because the gate runs every test.
export default defineProject({
  test: {
    name: 'shell',
    environment: 'node',
    include: ['src/**/*.test.ts'],
    testTimeout: 60_000,
    fileParallelism: false,
  },
})
