import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ResidentDetail } from './ResidentDetail.tsx'

/** T340: the monitoring block (toggle, history, consent) used to sit between the name
 * and the status chip in one packed header row. It now lives in its own full-width
 * row below the name/room/chip row, so the chip should land before it in DOM order. */

function offline() {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')))
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('ResidentDetail header layout (T340)', () => {
  it('keeps the status chip in the title row, before the monitoring block', async () => {
    offline()

    const { container } = render(<ResidentDetail residentId="mrs-k" onBack={() => {}} />)
    await screen.findByRole('heading', { level: 1, name: 'Mrs. K' })

    const header = container.querySelector('.resident-detail__header')
    expect(header).toBeTruthy()

    const titleRow = header?.querySelector('.resident-detail__title-row')
    const monitoring = header?.querySelector('.resident-detail__monitoring')
    expect(titleRow).toBeTruthy()
    expect(monitoring).toBeTruthy()

    const chip = titleRow?.querySelector('.status-chip')
    expect(chip).toBeTruthy()
    expect(titleRow?.contains(chip ?? null)).toBe(true)

    const all = Array.from(header?.querySelectorAll('*') ?? [])
    expect(all.indexOf(chip as Element)).toBeLessThan(all.indexOf(monitoring as Element))

    expect(screen.getByRole('switch', { name: 'Monitoring in room 204' })).toBeTruthy()
  })
})
