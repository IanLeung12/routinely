import { useState } from 'react'
import { apiUrl } from '../config.ts'

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
    <div role="note" style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      flexWrap: 'wrap', gap: 'var(--space-2)', padding: 'var(--space-2) var(--space-3)',
      background: 'var(--panel)', color: 'var(--muted)',
      border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)',
      fontSize: 'var(--text-sm)',
    }}>
      <span>Demo mode: synthetic residents, no real patient data. Changes are flagged for review only.</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
        {resetError && <span>Couldn&apos;t reset the demo</span>}
        <button type="button" className="btn btn--secondary" onClick={handleReset} disabled={resetting}>
          Reset demo
        </button>
        {onDismiss && <button type="button" className="btn btn--secondary" onClick={onDismiss}>Dismiss</button>}
      </div>
    </div>
  )
}
