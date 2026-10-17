import type { CaptureFrame } from '../contracts.ts'

const connections = [[11, 12], [11, 13], [13, 15], [12, 14], [14, 16], [11, 23], [12, 24], [23, 24]]

/** Which frame of a recording is closest to `t`, or -1 when it has no frames. */
function nearestIndex(frames: CaptureFrame[], t: number) {
  return frames.reduce((closest, frame, index) =>
    closest < 0 || Math.abs(frame.t - t) < Math.abs(frames[closest].t - t) ? index : closest, -1)
}

/** A recording and which of its frames is on screen; index -1 means it has none. */
type Layer = { frames: CaptureFrame[], index: number }

/** Where the drawn frame sits in its own recording. Only called with a frame to draw. */
function position({ frames, index }: Layer) {
  return `frame ${index + 1} of ${frames.length} at ${frames[index].t.toFixed(1)} s`
}

/** What the drawing says in words, for a nurse on a screen reader who can't see the two
 * skeletons: which recordings are drawn over each other, and where in them this frame
 * sits (web guide: accessible, never colour alone). */
function comparison(today: Layer, usual: Layer) {
  if (today.index >= 0 && usual.index >= 0) {
    return `Today's routine drawn over the usual routine, ${position(today)}`
  }
  if (today.index >= 0) {
    return `Today's routine, with no usual routine to compare it with, ${position(today)}`
  }
  return `The usual routine, with nothing recorded today to compare it with, ${position(usual)}`
}

export default function GhostReplay({ today, normal, t, width = 480, height = 360 }: {
  today: CaptureFrame[]
  normal: CaptureFrame[]
  t: number
  width?: number
  height?: number
}) {
  const layers = {
    normal: { frames: normal, index: nearestIndex(normal, t) },
    today: { frames: today, index: nearestIndex(today, t) },
  }
  if (layers.today.index < 0 && layers.normal.index < 0) return <p>No skeleton data</p>

  return (
    <figure className="ghost-replay">
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={comparison(layers.today, layers.normal)}>
        {(['normal', 'today'] as const).map(layer => {
          const { frames, index: frameIndex } = layers[layer]
          if (frameIndex < 0) return null
          const frame = frames[frameIndex]
          const color = layer === 'normal' ? 'var(--ghost-usual)' : 'var(--ghost-today)'
          return (
            <g key={layer} data-layer={layer} opacity={layer === 'normal' ? 0.4 : 1} fill={color} stroke={color}>
              {frame.poses.map((pose, poseIndex) => (
                <g key={poseIndex}>
                  {connections.map(([start, end]) => {
                    const a = pose.landmarks[start]
                    const b = pose.landmarks[end]
                    return a && b ? <line key={`${start}-${end}`} x1={a.x * width} y1={a.y * height} x2={b.x * width} y2={b.y * height} strokeWidth={2} /> : null
                  })}
                  {pose.landmarks.map((point, index) => (
                    <circle key={index} cx={point.x * width} cy={point.y * height} r={3} />
                  ))}
                </g>
              ))}
            </g>
          )
        })}
      </svg>
      <figcaption><span className="ghost-replay__caption--today">Today</span> / <span className="ghost-replay__caption--usual">Usual</span></figcaption>
      <p className="ghost-replay__disclaimer">Demo recording: the body is drawn as a stand-in; the hand follows the tracked hand box.</p>
    </figure>
  )
}
