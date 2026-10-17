import { describe, expect, it, vi } from 'vitest'

/** Reads the design tokens straight out of `src/index.css` so the contrast rule
 * in docs/DESIGN.md is checked against what ships, not against a copy of it.
 * The path is relative to the web package's working directory on purpose: in
 * jsdom, `new URL(..., import.meta.url)` can resolve to an http: URL. */
async function readIndexCss(): Promise<string> {
  const fs = await vi.importActual<{
    readFileSync: (path: string, encoding: 'utf8') => string
  }>('node:fs')
  return fs.readFileSync('src/index.css', 'utf8')
}

/** The custom properties declared in `:root`, with `var(--other)` resolved so
 * legacy aliases (`--panel`, `--alarm`) land on the same colours as the new names. */
function rootTokens(css: string): Record<string, string> {
  const block = /:root\s*\{([\s\S]*?)\n\}/.exec(css)
  if (!block) throw new Error('index.css has no :root block')
  const declarations = block[1].replace(/\/\*[\s\S]*?\*\//g, '')
  const tokens: Record<string, string> = {}
  for (const line of declarations.split(';')) {
    const decl = /(--[\w-]+)\s*:\s*([\s\S]+)/.exec(line)
    if (decl) tokens[decl[1]] = decl[2].trim()
  }
  for (let pass = 0; pass < 5; pass++) {
    for (const [name, value] of Object.entries(tokens)) {
      tokens[name] = value.replace(/var\((--[\w-]+)\)/g, (whole, ref) => tokens[ref] ?? whole)
    }
  }
  return tokens
}

type Colour = { r: number; g: number; b: number; a: number }

function parseColour(value: string): Colour {
  const hex = /^#([0-9a-f]{6})$/i.exec(value)
  if (hex) {
    const n = parseInt(hex[1], 16)
    return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255, a: 1 }
  }
  const rgba = /^rgba?\(([^)]+)\)$/i.exec(value)
  if (rgba) {
    const parts = rgba[1].split(',').map((p) => Number(p.trim()))
    return { r: parts[0], g: parts[1], b: parts[2], a: parts[3] ?? 1 }
  }
  throw new Error(`not a colour this test can read: ${value}`)
}

/** Paints `top` (which may be translucent) onto the opaque `bottom`. */
function composite(top: Colour, bottom: Colour): Colour {
  return {
    r: top.a * top.r + (1 - top.a) * bottom.r,
    g: top.a * top.g + (1 - top.a) * bottom.g,
    b: top.a * top.b + (1 - top.a) * bottom.b,
    a: 1,
  }
}

function relativeLuminance({ r, g, b }: Colour): number {
  const channel = (value: number) => {
    const c = value / 255
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  }
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
}

function contrast(foreground: Colour, background: Colour): number {
  const [light, dark] = [relativeLuminance(foreground), relativeLuminance(background)].sort(
    (a, b) => b - a,
  )
  return (light + 0.05) / (dark + 0.05)
}

/** Every opaque surface a word can land on. */
const SURFACES = ['--surface-page', '--surface-card', '--surface-raised', '--surface-raised-hover']

/** Text tokens, and the colours used as text (a flagged note, an axis label, a
 * chart's own legend), all of which can sit on any surface. */
const TEXT_ON_SURFACES = [
  '--text',
  '--text-secondary',
  '--text-muted',
  '--accent',
  '--status-normal',
  '--status-watch',
  '--status-flagged',
  '--status-neutral',
  '--chart-line',
  '--chart-comparison',
  '--chart-forecast',
]

/** Tinted pills: the text sits on a translucent tint of its own colour, which
 * in turn sits on a surface. The tint is what the text is actually read against. */
const TINTED_PILLS: [string, string][] = [
  ['--status-normal', '--status-normal-tint'],
  ['--status-watch', '--status-watch-tint'],
  ['--status-flagged', '--status-flagged-tint'],
  ['--status-neutral', '--status-neutral-tint'],
  ['--accent', '--accent-tint'],
]

const MINIMUM = 4.5

describe('design tokens', () => {
  it('keeps every text token at 4.5:1 or better on every surface it lands on', async () => {
    const tokens = rootTokens(await readIndexCss())
    for (const surfaceName of SURFACES) {
      const surface = parseColour(tokens[surfaceName])
      for (const textName of TEXT_ON_SURFACES) {
        const ratio = contrast(parseColour(tokens[textName]), surface)
        expect(ratio, `${textName} on ${surfaceName}`).toBeGreaterThanOrEqual(MINIMUM)
      }
    }
  })

  it('keeps a tinted pill readable on every surface', async () => {
    const tokens = rootTokens(await readIndexCss())
    for (const surfaceName of SURFACES) {
      const surface = parseColour(tokens[surfaceName])
      for (const [textName, tintName] of TINTED_PILLS) {
        const pill = composite(parseColour(tokens[tintName]), surface)
        const ratio = contrast(parseColour(tokens[textName]), pill)
        expect(ratio, `${textName} on ${tintName} over ${surfaceName}`).toBeGreaterThanOrEqual(
          MINIMUM,
        )
      }
    }
  })

  it('keeps the primary button readable (page colour on the text colour)', async () => {
    const tokens = rootTokens(await readIndexCss())
    const ratio = contrast(parseColour(tokens['--surface-page']), parseColour(tokens['--text']))
    expect(ratio).toBeGreaterThanOrEqual(MINIMUM)
  })

  it('points the legacy token names at the new ones so screens keep working', async () => {
    const tokens = rootTokens(await readIndexCss())
    expect(tokens['--bg']).toBe(tokens['--surface-page'])
    expect(tokens['--panel']).toBe(tokens['--surface-card'])
    expect(tokens['--border']).toBe(tokens['--hairline'])
    expect(tokens['--muted']).toBe(tokens['--text-secondary'])
    expect(tokens['--alarm']).toBe(tokens['--status-flagged'])
    expect(tokens['--amber']).toBe(tokens['--status-watch'])
    expect(tokens['--status-flagged-bg']).toBe(tokens['--status-flagged-tint'])
    expect(tokens['--error-red-text']).toBe(tokens['--status-flagged'])
  })

  it('ships the surfaces, chart palette and tabular-numerals utility', async () => {
    const css = await readIndexCss()
    const tokens = rootTokens(css)
    for (const name of [
      '--surface-page',
      '--surface-card',
      '--surface-raised',
      '--hairline',
      '--page-glow',
      '--chart-line',
      '--chart-comparison',
      '--chart-baseline',
      '--chart-forecast',
      '--radius-xs',
      '--radius-md',
      '--space-4',
      '--text-md',
    ]) {
      expect(tokens[name], `${name} is missing from :root`).toBeTruthy()
    }
    expect(css).toMatch(/\.tabular-nums\s*\{\s*font-variant-numeric:\s*tabular-nums/)
    // Cards: one step lighter than the page, a hairline border, radius ~12px.
    expect(css).toMatch(
      /\.panel,\s*\.card\s*\{[^}]*border:\s*1px solid var\(--hairline\)[^}]*border-radius:\s*var\(--radius-md\)[^}]*background:\s*var\(--surface-card\)/,
    )
  })
})
