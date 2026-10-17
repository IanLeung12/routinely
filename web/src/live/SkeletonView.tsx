import type { CaptureFrame, Landmark } from '../contracts.ts'

type SkeletonViewProps = {
  frame: CaptureFrame | null
  width?: number
  height?: number
}

/** MediaPipe pose landmark indices: shoulders, arms, torso (SPEC section 16). */
const POSE_CONNECTIONS: [number, number][] = [
  [11, 12], // shoulder to shoulder
  [11, 13], // left shoulder to elbow
  [13, 15], // left elbow to wrist
  [12, 14], // right shoulder to elbow
  [14, 16], // right elbow to wrist
  [11, 23], // left shoulder to hip
  [12, 24], // right shoulder to hip
  [23, 24], // hip to hip
]

function toPixels(landmark: Landmark, width: number, height: number) {
  return { x: landmark.x * width, y: landmark.y * height }
}

export function SkeletonView({ frame, width = 480, height = 360 }: SkeletonViewProps) {
  if (!frame) {
    return (
      <div className="skeleton-view skeleton-view--empty" style={{ width, height }}>
        <p>Waiting for camera</p>
      </div>
    )
  }

  return (
    <svg
      className="skeleton-view"
      role="img"
      aria-label="Skeleton view"
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
    >
      {frame.objects.map((object, index) => {
        const x1 = object.box.x1 * width
        const y1 = object.box.y1 * height
        const boxWidth = (object.box.x2 - object.box.x1) * width
        const boxHeight = (object.box.y2 - object.box.y1) * height
        return (
          <g key={`object-${index}`}>
            <rect
              className="skeleton-view__box"
              x={x1}
              y={y1}
              width={boxWidth}
              height={boxHeight}
              fill="none"
              stroke="var(--skeleton-box)"
              strokeWidth={2}
            />
            <text className="skeleton-view__label" x={x1} y={y1 - 4} fill="var(--skeleton-box)" fontSize={12}>
              {object.label}
            </text>
          </g>
        )
      })}

      {frame.poses.map((pose, poseIndex) => (
        <g key={`pose-${poseIndex}`} className="skeleton-view__pose">
          {POSE_CONNECTIONS.map(([startIndex, endIndex]) => {
            const start = pose.landmarks[startIndex]
            const end = pose.landmarks[endIndex]
            if (!start || !end) return null
            const a = toPixels(start, width, height)
            const b = toPixels(end, width, height)
            return (
              <line
                key={`bone-${poseIndex}-${startIndex}-${endIndex}`}
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke="var(--skeleton-bone)"
                strokeWidth={2}
              />
            )
          })}
          {pose.landmarks.map((landmark, landmarkIndex) => {
            const { x, y } = toPixels(landmark, width, height)
            return (
              <circle
                key={`pose-landmark-${poseIndex}-${landmarkIndex}`}
                className="skeleton-view__landmark"
                cx={x}
                cy={y}
                r={3}
                fill="var(--skeleton-bone)"
              />
            )
          })}
        </g>
      ))}

      {frame.hands.map((hand, handIndex) => (
        <g key={`hand-${handIndex}`} className="skeleton-view__hand">
          {hand.landmarks.map((landmark, landmarkIndex) => {
            const { x, y } = toPixels(landmark, width, height)
            return (
              <circle
                key={`hand-landmark-${handIndex}-${landmarkIndex}`}
                className="skeleton-view__landmark"
                cx={x}
                cy={y}
                r={2.5}
                fill={hand.handedness === 'left' ? 'var(--hand-left)' : 'var(--hand-right)'}
              />
            )
          })}
        </g>
      ))}
    </svg>
  )
}

export default SkeletonView
