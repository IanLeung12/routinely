import { useState } from 'react'
import { apiUrl } from '../config.ts'
import './demoBanner.css'

async function defaultReset() {
  const response = await fetch(`${apiUrl}/demo/reset`, { method: 'POST' })
  if (!response.ok) throw new Error(`demo reset failed: ${response.status}`)
  window.location.reload()
}

export function DemoBanner({ onDismiss, onReset = defaultReset }: { onDismiss?: () => void; onReset?: () => Promise<void> }) {
  const [resetting, setResetting] = useState(false)
  const [resetError, setResetError] = useState(false)

  async function handleReset() {
    setResetting(true)
    setResetError(false)
    try {
      await onReset()
    } catch {
      setResetError(true)
    } finally {
      setResetting(false)
    }
  }

  return (
    <div role="note" className="demo-banner">
      <span>Demo mode: synthetic residents, no real patient data. Changes are flagged for review only.</span>
      <div className="demo-banner__actions">
        {resetError && <span role="alert" className="demo-banner__error">Couldn&apos;t reset the demo</span>}
        <button type="button" className="btn btn--secondary" onClick={handleReset} disabled={resetting}>
          Reset demo
        </button>
        {onDismiss && <button type="button" className="btn btn--secondary" onClick={onDismiss}>Dismiss</button>}
      </div>
    </div>
  )
}
