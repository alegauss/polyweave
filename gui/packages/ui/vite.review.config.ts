// The review page's build (§PW403): the decision screen with its browser desk, into the
// folder `python -m polyweave review` serves. The bundle is committed, so a person with
// Python and no Node still has the page; `stamp.json` beside it names the sources it was
// built from and their digest, and tests/test_review_bundle.py fails when they moved on.

import { createHash } from 'node:crypto'
import { readFileSync, writeFileSync } from 'node:fs'
import { join, resolve } from 'node:path'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

const REPO = resolve(import.meta.dirname, '..', '..', '..')
const OUT = join(REPO, 'src', 'polyweave', 'review_page', 'screen')

/** Every file the bundle is built from, as the repository names it. */
export const SOURCES = [
  'gui/packages/core/src/desk.ts',
  'gui/packages/core/src/index.ts',
  'gui/packages/ui/review/index.html',
  'gui/packages/ui/src/Advanced.tsx',
  'gui/packages/ui/src/Decide.tsx',
  'gui/packages/ui/src/index.css',
  'gui/packages/ui/src/review.css',
  'gui/packages/ui/src/review.tsx',
]

/** The digest of the sources, line endings read as LF so a checkout on any OS agrees. */
export function digest(repo: string, sources: string[]): string {
  const hash = createHash('sha256')
  for (const path of [...sources].sort()) {
    hash.update(path + '\0')
    hash.update(readFileSync(join(repo, path), 'utf8').replace(/\r\n/g, '\n') + '\0')
  }
  return hash.digest('hex')
}

const stamped = (): Plugin => ({
  name: 'polyweave-stamp',
  closeBundle() {
    const stamp = { sources: SOURCES, sha256: digest(REPO, SOURCES), rebuild: 'cd gui && npm run build:review' }
    writeFileSync(join(OUT, 'stamp.json'), JSON.stringify(stamp, null, 2) + '\n')
  },
})

export default defineConfig({
  plugins: [react(), tailwindcss(), stamped()],
  root: resolve(import.meta.dirname, 'review'),
  // Relative, so the page's files resolve beside index.html wherever it is served from.
  base: './',
  build: {
    outDir: OUT,
    emptyOutDir: true,
    assetsDir: '.',
    rollupOptions: {
      output: {
        // Fixed names, so a rebuild of unchanged sources changes nothing in the tree.
        entryFileNames: 'review.js',
        chunkFileNames: '[name].js',
        assetFileNames: '[name][extname]',
      },
    },
  },
})
