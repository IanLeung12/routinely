import { useId } from 'react'

export function PrivacyPanel() {
  const headingId = useId()

  return (
    <section aria-labelledby={headingId}>
      <h2 id={headingId}>Privacy and limits</h2>
      <ul>
        <li>Only skeleton points and object boxes leave the camera. No video is stored.</li>
        <li>No face recognition. Each camera is linked to a room by configuration.</li>
        <li>It flags a change for a nurse to review. It is not a medical assessment.</li>
        <li>Low-confidence moments are shown as unclear, never counted as errors.</li>
        <li>Pose tracking is less accurate with walkers, wheelchairs and unusual postures.</li>
        <li>Residents or their decision-maker opt in, and monitoring can be turned off per room.</li>
      </ul>
    </section>
  )
}
