import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    // Two pages: the nurse's dashboard at `/` and the public landing page at
    // `/landing.html` (T378). Keeping the landing page in its own entry means a
    // change to it can't break the demo path, and vice versa.
    rollupOptions: {
      input: {
        main: fileURLToPath(new URL('index.html', import.meta.url)),
        landing: fileURLToPath(new URL('landing.html', import.meta.url)),
      },
    },
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{ts,tsx}'],
    setupFiles: ['src/testSetup.ts'],
    // Load every stylesheet under src/ into jsdom. Vitest stubs out CSS imports that
    // don't match this pattern even with `?raw`, so layout tests (getComputedStyle) and
    // media-query tests (jsdom doesn't evaluate @media, so they read the CSS text) need
    // it. One pattern instead of a folder list: no task should have to edit this line.
    // Unanchored on purpose - `?raw` imports arrive as `src/x.css?raw`.
    css: { include: [/src\/.*\.css/] },
  },
})
