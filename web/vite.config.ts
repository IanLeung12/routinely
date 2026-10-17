import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{ts,tsx}'],
    // Load the live-session and overview stylesheets into jsdom: the task map's wrapping
    // layout is testable with getComputedStyle (T120), and the overview's phone media
    // query is readable via `?raw` (T234 — jsdom doesn't evaluate @media itself). Other
    // CSS stays stubbed out, which is both faster and enough: those screens are tested
    // through the DOM.
    css: { include: [/src\/live\//, /src\/overview\//] },
  },
})
