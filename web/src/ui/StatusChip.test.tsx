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
})
