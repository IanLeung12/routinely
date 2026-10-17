import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { PrivacyCard } from './PrivacyCard'

afterEach(cleanup)

const pausedCopy = 'Watching is paused. Nothing is recorded until you resume.'
const banned = /diagnos|patient|danger|warning|emergency/i

describe('PrivacyCard', () => {
  it('shows storage details and updates the controlled pause state', () => {
    const onTogglePause = vi.fn()
    const { rerender } = render(<PrivacyCard paused={false} onTogglePause={onTogglePause} supervisorNames={[]} />)

    expect(screen.getByRole('heading', { name: 'Your privacy' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: "What's stored" })).toBeTruthy()
    expect(screen.getByText('Body outlines (skeletons) and timings only. No video or photos ever leave this device or get saved.')).toBeTruthy()
    expect(screen.queryByText(pausedCopy)).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Pause watching', pressed: false }))
    expect(onTogglePause).toHaveBeenCalledTimes(1)

    rerender(<PrivacyCard paused onTogglePause={onTogglePause} supervisorNames={[]} />)
    expect(screen.getByText(pausedCopy)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Resume watching', pressed: true }))
    expect(onTogglePause).toHaveBeenCalledTimes(2)

    rerender(<PrivacyCard paused={false} onTogglePause={onTogglePause} supervisorNames={[]} />)
    expect(screen.getByRole('button', { name: 'Pause watching', pressed: false })).toBeTruthy()
    expect(screen.queryByText(pausedCopy)).toBeNull()
  })

  it.each([
    { names: [], copy: 'Only you can see this.' },
    { names: ['Lena'], copy: 'Lena sees exactly what you see here.' },
    { names: ['Lena', 'Sam'], copy: 'Lena and Sam see exactly what you see here.' },
    { names: ['Lena', 'Sam', 'Alex'], copy: 'Lena, Sam, and Alex see exactly what you see here.' },
    { names: ['Lena', 'Sam', 'Alex', 'Jo'], copy: 'Lena, Sam, Alex, and Jo see exactly what you see here.' },
  ])('describes sharing with $names.length supervisors', ({ names, copy }) => {
    const { container, rerender } = render(<PrivacyCard paused={false} onTogglePause={vi.fn()} supervisorNames={names} />)
    expect(screen.getByText(copy)).toBeTruthy()
    expect(container.textContent).not.toMatch(banned)
    rerender(<PrivacyCard paused onTogglePause={vi.fn()} supervisorNames={names} />)
    expect(container.textContent).not.toMatch(banned)
  })
})
