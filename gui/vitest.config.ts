import { defineConfig } from 'vitest/config'

// One project per package, each with its own environment. `core` runs in Node and may
// touch nothing of it: what it reads arrives through the interfaces it is handed. `shell`
// starts processes, and its `*-live.test.ts` start a real polyweave serve.
export default defineConfig({
  test: {
    projects: ['packages/core', 'packages/shell', 'packages/ui/vite.config.ts'],
  },
})
