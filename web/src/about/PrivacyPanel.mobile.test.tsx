import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { PrivacyPanel } from './PrivacyPanel.tsx'

afterEach(cleanup)

describe('PrivacyPanel at phone width', () => {
  it('wraps list text inside the phone media query', async () => {
    const fs = await vi.importActual<{
      readFileSync: (path: string, encoding: 'utf8') => string
    }>('node:fs')
    const css = fs.readFileSync('src/about/privacyPanel.css', 'utf8')
    const phoneStyles = css.match(
      /@media\s*\(max-width:\s*30rem\)\s*\{([\s\S]*?)\n\}/,
    )?.[1]

    expect(phoneStyles).toBeDefined()
    expect(phoneStyles).toMatch(/\.privacy-panel__list\s*\{[^}]*overflow-wrap:\s*anywhere/)
  })

  it('renders the panel and list with their responsive class names', () => {
    render(<PrivacyPanel />)
    const region = screen.getByRole('region')
    expect(region.classList.contains('privacy-panel')).toBe(true)
    expect(screen.getByRole('list').classList.contains('privacy-panel__list')).toBe(true)
  })
})
