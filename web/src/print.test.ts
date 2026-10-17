import { describe, expect, it } from 'vitest'
import printCss from './print.css?raw'

/** The shared print rules (T289, T333, originally duplicated per screen; moved
 * here in T353) that every printable screen relies on. */
describe('print.css', () => {
  it('hides every no-print element when printing', () => {
    const printBlock = printCss.match(/@media print \{([\s\S]*)\}\s*$/)?.[1]
    expect(printBlock).toBeTruthy()

    expect(printBlock).toMatch(/\.no-print\s*\{[^}]*display:\s*none/)
  })

  it('forces black text on a white background regardless of the dark theme', () => {
    const printBlock = printCss.match(/@media print \{([\s\S]*)\}\s*$/)?.[1]

    expect(printBlock).toMatch(/body \*\s*\{[^}]*background:\s*#fff/)
    expect(printBlock).toMatch(/body \*\s*\{[^}]*color:\s*#000/)
  })
})
