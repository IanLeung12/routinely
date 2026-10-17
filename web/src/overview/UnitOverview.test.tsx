import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mockResidents } from '../mock/residents.ts'
import overviewCss from './overview.css?raw'
import { UnitOverview } from './UnitOverview.tsx'

function rowNames() {
  return screen
    .getAllByRole('listitem')
    .map((row) => row.querySelector('.resident-name')?.textContent)
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('UnitOverview', () => {
  it('falls back to the mock residents when the API is unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')))

    render(<UnitOverview />)

    for (const resident of mockResidents) {
      expect(await screen.findByText(resident.name)).toBeTruthy()
    }
  })

  it('renders every resident with their status chip, flagged residents first', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => mockResidents }),
    )

    render(<UnitOverview />)

    await waitFor(() => {
      expect(screen.getAllByRole('listitem')).toHaveLength(mockResidents.length)
    })

    const rows = screen.getAllByRole('listitem')
    const names = rows.map((row) => row.querySelector('.resident-name')?.textContent)
    expect(names).toEqual(['Mrs. K', 'Mr. Chen', 'Mr. Nguyen', 'Mrs. Patel', 'Mrs. Ahmed', 'Mr. Silva'])

    expect(rows[0].querySelector('.status-chip')?.textContent).toBe('Flagged')
    expect(rows[1].querySelector('.status-chip')?.textContent).toBe('Watch')
    for (const row of rows.slice(1, 4)) {
      expect(row.querySelector('.status-chip')?.textContent).toBe('Watch')
    }
    for (const row of rows.slice(4)) {
      expect(row.querySelector('.status-chip')?.textContent).toBe('Normal')
    }
  })

  it('summarizes mixed statuses in a status line', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => mockResidents }),
    )

    render(<UnitOverview />)

    const status = await screen.findByText('1 flagged for review · 3 on watch · 2 normal')
    expect(status.getAttribute('role')).toBe('status')
  })

  it('shows "All residents normal" when nothing is flagged or on watch', async () => {
    const allNormal = mockResidents.map((resident) => ({ ...resident, status: 'normal' as const }))
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => allNormal }))

    render(<UnitOverview />)

    const status = await screen.findByText('All residents normal')
    expect(status.getAttribute('role')).toBe('status')
  })

  it('shows the top pattern for flagged and watch residents, nothing for normal', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => mockResidents }),
    )

    render(<UnitOverview />)

    await waitFor(() => {
      expect(screen.getAllByRole('listitem')).toHaveLength(mockResidents.length)
    })

    const rows = screen.getAllByRole('listitem')
    const byName = new Map(rows.map((row) => [row.querySelector('.resident-name')?.textContent, row]))

    expect(byName.get('Mrs. K')?.querySelector('.resident-pattern')?.textContent).toBe(
      'Sudden change (delirium pattern)',
    )
    expect(byName.get('Mr. Chen')?.querySelector('.resident-pattern')?.textContent).toBe(
      'Slow drift (cognitive decline pattern)',
    )
    expect(byName.get('Mrs. Ahmed')?.querySelector('.resident-pattern')).toBeNull()
    expect(byName.get('Mr. Silva')?.querySelector('.resident-pattern')).toBeNull()
  })

  it('refetches residents when refreshKey changes', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => mockResidents })
    vi.stubGlobal('fetch', fetchMock)

    const { rerender } = render(<UnitOverview refreshKey={0} />)
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))

    rerender(<UnitOverview refreshKey={1} />)
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
  })

  it('shows an empty state when there are no residents', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => [] }))

    render(<UnitOverview />)

    expect(await screen.findByText('No residents on this unit yet.')).toBeTruthy()
    expect(screen.queryByRole('list')).toBeNull()
  })

  it('colours the status chip per status', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => mockResidents }),
    )

    render(<UnitOverview />)

    const flagged = await screen.findByText('Flagged', { selector: '.status-chip' })
    expect(flagged.className).toContain('status-chip--flagged')
    const [watch] = await screen.findAllByText('Watch', { selector: '.status-chip' })
    expect(watch.className).toContain('status-chip--watch')
    const [normal] = await screen.findAllByText('Normal', { selector: '.status-chip' })
    expect(normal.className).toContain('status-chip--normal')
  })

  it('defaults to the All filter showing every resident', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => mockResidents }),
    )

    render(<UnitOverview />)

    await waitFor(() => {
      expect(screen.getAllByRole('listitem')).toHaveLength(mockResidents.length)
    })
    expect(screen.getByRole('button', { name: 'All' }).getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByRole('button', { name: 'Flagged' }).getAttribute('aria-pressed')).toBe(
      'false',
    )
    expect(screen.getByRole('button', { name: 'Watch' }).getAttribute('aria-pressed')).toBe(
      'false',
    )
  })

  it('filters to only flagged residents', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => mockResidents }),
    )

    render(<UnitOverview />)
    await waitFor(() => {
      expect(screen.getAllByRole('listitem')).toHaveLength(mockResidents.length)
    })

    screen.getByRole('button', { name: 'Flagged' }).click()

    await waitFor(() => {
      expect(rowNames()).toEqual(['Mrs. K'])
    })
    expect(screen.getByRole('button', { name: 'Flagged' }).getAttribute('aria-pressed')).toBe(
      'true',
    )
  })

  it('filters to only watch residents', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => mockResidents }),
    )

    render(<UnitOverview />)
    await waitFor(() => {
      expect(screen.getAllByRole('listitem')).toHaveLength(mockResidents.length)
    })

    screen.getByRole('button', { name: 'Watch' }).click()

    await waitFor(() => {
      expect(rowNames()).toEqual(['Mr. Chen', 'Mr. Nguyen', 'Mrs. Patel'])
    })
  })

  it('shows "No residents flagged for review." when the flagged filter is empty', async () => {
    const noneFlagged = mockResidents.map((resident) =>
      resident.status === 'flagged' ? { ...resident, status: 'normal' as const } : resident,
    )
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => noneFlagged }))

    render(<UnitOverview />)
    await waitFor(() => {
      expect(screen.getAllByRole('listitem')).toHaveLength(noneFlagged.length)
    })

    screen.getByRole('button', { name: 'Flagged' }).click()

    expect(await screen.findByText('No residents flagged for review.')).toBeTruthy()
    expect(screen.queryByRole('list')).toBeNull()
  })

  it('shows "No residents to watch." when the watch filter is empty', async () => {
    const noneWatch = mockResidents.map((resident) =>
      resident.status === 'watch' ? { ...resident, status: 'normal' as const } : resident,
    )
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => noneWatch }))

    render(<UnitOverview />)
    await waitFor(() => {
      expect(screen.getAllByRole('listitem')).toHaveLength(noneWatch.length)
    })

    screen.getByRole('button', { name: 'Watch' }).click()

    expect(await screen.findByText('No residents to watch.')).toBeTruthy()
    expect(screen.queryByRole('list')).toBeNull()
  })

  it('returns to showing every resident when All is clicked again', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => mockResidents }),
    )

    render(<UnitOverview />)
    await waitFor(() => {
      expect(screen.getAllByRole('listitem')).toHaveLength(mockResidents.length)
    })

    screen.getByRole('button', { name: 'Flagged' }).click()
    await waitFor(() => {
      expect(rowNames()).toEqual(['Mrs. K'])
    })

    screen.getByRole('button', { name: 'All' }).click()
    await waitFor(() => {
      expect(screen.getAllByRole('listitem')).toHaveLength(mockResidents.length)
    })
  })
})

