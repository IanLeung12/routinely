import { describe, expect, it, vi } from 'vitest'

/** jsdom never evaluates `@media`, so a phone-width test has to read the rule itself
 * (lesson from T-335). The path is relative to the web package's working directory;
 * `node:fs` comes through `importActual` because the browser build has no Node types. */
async function routineCss(): Promise<string> {
  const fs = await vi.importActual<{
    readFileSync: (path: string, encoding: 'utf8') => string
  }>('node:fs')
  return fs.readFileSync('src/person/routine/routine.css', 'utf8')
}

describe('my routine at phone width', () => {
  it('puts the two numbers side by side and makes the taps full width', async () => {
    const css = await routineCss()
    const phone = css.match(/@media\s*\(max-width:\s*480px\)\s*\{([\s\S]*?)\n\}/)?.[1]

    expect(phone).toBeDefined()
    expect(phone).toMatch(
      /\.routine-status__stats\s*\{[^}]*grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\)/,
    )
    expect(phone).toMatch(/\.privacy-card__pause\s*\{[^}]*width:\s*100%/)
    expect(phone).toMatch(/\.routine-note__tell/)
  })

  it('keeps every colour and size on a token', async () => {
    const css = await routineCss()

    expect(css).not.toMatch(/#[0-9a-f]{3,8}\b/i)
    expect(css).not.toMatch(/rgba?\(/)
  })
})
