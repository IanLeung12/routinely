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

  it('reuses the canvas\' own node marker as its swatch, hidden from screen readers', () => {
    render(<TaskMapLegend />)

    const items = screen.getAllByRole('listitem')
    ;['pending', 'done', 'omission', 'repeat', 'sequence'].forEach((state, index) => {
      const swatch = items[index].querySelector('.task-map__dot')
      expect(swatch?.className).toBe(`task-map__dot task-map__dot--${state}`)
      expect(swatch?.getAttribute('aria-hidden')).toBe('true')
      // Only the colour: the word beside it is what the swatch stands for.
      expect(swatch?.textContent).toBe('')
    })
  })

  it('names the two marks the canvas makes without a colour', () => {
    render(<TaskMapLegend />)

    // The dashed optional step and the glow on the step that comes next are both
    // drawn, not written, so the key says what they mean.
    const note = screen.getByText(/Dashed = optional step/)
    expect(note.textContent).toContain('glowing = ready next')
    expect(note.textContent).toContain('side by side may happen in either order')
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
