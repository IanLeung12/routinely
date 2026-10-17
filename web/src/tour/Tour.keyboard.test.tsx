import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { TOUR_STEPS } from './steps.ts'
import { Tour } from './Tour.tsx'

afterEach(cleanup)

const LAST = TOUR_STEPS.length

function control(name: 'Back' | 'Next' | 'Close') {
  return screen.getByRole('button', { name }) as HTMLButtonElement
}

function stepCount() {
  return screen.getByRole('dialog').querySelector('.tour__count')?.textContent
}

describe('Tour keyboard access', () => {
  it('tabs through Back, Next and Close in that order, skipping Back while it is disabled', async () => {
    const user = userEvent.setup()
    render(<Tour />)

    // Step 1 has nothing to go back to, so the first Tab stop is Next.
    expect(control('Back').disabled).toBe(true)
    await user.tab()
    expect(document.activeElement).toBe(control('Next'))
    await user.tab()
    expect(document.activeElement).toBe(control('Close'))

    // On a middle step all three are reachable; walking back from Close shows
    // the order a nurse tabs through: Back, then Next, then Close.
    await user.keyboard('{ArrowRight}')
    expect(stepCount()).toBe(`2 of ${LAST}`)
    expect(control('Back').disabled).toBe(false)
    await user.tab({ shift: true })
    expect(document.activeElement).toBe(control('Next'))
    await user.tab({ shift: true })
    expect(document.activeElement).toBe(control('Back'))
  })

  it('advances a step on Enter and goes back on Space, keeping focus on the control', async () => {
    const user = userEvent.setup()
    render(<Tour />)

    await user.tab()
    expect(document.activeElement).toBe(control('Next'))

    await user.keyboard('{Enter}')
    expect(stepCount()).toBe(`2 of ${LAST}`)
    expect(screen.getByRole('heading', { name: TOUR_STEPS[1].title })).toBeTruthy()
    // Focus stays put, so Enter again is enough to keep going.
    expect(document.activeElement).toBe(control('Next'))

    await user.keyboard('{Enter}')
    expect(stepCount()).toBe(`3 of ${LAST}`)
    expect(screen.getByRole('heading', { name: TOUR_STEPS[2].title })).toBeTruthy()

    await user.tab({ shift: true })
    expect(document.activeElement).toBe(control('Back'))
    await user.keyboard(' ')
    expect(stepCount()).toBe(`2 of ${LAST}`)
    expect(screen.getByRole('heading', { name: TOUR_STEPS[1].title })).toBeTruthy()
    expect(document.activeElement).toBe(control('Back'))
  })

  it('reaches the last step with Enter, where Close is the only way on', async () => {
    const onClose = vi.fn()
    const user = userEvent.setup()
    render(<Tour onClose={onClose} />)

    await user.tab()
    expect(document.activeElement).toBe(control('Next'))
    for (let i = 1; i < LAST; i++) {
      await user.keyboard('{Enter}')
    }
    expect(stepCount()).toBe(`${LAST} of ${LAST}`)
    expect(screen.getByRole('heading', { name: TOUR_STEPS[LAST - 1].title })).toBeTruthy()

    // Next is spent on the last card: Enter on it does nothing. Disabling the
    // focused button drops focus, so tabbing restarts at Back and then skips the
    // disabled Next to reach Close, which finishes the tour.
    expect(control('Next').disabled).toBe(true)
    await user.keyboard('{Enter}')
    expect(stepCount()).toBe(`${LAST} of ${LAST}`)
    expect(onClose).not.toHaveBeenCalled()

    await user.tab()
    expect(document.activeElement).toBe(control('Back'))
    await user.tab()
    expect(document.activeElement).toBe(control('Close'))
    await user.keyboard('{Enter}')
    expect(onClose).toHaveBeenCalledOnce()
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('closes with Escape without needing to focus anything first', async () => {
    const onClose = vi.fn()
    const user = userEvent.setup()
    render(<Tour onClose={onClose} />)

    expect(document.activeElement).toBe(document.body)
    await user.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalledOnce()
    expect(screen.queryByRole('dialog')).toBeNull()
  })
})
