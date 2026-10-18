import { useEffect, useState } from 'react'
import type { CaptureFrame } from '../contracts.ts'
import SkeletonView from '../live/SkeletonView.tsx'
import Button from '../ui/Button.tsx'
import './evidence.css'
import { prefersReducedMotion } from './reducedMotion.ts'

/** A moment worth jumping to inside a replay — an error out of the session's marker list
 * (`ReplayMarker`, SPEC section 17), timed on the same clock as `frames[i].t`. `kind` is the
 * error type and only tints the tick: the marker is named after what happened, so the
 * category is never carried by colour alone. */
export type ReplayPlayerMarker = { t: number; label: string; kind?: string }

type ReplayPlayerProps = {
  frames: CaptureFrame[]
  autoPlay?: boolean
  fps?: number
  markers?: ReplayPlayerMarker[]
}

/** Half speed to watch a fumble closely, double to skim to the next error. */
const SPEEDS = [0.5, 1, 2]

/** m:ss — the replay clock and the marker names write a session time the same way. */
function clock(t: number): string {
  const seconds = Math.max(0, Math.floor(t))
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

/** Where a marker sits along the bar: its time as a share of the last frame's, clamped so a
 * marker just outside the kept frames still lands on the timeline rather than beside it. */
function markerOffset(t: number, end: number): number {
  return end > 0 ? Math.min(Math.max(t / end, 0), 1) * 100 : 0
}

export function ReplayPlayer({ frames, autoPlay = false, fps = 10, markers }: ReplayPlayerProps) {
  const [playback, setPlayback] = useState(() => ({ position: 0, playing: autoPlay && !prefersReducedMotion() }))
  const [speed, setSpeed] = useState(1)
  const last = Math.max(0, frames.length - 1)
  const current = Math.min(playback.position, last)
  const playing = playback.playing && current < last
  const frameRate = (Number.isFinite(fps) && fps > 0 ? fps : 10) * speed

  useEffect(() => {
    if (!playing) return
    const timer = setInterval(() => setPlayback((previous) => {
      const position = Math.min(previous.position + 1, last)
      return { position, playing: position < last }
    }), 1000 / frameRate)
    return () => clearInterval(timer)
  }, [playing, current, last, frameRate])

  if (frames.length === 0) return <p>No replay available</p>

  const time = clock(frames[current].t)
  const valueText = `${frames[current].t.toFixed(1)} s of ${frames[last].t.toFixed(1)} s`

  const togglePlay = () => {
    setPlayback({ position: !playing && current === last ? 0 : current, playing: !playing })
  }

  /** Stepping a frame or jumping to a marker stops playback: the supervisor is holding still
   * on one moment, not watching on from it. */
  const pauseAt = (position: number) => {
    setPlayback({ position: Math.min(Math.max(position, 0), last), playing: false })
  }

  /** The first frame at or after the marker, so a fractional error time lands on a real frame. */
  const jumpTo = (t: number) => {
    const index = frames.findIndex((frame) => frame.t >= t)
    pauseAt(index === -1 ? last : index)
  }

  return (
    <div
      className="replay-player"
      role="group"
      aria-label="Skeleton replay. Press space to play or pause, arrow keys to step one frame."
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.target !== event.currentTarget) return
        if (event.key === ' ' || event.key === 'Spacebar') {
          event.preventDefault()
          togglePlay()
        } else if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
          event.preventDefault()
          pauseAt(current + (event.key === 'ArrowRight' ? 1 : -1))
        }
      }}
    >
      <SkeletonView frame={frames[current]} />
      <div className="replay-player__controls">
        <Button onClick={togglePlay} aria-pressed={playing}>
          {playing ? 'Pause' : 'Play'}
        </Button>
        {/* The markers come after the slider in the markup so the transport keeps its tab
            order — player, Play, scrub bar, then each error — while sitting over the bar. */}
        <div className="replay-player__timeline">
          <input
            type="range"
            aria-label="Replay position"
            aria-valuetext={valueText}
            min={0}
            max={last}
            step={1}
            value={current}
            onChange={(event) => {
              const position = Number(event.target.value)
              setPlayback({ position, playing: playing && position < last })
            }}
          />
          {markers && markers.length > 0 && (
            <div className="replay-player__markers">
              {markers.map((marker, index) => {
                const moment = `${marker.label} at ${clock(marker.t)}`
                return (
                  <button
                    key={`${marker.t}-${index}`}
                    type="button"
                    className={`replay-player__marker${marker.kind ? ` replay-player__marker--${marker.kind}` : ''}`}
                    style={{ left: `${markerOffset(marker.t, frames[last].t)}%` }}
                    aria-label={`Jump to ${moment}`}
                    title={moment}
                    onClick={() => jumpTo(marker.t)}
                  />
                )
              })}
            </div>
          )}
        </div>
        <output aria-label="Replay time">{time}</output>
      </div>
      {/* `role="toolbar"` rather than `role="group"`: the player itself is the group, and a
          second one would leave "the replay" ambiguous to a screen reader. */}
      <div className="replay-player__speed" role="toolbar" aria-label="Playback speed">
        <span className="replay-player__speed-label">Speed</span>
        {SPEEDS.map((option) => (
          <Button key={option} aria-pressed={speed === option} onClick={() => setSpeed(option)}>
            {`${option}×`}
          </Button>
        ))}
      </div>
    </div>
  )
}

export default ReplayPlayer
