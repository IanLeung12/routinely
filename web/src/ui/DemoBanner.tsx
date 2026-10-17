export function DemoBanner({ onDismiss }: { onDismiss?: () => void }) {
  return (
    <div role="note" style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      flexWrap: 'wrap', gap: 'var(--space-2)', padding: 'var(--space-2) var(--space-3)',
      background: 'var(--panel)', color: 'var(--muted)',
      border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)',
      fontSize: 'var(--text-sm)',
    }}>
      <span>Demo mode: synthetic residents, no real patient data. Flags a change for review; never a diagnosis.</span>
      {onDismiss && <button type="button" className="btn btn--secondary" onClick={onDismiss}>Dismiss</button>}
    </div>
  )
}
