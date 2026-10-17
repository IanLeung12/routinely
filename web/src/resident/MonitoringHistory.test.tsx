import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import type { MonitoringChange } from '../about/monitoringApi.ts'
import { MonitoringHistory } from './MonitoringHistory.tsx'

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
})
