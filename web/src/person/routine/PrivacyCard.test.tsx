import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { PrivacyCard } from './PrivacyCard.tsx'

afterEach(cleanup)

const banned = /diagnos|patient|resident|danger|warning|emergency|alarm/i

const PAUSED_LINE = 'Watching is paused. Nothing is recorded until you resume.'

describe('PrivacyCard', () => {
  it('offers the off switch and reports its own state', () => {
    render(<PrivacyCard paused={false} onTogglePause={() => {}} supervisorNames={[]} />)

    const pause = screen.getByRole('button', { name: 'Pause watching' })
    expect(pause.getAttribute('aria-pressed')).toBe('false')
    expect(screen.queryByText(PAUSED_LINE)).toBeNull()
  })

  it('says what is happening while it is paused', () => {
    render(<PrivacyCard paused onTogglePause={() => {}} supervisorNames={[]} />)

    const resume = screen.getByRole('button', { name: 'Resume watching' })
    expect(resume.getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByRole('status').textContent).toBe(PAUSED_LINE)
  })

  it('hands the pause back to whoever owns it', () => {
    const onTogglePause = vi.fn()
    render(<PrivacyCard paused={false} onTogglePause={onTogglePause} supervisorNames={[]} />)

    fireEvent.click(screen.getByRole('button', { name: 'Pause watching' }))

    expect(onTogglePause).toHaveBeenCalledTimes(1)
  })

  it('says only skeletons and timings are kept, never video', () => {
    render(<PrivacyCard paused={false} onTogglePause={() => {}} supervisorNames={['Lena']} />)

    expect(screen.getByText(/Body outlines \(skeletons\) and timings only/)).toBeTruthy()
    expect(screen.getByText(/No video or photos ever leave this device/)).toBeTruthy()
  })

  it.each([
    [[], 'Only you can see this.'],
    [['Lena'], 'Lena sees exactly what you see here.'],
    [['Lena', 'Ana'], 'Lena and Ana see exactly what you see here.'],
    [['Lena', 'Ana', 'Sam'], 'Lena, Ana and Sam see exactly what you see here.'],
  ])('names who sees it with %j supervisors', (names, expected) => {
    render(<PrivacyCard paused={false} onTogglePause={() => {}} supervisorNames={names} />)

    expect(screen.getByText(expected)).toBeTruthy()
  })

  it('never names a condition or raises an alarm', () => {
    const { container } = render(
      <PrivacyCard paused onTogglePause={() => {}} supervisorNames={['Lena']} />,
    )

    expect(container.textContent ?? '').not.toMatch(banned)
  })
})
