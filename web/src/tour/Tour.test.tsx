import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { TOUR_STEPS } from './steps.ts'
import { Tour } from './Tour.tsx'

afterEach(cleanup)

describe('Tour', () => {
  it('limits the phone card width and wraps its navigation buttons', async () => {
    const fs = await vi.importActual<{
      readFileSync: (path: string, encoding: 'utf8') => string
    }>('node:fs')
    const css = fs.readFileSync('src/tour/tour.css', 'utf8')
    expect(css).toMatch(/@media\s*\(max-width:\s*480px\)/)
    expect(css).toMatch(/\.tour\s*\{[^}]*max-width:\s*calc\(100vw - 2rem\)/)
    expect(css).toMatch(/\.tour__footer,\s*\.tour__nav\s*\{[^}]*flex-wrap:\s*wrap/)
  })

  it('starts on step 1 and never uses diagnostic language', () => {
    render(<Tour />)
    expect(screen.getByText(`1 of ${TOUR_STEPS.length}`)).toBeTruthy()
    expect(screen.getByRole('heading', { name: TOUR_STEPS[0].title })).toBeTruthy()
    for (const step of TOUR_STEPS) {
      expect(step.title.toLowerCase()).not.toContain('diagnos')
      expect(step.body.toLowerCase()).not.toContain('diagnos')
    }
  })

  it('Alert step describes the flag rule as within 48 hours', () => {
    const alertStep = TOUR_STEPS.find((step) => step.title === 'Alert')
    expect(alertStep?.body).toContain('48 hours')
    expect(alertStep?.body.toLowerCase()).not.toContain('in a row')
  })

  it('disables Back on the first step and Next on the last step', () => {
    render(<Tour />)
    expect((screen.getByRole('button', { name: 'Back' }) as HTMLButtonElement).disabled).toBe(true)

    for (let i = 0; i < TOUR_STEPS.length - 1; i++) {
      fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    }
    expect(screen.getByText(`${TOUR_STEPS.length} of ${TOUR_STEPS.length}`)).toBeTruthy()
    expect((screen.getByRole('button', { name: 'Next' }) as HTMLButtonElement).disabled).toBe(true)
  })

  it('moves forward with Next and back with Back', () => {
    render(<Tour />)
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(screen.getByRole('heading', { name: TOUR_STEPS[1].title })).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Back' }))
    expect(screen.getByRole('heading', { name: TOUR_STEPS[0].title })).toBeTruthy()
  })

  it('hides itself and calls onClose when Close is clicked', () => {
    const onClose = vi.fn()
    render(<Tour onClose={onClose} />)
    fireEvent.click(screen.getByRole('button', { name: 'Close' }))
    expect(onClose).toHaveBeenCalledOnce()
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('Escape hides the card and calls onClose', () => {
    const onClose = vi.fn()
    render(<Tour onClose={onClose} />)
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledOnce()
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('ArrowRight/ArrowLeft step through and respect bounds', () => {
    render(<Tour />)
    fireEvent.keyDown(window, { key: 'ArrowLeft' })
    expect(screen.getByRole('heading', { name: TOUR_STEPS[0].title })).toBeTruthy()

    fireEvent.keyDown(window, { key: 'ArrowRight' })
    expect(screen.getByRole('heading', { name: TOUR_STEPS[1].title })).toBeTruthy()

    for (let i = 0; i < TOUR_STEPS.length; i++) {
      fireEvent.keyDown(window, { key: 'ArrowRight' })
    }
    expect(screen.getByText(`${TOUR_STEPS.length} of ${TOUR_STEPS.length}`)).toBeTruthy()

    fireEvent.keyDown(window, { key: 'ArrowLeft' })
    expect(screen.getByRole('heading', { name: TOUR_STEPS[TOUR_STEPS.length - 2].title })).toBeTruthy()
  })
})
