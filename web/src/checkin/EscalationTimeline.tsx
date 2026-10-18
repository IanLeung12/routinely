import type { CheckInEvent } from './types.ts'
import './alarm.css'

function eventLabel(event: CheckInEvent): string {
  switch (event.event) {
    case 'alert': return 'Alert raised'
    case 'pending':
    case 'checkin_sent': return 'Check-in sent'
    case 'no_answer': return 'No answer'
    case 'alarm': return 'You were alarmed'
    case 'escalated': return event.next ? `Escalated to ${event.next}` : 'Escalated'
    case 'acknowledged': return event.actor ? `Acknowledged by ${event.actor}` : 'Acknowledged'
    case 'resolved': return `Resolved${event.actor ? ` by ${event.actor}` : ''}${event.reason ? `: ${event.reason.replaceAll('_', ' ')}` : ''}`
    case 'disconnect': return 'Device disconnected'
    case 'reconnect': return 'Device reconnected'
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
