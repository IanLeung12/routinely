/** Placeholder shown while a screen's data is still being fetched. */
export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <p className="loading" role="status" aria-live="polite">
      {label}
    </p>
  )
}

export default Loading
