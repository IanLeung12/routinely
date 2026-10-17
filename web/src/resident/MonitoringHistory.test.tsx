import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import type { MonitoringChange } from '../about/monitoringApi.ts'
import { MonitoringHistory } from './MonitoringHistory.tsx'
import monitoringHistoryCss from './monitoringHistory.css?raw'

function change(on: boolean, by: string, at: string): MonitoringChange {
  return { on, by, at }
}

describe('MonitoringHistory', () => {
  afterEach(cleanup)

  it('lists who paused or resumed the room and when, newest first', () => {
    render(
      <MonitoringHistory
        changes={[
          change(true, 'nurse-bo', '2026-10-17T09:25:00+00:00'),
          change(false, 'nurse-amy', '2026-10-17T09:10:00+00:00'),
        ]}
      />,
    )

    const items = screen.getAllByRole('listitem')
    expect(items.map((item) => item.textContent)).toEqual([
      'Resumed by nurse-bo · 17 Oct, 09:25',
      'Paused by nurse-amy · 17 Oct, 09:10',
    ])
    expect(screen.getByRole('group', { name: 'Recent changes' })).toBeTruthy()
  })

  it('says so when nobody has touched the switch', () => {
    render(<MonitoringHistory changes={[]} />)

    expect(screen.getByText('No changes this shift')).toBeTruthy()
    expect(screen.queryByRole('list')).toBeNull()
  })

  it('shows only the five most recent changes', () => {
    const changes = Array.from({ length: 7 }, (_, index) =>
      change(index % 2 === 0, 'nurse', `2026-10-17T09:${String(50 - index).padStart(2, '0')}:00+00:00`),
    )

    render(<MonitoringHistory changes={changes} />)

    const items = screen.getAllByRole('listitem')
    expect(items).toHaveLength(5)
    expect(items[0].textContent).toContain('09:50')
    expect(items[4].textContent).toContain('09:46')
  })

  it('tells a pause from a resume by text as well as colour', () => {
    const { container } = render(
      <MonitoringHistory changes={[change(false, 'nurse', '2026-10-17T09:10:00+00:00')]} />,
    )

    const what = container.querySelector('.monitoring-history__what')
    expect(what?.textContent).toBe('Paused')
    expect(what?.className).toContain('monitoring-history__what--paused')
  })

  it('splits each row into a who/action piece and a time piece so they can wrap separately', () => {
    const { container } = render(
      <MonitoringHistory changes={[change(true, 'nurse-bo', '2026-10-17T09:25:00+00:00')]} />,
    )

    const row = container.querySelector('.monitoring-history__change')
    const who = row?.querySelector('.monitoring-history__who')
    const when = row?.querySelector('.monitoring-history__when')
    expect(who?.textContent).toBe('Resumed by nurse-bo')
    expect(when?.textContent).toBe(' · 17 Oct, 09:25')
    expect(row?.textContent).toBe('Resumed by nurse-bo · 17 Oct, 09:25')
  })
})

/** jsdom doesn't evaluate @media conditions for getComputedStyle, so this checks the
 * stylesheet text directly: below 480px each row wraps its who/action onto one line
 * and its timestamp onto the next, and the list's text grows to >= 14px (T309). */
describe('monitoringHistory.css phone layout', () => {
  it('wraps the row and gives the timestamp its own line below 480px', () => {
    const mobileBlock = monitoringHistoryCss.match(/@media \(max-width: 480px\) \{([\s\S]*)\}\s*$/)?.[1]
    expect(mobileBlock).toBeTruthy()

    expect(mobileBlock).toMatch(/\.monitoring-history__change\s*\{[^}]*flex-wrap:\s*wrap/)
    expect(mobileBlock).toMatch(/\.monitoring-history__when\s*\{[^}]*flex-basis:\s*100%/)
    expect(mobileBlock).toMatch(/\.monitoring-history__empty,\s*\n\s*\.monitoring-history__list\s*\{[^}]*font-size:\s*var\(--text-md\)/)
  })
})
