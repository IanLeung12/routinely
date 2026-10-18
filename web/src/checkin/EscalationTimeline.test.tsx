import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import { EscalationTimeline } from './EscalationTimeline.tsx'

afterEach(cleanup)

it('renders each supplied transition with its time and actor, without inventing private fields', () => {
  const events = [
    { event: 'alert', at: '2026-10-17T12:00:00Z' },
    { event: 'checkin_sent', at: '2026-10-17T12:00:01Z' },
    { event: 'no_answer', at: '2026-10-17T12:02:01Z' },
    { event: 'alarm', at: '2026-10-17T12:02:01Z' },
    { event: 'escalated', at: '2026-10-17T12:04:01Z', next: 'Lena' },
    { event: 'acknowledged', at: '2026-10-17T12:04:20Z', actor: 'Lena' },
    { event: 'resolved', at: '2026-10-17T12:06:00Z', actor: 'Lena' },
  ]
  const { container } = render(<EscalationTimeline events={events} />)
  for (const label of ['Alert raised', 'Check-in sent', 'No answer', 'You were alarmed', 'Escalated to Lena', 'Acknowledged by Lena', 'Resolved by Lena']) {
    expect(screen.getByText(label)).toBeTruthy()
  }
  expect([...container.querySelectorAll('time')].map(time => time.dateTime)).toEqual(events.map(event => event.at))
  expect(screen.queryByText(/location/i)).toBeNull()
})

it('handles empty or partial event logs without fabricating steps', () => {
  const view = render(<EscalationTimeline events={[]} />)
  expect(screen.getByText('No events yet.')).toBeTruthy()
  view.rerender(<EscalationTimeline events={[{ event: 'alarm', at: '2026-10-17T12:02:00Z' }]} />)
  expect(screen.getAllByRole('listitem')).toHaveLength(1)
  expect(screen.queryByText('Alert raised')).toBeNull()
  expect(screen.queryByText(/Escalated to/)).toBeNull()
})
