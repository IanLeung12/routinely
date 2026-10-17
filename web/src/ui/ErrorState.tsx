/** Message for a failed fetch or offline mode. Announced to screen readers since it
 * replaces content the nurse was expecting to see. */
export function ErrorState({ message }: { message: string }) {
  return (
    <p className="error-state" role="alert">
      {message}
    </p>
  )
}

export default ErrorState
