import { apiUrl } from '../config.ts'
import type { Alert, FeedbackVerdict } from '../contracts.ts'
import { mockAlerts } from '../mock/alerts.ts'

export async function fetchAlerts(): Promise<Alert[]> {
  try {
    const response = await fetch(`${apiUrl}/alerts`)
    if (response.ok) return await response.json() as Alert[]
  } catch { /* Keep the dashboard usable while offline. */ }
  return mockAlerts
}

export async function fetchAlert(id: string): Promise<Alert | null> {
  try {
    const response = await fetch(`${apiUrl}/alerts/${encodeURIComponent(id)}`)
    if (response.status === 404) return null
    if (response.ok) return await response.json() as Alert
  } catch { /* Use the matching local alert when the API is unavailable. */ }
  return mockAlerts.find(alert => alert.alert_id === id) ?? null
}

export async function postFeedback(
  id: string, verdict: FeedbackVerdict, note?: string,
): Promise<Alert> {
  try {
    const response = await fetch(`${apiUrl}/alerts/${encodeURIComponent(id)}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ verdict, note }),
    })
    if (response.ok) return await response.json() as Alert
  } catch { /* Record feedback locally when the API is unavailable. */ }

  const alert = mockAlerts.find(alert => alert.alert_id === id)
  if (!alert) throw new Error(`Unknown alert: ${id}`)
  alert.feedback = { verdict, by: 'nurse', at: new Date().toISOString(), note }
  return alert
}
