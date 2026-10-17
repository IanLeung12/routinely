import type { CaptureFrame } from '../contracts.ts'

const connections = [[11, 12], [11, 13], [13, 15], [12, 14], [14, 16], [11, 23], [12, 24], [23, 24]]

function nearest(frames: CaptureFrame[], t: number) {
  return frames.reduce<CaptureFrame | undefined>((closest, frame) =>
    !closest || Math.abs(frame.t - t) < Math.abs(closest.t - t) ? frame : closest, undefined)
}

export default function GhostReplay({ today, normal, t, width = 480, height = 360 }: {
  today: CaptureFrame[]
  normal: CaptureFrame[]
  t: number
  width?: number
  height?: number
}) {
  if (today.length === 0 && normal.length === 0) return <p>No skeleton data</p>

  return (
    <figure>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Today and usual skeleton replay">
        {(['normal', 'today'] as const).map(layer => {
          const frame = nearest(layer === 'normal' ? normal : today, t)
          if (!frame) return null
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
    </figure>
  )
}
