import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import { EscalationTimeline } from './EscalationTimeline.tsx'

afterEach(cleanup)

it('renders each supplied transition with its time and actor, without inventing private fields', () => {
  const events = [
    { event: 'started', at: '2026-10-17T12:00:00Z', actor: 'server', state: 'pending' as const, detail: null },
    { event: 'checked_in', at: '2026-10-17T12:00:01Z', actor: 'person', state: 'ok' as const },
    { event: 'alarmed', at: '2026-10-17T12:02:01Z', actor: 'server', state: 'alarm' as const, detail: 'nurse-ana' },
    { event: 'escalated', at: '2026-10-17T12:04:01Z', actor: 'server', state: 'escalated' as const, detail: 'lena' },
    { event: 'acknowledged', at: '2026-10-17T12:04:20Z', actor: 'lena', state: 'acknowledged' as const },
    { event: 'resolved', at: '2026-10-17T12:06:00Z', actor: 'lena', state: 'resolved' as const, detail: 'helped' },
  ]
  const { container } = render(<EscalationTimeline events={events} />)
  for (const label of ['Check-in sent', 'Checked in', 'Alarm raised, notified nurse-ana', 'Escalated to lena', 'Acknowledged by lena', 'Resolved by lena: helped']) {
    expect(screen.getByText(label)).toBeTruthy()
  }
  expect([...container.querySelectorAll('time')].map(time => time.dateTime)).toEqual(events.map(event => event.at))
  expect(screen.queryByText(/location/i)).toBeNull()
})

it('handles empty or partial event logs without fabricating steps', () => {
  const view = render(<EscalationTimeline events={[]} />)
  expect(screen.getByText('No events yet.')).toBeTruthy()
  view.rerender(<EscalationTimeline events={[{ event: 'alarmed', at: '2026-10-17T12:02:00Z', actor: 'server', state: 'alarm' }]} />)
  expect(screen.getAllByRole('listitem')).toHaveLength(1)
  expect(screen.queryByText('Check-in sent')).toBeNull()
  expect(screen.queryByText(/Escalated to/)).toBeNull()
})
