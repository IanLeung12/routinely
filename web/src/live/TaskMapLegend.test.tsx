import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { TaskMapLegend } from './TaskMapLegend.tsx'

afterEach(cleanup)

describe('TaskMapLegend', () => {
  it('explains all five task states in an accessible list', () => {
    render(<TaskMapLegend />)

    const list = screen.getByRole('list', { name: 'Task map legend' })
    expect(within(list).getAllByRole('listitem').map((item) => item.textContent)).toEqual([
      'not yet', '✓ done', '✕ missed step', '↻ repeated step', '⇄ out of order',
    ])
    expect(list.textContent).not.toMatch(/diagnos/i)
  })

  it('reuses the step list\'s own node as its swatch, hidden from screen readers', () => {
    render(<TaskMapLegend />)

    const items = screen.getAllByRole('listitem')
    ;['pending', 'done', 'omission', 'repeat', 'sequence'].forEach((state, index) => {
      const swatch = items[index].querySelector('.step__node')
      expect(swatch?.className).toBe(`step__node step__node--${state}`)
      expect(swatch?.getAttribute('aria-hidden')).toBe('true')
      // Only the colour: the word beside it is what the swatch stands for.
      expect(swatch?.textContent).toBe('')
    })
  })

  it('shows the same icon per state as the task map, hidden from screen readers', () => {
    render(<TaskMapLegend />)

    const items = screen.getAllByRole('listitem')
    const icons = ['', '✓', '✕', '↻', '⇄']
    icons.forEach((icon, index) => {
      if (!icon) return
      const iconSpan = Array.from(items[index].querySelectorAll('[aria-hidden="true"]')).find(
        (el) => el.textContent?.includes(icon),
      )
      expect(iconSpan).toBeDefined()
    })
  })
})
