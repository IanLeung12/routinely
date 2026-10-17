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
        <li>Residents or their decision-maker opt in; who consented and when is shown on each resident's page.</li>
        <li>Monitoring can be paused per room; every pause and resume is logged with who and when.</li>
      </ul>
    </section>
  )
}
