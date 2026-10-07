import { builtinModules } from 'node:module'

import { defineConfig } from 'vite'

// The Electron main process, bundled with `core` inside it. Node's builtins and Electron
// stay external: they are there at runtime, and bundling them would make a second copy.
export default defineConfig({
  build: {
    outDir: 'dist',
    emptyOutDir: false,
    minify: false,
    target: 'node22',
    lib: { entry: { main: 'src/main.ts' }, formats: ['es'] },
    rollupOptions: {
      external: ['electron', ...builtinModules, ...builtinModules.map((m) => `node:${m}`)],
    },
  },
})
