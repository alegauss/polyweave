import { defineConfig } from 'vite'

// The preload, as CommonJS with `core`'s channel names already inside it: a sandboxed
// preload's `require` reaches Electron's own modules and nothing else.
export default defineConfig({
  build: {
    outDir: 'dist',
    emptyOutDir: false,
    minify: false,
    target: 'node22',
    lib: { entry: { preload: 'src/preload.ts' }, formats: ['cjs'], fileName: () => 'preload.cjs' },
    rollupOptions: { external: ['electron'] },
  },
})
