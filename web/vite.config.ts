import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{ts,tsx}'],
    setupFiles: ['src/testSetup.ts'],
    // Load the live-session, overview, alert, resident, evidence, handoff and shared print
    // stylesheets into jsdom: the task map's wrapping layout is testable with getComputedStyle
    // (T120), and the overview's, alert's, resident detail's, evidence's, shift handoff's and
    // shared print.css's media queries are readable via `?raw` (T234, T238, T239, T353, T358,
    // T203 — jsdom doesn't evaluate @media itself, and Vitest stubs out CSS imports that don't
    // match here even with `?raw`). Other CSS stays stubbed out, which is both faster and
    // enough: those screens are tested through the DOM.
    css: { include: [/src\/live\//, /src\/overview\//, /src\/alert\//, /src\/resident\//, /src\/evidence\//, /src\/handoff\/handoff\.css/, /src\/print\.css/] },
  },
})
