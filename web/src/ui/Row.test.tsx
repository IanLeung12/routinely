import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Pill } from './Pill.tsx'
import { Row } from './Row.tsx'

afterEach(() => {
  cleanup()
})

describe('Row', () => {
  it('shows who it is about, where they are, and the number', () => {
    render(<Row title="Mrs. K" subtitle="Room 204" value="3" />)
    expect(screen.getByText('Mrs. K').className).toContain('row__title')
    expect(screen.getByText('Room 204').className).toContain('row__subtitle')
    expect(screen.getByText('3').className).toContain('row__value')
  })

  it('leaves out the parts it was not given', () => {
    const { container } = render(<Row title="Mr. Silva" />)
    expect(container.querySelector('.row__subtitle')).toBeNull()
    expect(container.querySelector('.row__value')).toBeNull()
    expect(container.querySelector('.row__trailing')).toBeNull()
  })

  it('still shows a zero value', () => {
    render(<Row title="Mrs. Ahmed" value={0} />)
    expect(screen.getByText('0')).toBeTruthy()
  })

  it('puts a chip or pill after the value', () => {
    render(<Row title="Mrs. K" value="3" trailing={<Pill tone="watch">Watch</Pill>} />)
    expect(screen.getByText('Watch').className).toContain('pill--watch')
  })

  it('is a plain row, not a control, until it is given something to do', () => {
    render(<Row title="Mrs. K" />)
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('becomes a keyboard-reachable button when it can be opened', async () => {
    const onSelect = vi.fn()
    const user = userEvent.setup()
    render(<Row title="Mrs. K" subtitle="Room 204" onSelect={onSelect} selectLabel="Open Mrs. K" />)
    const row = screen.getByRole('button', { name: 'Open Mrs. K' })
    expect(row.className).toContain('row--interactive')
    await user.tab()
    expect(document.activeElement).toBe(row)
    await user.keyboard('{Enter}')
    expect(onSelect).toHaveBeenCalledTimes(1)
  })

  /** Rows draw the hairline themselves, so a screen only has to render them as
   * siblings. jsdom won't apply the rule, so this reads the stylesheet. */
  it('separates itself from the row above with a hairline', async () => {
    const fs = await vi.importActual<{
      readFileSync: (path: string, encoding: 'utf8') => string
    }>('node:fs')
    const css = fs.readFileSync('src/index.css', 'utf8')
    expect(css).toMatch(
      /\.row \+ \.row,\s*li \+ li > \.row \{[^}]*border-top:\s*1px solid var\(--hairline\)/,
    )
  })
})
