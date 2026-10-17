import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReplaySummary } from '../contracts'
import { ReplayList } from './ReplayList'

afterEach(cleanup)

const older: ReplaySummary = {
  session_id: 'older', person_id: 'person', task_id: 'tea',
  started_at: '2026-10-15T12:00:00Z', duration_s: 65,
  error_count: 1, error_types: ['omission'],
}
const newer: ReplaySummary = {
  ...older, session_id: 'newer', task_id: 'toast',
  started_at: '2026-10-16T12:00:00Z', error_types: ['sequence', 'perseveration'],
}
const normal: ReplaySummary = {
  ...older, session_id: 'normal', task_id: 'comparison',
  started_at: '2026-10-17T12:00:00Z', error_count: 0, error_types: [],
}
const rows = () => within(screen.getByRole('list', { name: 'Replay sessions' })).getAllByRole('button')

describe('ReplayList', () => {
  it('sorts newest first without changing input and shows times, labels and duration', () => {
    const replays = [older, newer]
    render(<ReplayList replays={replays} onOpen={vi.fn()} />)
    expect(rows().map((row) => row.textContent)).toEqual([
      expect.stringContaining('toast'), expect.stringContaining('tea'),
    ])
    expect(replays).toEqual([older, newer])
    expect(within(rows()[0]).getByText('repeated step')).toBeTruthy()
    expect(within(rows()[0]).getByText('1:05')).toBeTruthy()
    expect(rows()[0].querySelector('time')?.dateTime).toBe(newer.started_at)
  })

  it('filters by error type and restores all rows', async () => {
    const user = userEvent.setup()
    render(<ReplayList replays={[older, newer]} normal={normal} onOpen={vi.fn()} />)
    const filter = within(screen.getByRole('group', { name: 'Filter replays by error type' }))
    expect(filter.queryByRole('button', { name: 'wrong object' })).toBeNull()
    await user.click(filter.getByRole('button', { name: 'skipped step' }))
    expect(rows()).toHaveLength(2)
    expect(rows()[0].textContent).toContain('tea')
    expect(rows()[1].textContent).toContain('comparison')
    await user.click(filter.getByRole('button', { name: 'All' }))
    expect(rows()).toHaveLength(3)
  })

  it('shows the empty message, including when a comparison exists', () => {
    render(<ReplayList replays={[]} normal={normal} onOpen={vi.fn()} />)
    expect(screen.getByText('No sessions with errors in the last 30 days')).toBeTruthy()
    expect(rows()).toHaveLength(1)
  })

  it('keeps the normal session last with its comparison label and opens rows', async () => {
    const onOpen = vi.fn()
    const user = userEvent.setup()
    render(<ReplayList replays={[older, newer]} normal={normal} onOpen={onOpen} />)
    expect(within(rows()[2]).getByText('Most recent normal session (for comparison)')).toBeTruthy()
    await user.click(rows()[0])
    expect(onOpen).toHaveBeenCalledWith('newer')
    await user.click(rows()[2])
    expect(onOpen).toHaveBeenCalledWith('normal')
  })

  it('lets keyboard users tab to every row and activate it with Enter', async () => {
    const onOpen = vi.fn()
    const user = userEvent.setup()
    render(<ReplayList replays={[older]} normal={normal} onOpen={onOpen} />)
    await user.tab()
    await user.tab()
    await user.tab()
    expect(document.activeElement).toBe(rows()[0])
    await user.keyboard('{Enter}')
    expect(onOpen).toHaveBeenLastCalledWith('older')
    await user.tab()
    expect(document.activeElement).toBe(rows()[1])
    await user.keyboard('{Enter}')
    expect(onOpen).toHaveBeenLastCalledWith('normal')
  })
})
