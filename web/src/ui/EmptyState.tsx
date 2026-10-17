/** Message for a list or chart with nothing to show yet (e.g. "No sessions recorded"). */
export function EmptyState({ message }: { message: string }) {
  return <p className="empty-state">{message}</p>
}

export default EmptyState
