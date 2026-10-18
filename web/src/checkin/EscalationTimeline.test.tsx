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

it("spells every other transition checkin.py can log, without reading a machine's own detail out loud", () => {
  const view = render(
    <EscalationTimeline
      events={[
        { event: 'duress', at: '2026-10-17T12:01:00Z', actor: 'person', state: 'alarm', detail: 'duress' },
        { event: 'disconnected', at: '2026-10-17T12:01:30Z', actor: 'server', state: 'alarm' },
        { event: 'reconnected', at: '2026-10-17T12:01:40Z', actor: 'server', state: 'alarm' },
        { event: 'escalation_exhausted', at: '2026-10-17T12:05:00Z', actor: 'server', state: 'escalated', detail: 'nobody left to alarm' },
      ]}
    />,
  )
  for (const label of ['Silent help request raised', 'Device disconnected', 'Device reconnected', 'No one left to alarm']) {
    expect(screen.getByText(label)).toBeTruthy()
  }
  // `alarmed`'s detail is a supporter id, except when it says nobody is linked.
  view.rerender(
    <EscalationTimeline events={[{ event: 'alarmed', at: '2026-10-17T12:02:00Z', actor: 'server', state: 'alarm', detail: 'nobody linked' }]} />,
  )
  expect(screen.getByText('Alarm raised')).toBeTruthy()
})
