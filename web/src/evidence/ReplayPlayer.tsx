import { useEffect, useState } from 'react'
import type { CaptureFrame } from '../contracts.ts'
import SkeletonView from '../live/SkeletonView.tsx'

type ReplayPlayerProps = {
  frames: CaptureFrame[]
  autoPlay?: boolean
  fps?: number
}

export function ReplayPlayer({ frames, autoPlay = false, fps = 10 }: ReplayPlayerProps) {
  const [playback, setPlayback] = useState({ position: 0, playing: autoPlay })
  const last = Math.max(0, frames.length - 1)
  const current = Math.min(playback.position, last)
  const playing = playback.playing && current < last
  const frameRate = Number.isFinite(fps) && fps > 0 ? fps : 10

  useEffect(() => {
    if (!playing) return
    const timer = setInterval(() => setPlayback((previous) => {
      const position = Math.min(previous.position + 1, last)
      return { position, playing: position < last }
    }), 1000 / frameRate)
    return () => clearInterval(timer)
  }, [playing, current, last, frameRate])

  if (frames.length === 0) return <p>No replay available</p>

  const seconds = Math.max(0, Math.floor(frames[current].t))
  const time = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`

  return (
    <div className="replay-player">
      <SkeletonView frame={frames[current]} />
      <button type="button" onClick={() => {
        setPlayback({ position: !playing && current === last ? 0 : current, playing: !playing })
      }}>
        {playing ? 'Pause' : 'Play'}
      </button>
      <input
        type="range"
        aria-label="Replay position"
        min={0}
        max={last}
        step={1}
        value={current}
        onChange={(event) => {
          const position = Number(event.target.value)
          setPlayback({ position, playing: playing && position < last })
        }}
      />
      <output aria-label="Replay time">{time}</output>
    </div>
  )
}

export default ReplayPlayer
