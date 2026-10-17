import type { SuggestedCheck } from '../contracts.ts'

const LABELS: Record<SuggestedCheck, string> = {
  infection_or_uti: 'Check for infection / UTI',
  hydration: 'Check hydration',
  medication_review: 'Review recent medication changes',
  cam_screen: 'Run a CAM delirium screen',
}

/** Suggested checks for a nurse to follow up on, alongside a flagged alert. */
export function SuggestedChecks({ checks }: { checks: SuggestedCheck[] }) {
  if (checks.length === 0) {
    return null
  }

  return (
    <ul className="suggested-checks">
      {checks.map((check) => (
        <li key={check} className="suggested-check">
          {LABELS[check]}
        </li>
      ))}
    </ul>
  )
}
