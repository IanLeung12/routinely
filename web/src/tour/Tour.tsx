import { useEffect, useState } from 'react'
import { Button } from '../ui/Button.tsx'
import { TOUR_STEPS } from './steps.ts'
import './tour.css'

/** Presenter cue card for the guided demo (SPEC section 10). Mounted by App.tsx only
 * behind `?tour=1`, so it can never show up on the real demo path. */
export function Tour({ onClose }: { onClose?: () => void } = {}) {
  const [index, setIndex] = useState(0)
  const [closed, setClosed] = useState(false)

  const step = TOUR_STEPS[index]
  const isFirst = index === 0
  const isLast = index === TOUR_STEPS.length - 1

  function close() {
    setClosed(true)
    onClose?.()
  }

  useEffect(() => {
    if (closed) return
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') close()
      else if (e.key === 'ArrowRight') setIndex(i => Math.min(i + 1, TOUR_STEPS.length - 1))
      else if (e.key === 'ArrowLeft') setIndex(i => Math.max(i - 1, 0))
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [closed])

  if (closed) return null

  return (
    <div className="tour" role="dialog" aria-label="Guided demo tour">
      <h2 className="tour__title">{step.title}</h2>
      <p className="tour__body">{step.body}</p>
      <div className="tour__footer">
        <span className="tour__count">{index + 1} of {TOUR_STEPS.length}</span>
        <div className="tour__nav">
          <Button onClick={() => setIndex(i => i - 1)} disabled={isFirst}>Back</Button>
          <Button onClick={() => setIndex(i => i + 1)} disabled={isLast}>Next</Button>
          <Button variant="primary" onClick={close}>Close</Button>
        </div>
      </div>
    </div>
  )
}

export default Tour
