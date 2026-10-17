import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ResidentDetail } from './ResidentDetail.tsx'
import residentPrintCss from './residentPrint.css?raw'

function offline() {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')))
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('ResidentDetail print', () => {
  it('prints the resident when the Print button is clicked, and hides the button itself', async () => {
    offline()
    const printSpy = vi.fn()
    vi.stubGlobal('print', printSpy)

    render(<ResidentDetail residentId="mrs-k" onBack={() => {}} />)
    await screen.findByRole('heading', { level: 1, name: 'Mrs. K' })

    const printButton = screen.getByRole('button', { name: 'Print' })
    expect(printButton.className).toContain('no-print')

    printButton.focus()
    expect(document.activeElement).toBe(printButton)

    fireEvent.click(printButton)

    expect(printSpy).toHaveBeenCalledTimes(1)
  })

  it('marks the back button and monitoring controls as no-print, keeping the rest printable', async () => {
    offline()
    render(<ResidentDetail residentId="mrs-k" onBack={() => {}} />)
    await screen.findByRole('heading', { level: 1, name: 'Mrs. K' })

    expect(screen.getByRole('button', { name: /unit overview/i }).className).toContain('no-print')
    expect(screen.getByRole('switch', { name: /monitoring in room/i }).closest('.no-print')).toBeTruthy()

    expect(screen.getByText(/Consent:/).closest('.no-print')).toBeNull()

    const baselineHeading = screen.getByRole('heading', { name: 'Baseline' })
    expect(baselineHeading.closest('.no-print')).toBeNull()

    const dailyScoresHeading = screen.getByRole('heading', { name: 'Daily scores' })
    expect(dailyScoresHeading.closest('.no-print')).toBeNull()

    const feedbackHeading = screen.getByRole('heading', { name: 'What nurses said' })
    expect(feedbackHeading.closest('.no-print')).toBeNull()
  })

  it('keeps the drift card printable for a trending resident', async () => {
    offline()
    render(<ResidentDetail residentId="mr-chen" onBack={() => {}} />)

    const driftCard = await screen.findByRole('region', { name: 'Slow drift' })
    expect(driftCard.closest('.no-print')).toBeNull()
  })
})

/** jsdom doesn't evaluate @media conditions for getComputedStyle, so this checks the
 * stylesheet text directly, following alert.css's print test (T289). */
describe('residentPrint.css print layout', () => {
  it('hides every no-print element when printing', () => {
    const printBlock = residentPrintCss.match(/@media print \{([\s\S]*)\}\s*$/)?.[1]
    expect(printBlock).toBeTruthy()

    expect(printBlock).toMatch(/\.no-print\s*\{[^}]*display:\s*none/)
  })

  it('forces black text on a white background regardless of the dark theme', () => {
    const printBlock = residentPrintCss.match(/@media print \{([\s\S]*)\}\s*$/)?.[1]

    expect(printBlock).toMatch(/body \*\s*\{[^}]*background:\s*#fff/)
    expect(printBlock).toMatch(/body \*\s*\{[^}]*color:\s*#000/)
  })

  it('hides the app shell header and demo banner while a resident is open', () => {
    const printBlock = residentPrintCss.match(/@media print \{([\s\S]*)\}\s*$/)?.[1]

    expect(printBlock).toMatch(/\.app:has\(\.resident-detail\) > header\s*,/)
    expect(printBlock).toMatch(/\.app:has\(\.resident-detail\) > \.demo-banner\s*\{[^}]*display:\s*none/)
  })
})
