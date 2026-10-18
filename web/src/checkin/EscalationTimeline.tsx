import type { CheckInEvent } from './types.ts'
import './alarm.css'

function eventLabel(event: CheckInEvent): string {
  switch (event.event) {
    case 'started': return 'Check-in sent'
    case 'checked_in': return 'Checked in'
    // `alarmed`'s detail is the first supporter's id, or says nobody is linked
    // (`checkin.py`'s `_raise_alarm`) - which is not a name to read out.
    case 'alarmed': return event.detail && !event.detail.includes('nobody') ? `Alarm raised, notified ${event.detail}` : 'Alarm raised'
    case 'duress': return 'Silent help request raised'
    case 'escalated': return event.detail ? `Escalated to ${event.detail}` : 'Escalated'
    case 'escalation_exhausted': return 'No one left to alarm'
    case 'acknowledged': return `Acknowledged by ${event.actor}`
    case 'resolved': return `Resolved by ${event.actor}${event.detail ? `: ${event.detail.replaceAll('_', ' ')}` : ''}`
    case 'disconnected': return 'Device disconnected'
    case 'reconnected': return 'Device reconnected'
    default: return event.event.replaceAll('_', ' ')
  }
}

export function EscalationTimeline({ events }: { events: CheckInEvent[] }) {
  return (
    <section className="escalation-timeline" aria-label="Escalation timeline">
      <h3>Escalation timeline</h3>
      {events.length === 0 ? <p>No events yet.</p> : (
        <ol className="escalation-timeline__events">
          {events.map((event, index) => (
            <li key={`${event.at}-${index}`}>
              <span>{eventLabel(event)}</span>
              <time dateTime={event.at}>{new Date(event.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</time>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
