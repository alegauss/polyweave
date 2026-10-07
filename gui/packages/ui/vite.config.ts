import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Relative, because the window loads this bundle over `file://`, where an absolute base
  // resolves to the drive root rather than to the app.
  base: './',
  build: { outDir: 'dist', emptyOutDir: true },
  test: {
    name: 'ui',
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
})
