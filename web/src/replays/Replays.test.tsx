import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { deleteReplay } from './api.ts'
import { Replays } from './Replays.tsx'

vi.mock('./api.ts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api.ts')>()
  return { ...actual, deleteReplay: vi.fn(actual.deleteReplay) }
})

function offline() {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')))
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.mocked(deleteReplay).mockClear()
})

async function rows() {
  return within(await screen.findByRole('list', { name: 'Replay sessions' })).getAllByRole('button')
}

describe('Replays', () => {
  it('lists a person\'s sessions newest first, with error pills, task and duration', async () => {
    offline()
    render(<Replays personId="mrs-k" role="supervisor" onBack={() => {}} />)

    const list = await rows()
    expect(list).toHaveLength(4)
    expect(list[0].textContent).toContain('skipped step')
    expect(list[0].textContent).toContain('make-tea')
    expect(list[1].textContent).toContain('out of order')
    expect(list[2].textContent).toContain('repeated step')
    expect(list[3].textContent).toContain('Most recent normal session (for comparison)')
  })

  it('shows the "no sessions with errors" empty state for a person with none', async () => {
    offline()
    render(<Replays personId="sam" role="person" onBack={() => {}} />)
    expect(await screen.findByText('No sessions with errors in the last 30 days')).toBeTruthy()
  })

  it('filters by date range, with its own empty state when nothing is left', async () => {
    offline()
    render(<Replays personId="mrs-k" role="supervisor" onBack={() => {}} />)
    await rows()

    fireEvent.change(screen.getByLabelText('From'), { target: { value: '2026-01-03' } })
    expect(await rows()).toHaveLength(3)

    fireEvent.change(screen.getByLabelText('From'), { target: { value: '2026-02-01' } })
    expect(await screen.findByText('No sessions with errors in this date range.')).toBeTruthy()
  })

  it('opens a session into the player and notes, with Back returning to the list', async () => {
    offline()
    const user = userEvent.setup()
    render(<Replays personId="mrs-k" role="supervisor" onBack={() => {}} />)

    const list = await rows()
    await user.click(list[0])
    expect(await screen.findByRole('button', { name: /play/i })).toBeTruthy()
    expect(screen.getByText('No notes yet.')).toBeTruthy()

    await user.click(screen.getByRole('button', { name: '← Sessions' }))
    expect(await rows()).toHaveLength(4)
  })

  it('shows the session\'s errors as jumpable markers on the player timeline', async () => {
    offline()
    const user = userEvent.setup()
    render(<Replays personId="mrs-k" role="supervisor" onBack={() => {}} />)

    await user.click((await rows())[0])
    expect(await screen.findByRole('button', { name: 'Jump to skipped pour-water at 0:10' })).toBeTruthy()
  })

  it('lets a supervisor add a note, shown with their name and the time', async () => {
    offline()
    const user = userEvent.setup()
    render(<Replays personId="mrs-k" role="supervisor" onBack={() => {}} />)

    await user.click((await rows())[0])
    await user.type(screen.getByLabelText('Add a note'), 'Took longer than usual')
    await user.click(screen.getByRole('button', { name: 'Add note' }))

    expect(screen.getByText('Took longer than usual')).toBeTruthy()
    expect(screen.getByText(/Nurse Ana · \d{2}:\d{2}/)).toBeTruthy()
  })

  it('hides the note form for the person, who sees "Delete this replay" instead', async () => {
    offline()
    const user = userEvent.setup()
    render(<Replays personId="mr-d" role="person" onBack={() => {}} />)

    await user.click((await rows())[0])
    expect(screen.queryByLabelText('Add a note')).toBeNull()
    expect(screen.getByRole('button', { name: 'Delete this replay' })).toBeTruthy()
  })

  it('deletes a replay after confirming, and removes it from the list', async () => {
    offline()
    const user = userEvent.setup()
    render(<Replays personId="mr-d" role="person" onBack={() => {}} />)

    await user.click((await rows())[0])
    await user.click(screen.getByRole('button', { name: 'Delete this replay' }))
    expect(screen.getByText("Delete this replay? This can't be undone.")).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Delete' }))

    expect(await screen.findByText('No sessions with errors in the last 30 days')).toBeTruthy()
  })

  it('cancels out of the delete confirmation without deleting', async () => {
    offline()
    const user = userEvent.setup()
    render(<Replays personId="mrs-k" role="person" onBack={() => {}} />)

    await user.click((await rows())[0])
    await user.click(screen.getByRole('button', { name: 'Delete this replay' }))
    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(screen.getByRole('button', { name: 'Delete this replay' })).toBeTruthy()
  })

  it('is keyboard operable: Enter opens a focused row, Enter reopens the list', async () => {
    offline()
    const user = userEvent.setup()
    render(<Replays personId="mrs-k" role="supervisor" onBack={() => {}} />)

    const list = await rows()
    list[0].focus()
    await user.keyboard('{Enter}')
    expect(await screen.findByRole('button', { name: /play/i })).toBeTruthy()

    screen.getByRole('button', { name: '← Sessions' }).focus()
    await user.keyboard('{Enter}')
    expect(await rows()).toHaveLength(4)
  })

  it('opens straight into a session when initialSessionId is given', async () => {
    offline()
    render(
      <Replays
        personId="mrs-k"
        role="supervisor"
        initialSessionId="mrs-k-sequence"
        onBack={() => {}}
      />,
    )
    expect(await screen.findByRole('button', { name: /play/i })).toBeTruthy()
  })

  it('shows an error and keeps the replay when delete fails, then allows retrying', async () => {
    offline()
    const user = userEvent.setup()
    vi.mocked(deleteReplay).mockRejectedValueOnce(new Error('refused'))
    render(<Replays personId="mrs-k" role="person" onBack={() => {}} />)

    await user.click((await rows())[0])
    await user.click(screen.getByRole('button', { name: 'Delete this replay' }))
    await user.click(screen.getByRole('button', { name: 'Delete' }))

    expect(await screen.findByText('This replay could not be deleted. It is still stored.')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Delete this replay' })).toBeTruthy()

    await user.click(screen.getByRole('button', { name: '← Sessions' }))
    expect(await rows()).toHaveLength(4)

    await user.click((await rows())[0])
    await user.click(screen.getByRole('button', { name: 'Delete this replay' }))
    await user.click(screen.getByRole('button', { name: 'Delete' }))

    expect(await rows()).toHaveLength(3)
  })
})
