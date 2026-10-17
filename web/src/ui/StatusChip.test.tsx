import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { StatusChip } from './StatusChip.tsx'

afterEach(() => {
  cleanup()
})

describe('StatusChip', () => {
  it('labels and colours each status', () => {
    const cases = [
      ['normal', 'Normal'],
      ['watch', 'Watch'],
      ['flagged', 'Flagged'],
    ] as const

    for (const [status, label] of cases) {
      render(<StatusChip status={status} />)
      const chip = screen.getByText(label)
      expect(chip.className).toContain(`status-chip--${status}`)
      cleanup()
    }
  })

  it('describes what each status means for hover and screen readers', () => {
    const cases = [
      ['normal', 'Within their usual range'],
      ['watch', 'Worth watching: trending away from their usual routine'],
      ['flagged', 'Change flagged for review'],
    ] as const

    for (const [status, description] of cases) {
      render(<StatusChip status={status} />)
      const chip = screen.getByLabelText(description)
      expect(chip.title).toBe(description)
      expect(description.toLowerCase()).not.toContain('diagnos')
      cleanup()
    }
  })
})