/** jsdom doesn't evaluate @media conditions for getComputedStyle, so this checks the
 * stylesheet text directly (verified against a real headless Chrome at 320/375/480/768px
 * for T234: the identity, status and sparkline each get their own full-width row and the
 * filter buttons keep a 44px tap target, with no horizontal scroll). */
describe('overview.css phone layout', () => {
  it('stacks each row full-width below 480px instead of scrolling sideways', () => {
    const mobileBlock = overviewCss.match(/@media \(max-width: 480px\) \{([\s\S]*)\}\s*$/)?.[1]
    expect(mobileBlock).toBeTruthy()

    expect(mobileBlock).toMatch(/\.resident-open\s*\{[^}]*flex-wrap:\s*wrap/)
    expect(mobileBlock).toMatch(/\.resident-identity\s*\{[^}]*width:\s*100%/)
    expect(mobileBlock).toMatch(/\.resident-status\s*\{[^}]*width:\s*100%/)
    expect(mobileBlock).toMatch(/\.resident-open svg\s*\{[^}]*flex-basis:\s*100%/)
  })

  it('keeps filter buttons at a 44px tap target and lets them wrap', () => {
    const mobileBlock = overviewCss.match(/@media \(max-width: 480px\) \{([\s\S]*)\}\s*$/)?.[1]

    expect(mobileBlock).toMatch(/\.unit-filter\s*\{[^}]*flex-wrap:\s*wrap/)
    expect(mobileBlock).toMatch(/\.unit-filter__button\s*\{[^}]*min-height:\s*2\.75rem/)
  })
})
