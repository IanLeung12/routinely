import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { PrivacyPanel } from './PrivacyPanel.tsx'

afterEach(cleanup)

describe('PrivacyPanel at phone width', () => {
  it('renders with its existing class names at 375px', () => {
    window.innerWidth = 375
    render(<PrivacyPanel />)
    const region = screen.getByRole('region')
    expect(region.classList.contains('privacy-panel')).toBe(true)
    expect(screen.getByRole('list').classList.contains('privacy-panel__list')).toBe(true)
  })
})
