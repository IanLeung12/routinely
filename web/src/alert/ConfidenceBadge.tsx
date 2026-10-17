/** Show uncertainty beside a step or alert without treating it as an error. */
export function ConfidenceBadge({ confidence, unclear }: { confidence: number; unclear?: boolean }) {
  const clamped = Math.min(1, Math.max(0, confidence))
  const level = unclear ? 'unclear' : clamped >= 0.8 ? 'high' : clamped >= 0.5 ? 'medium' : 'low'
  const label = level === 'unclear' ? 'Unclear' : `${level[0].toUpperCase()}${level.slice(1)} confidence`

  return (
    <span
      className="confidence-badge"
      data-level={level}
      title={unclear ? 'Low confidence; not counted as an error' : undefined}
      style={{ color: `var(--color-${level})` }}
    >
      <span>{label}</span>{' '}<span>{Math.round(clamped * 100)}%</span>
    </span>
  )
}
