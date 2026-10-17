import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CameraPreview } from './CameraPreview.tsx'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('CameraPreview', () => {
  it('renders only children when the probe resolves false', async () => {
    render(
      <CameraPreview probe={async () => false}>
        <p>skeleton</p>
      </CameraPreview>,
    )

    expect(await screen.findByText('skeleton')).toBeTruthy()
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('hides the toggle on a non-localhost hostname with the default probe, without calling fetch', async () => {
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    vi.stubGlobal('location', { ...window.location, hostname: 'example.com' })

    render(
      <CameraPreview>
        <p>skeleton</p>
      </CameraPreview>,
    )

    expect(await screen.findByText('skeleton')).toBeTruthy()
    expect(screen.queryByRole('button')).toBeNull()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('shows a toggle that reveals the preview image, badge and children, and can hide it again', async () => {
    const user = userEvent.setup()
    const { container } = render(
      <CameraPreview probe={async () => true}>
        <p>skeleton</p>
      </CameraPreview>,
    )

    const toggle = await screen.findByRole('button', { name: 'Show camera preview (this device only)' })
    expect(toggle.getAttribute('aria-pressed')).toBe('false')
    expect(container.querySelector('img')).toBeNull()

    await user.click(toggle)

    expect(toggle.getAttribute('aria-pressed')).toBe('true')
    expect(container.querySelector('img')?.getAttribute('src')).toBe('http://127.0.0.1:8765/preview.mjpg')
    expect(screen.getByText('Preview · not recorded · this device only')).toBeTruthy()
    expect(screen.getByText('skeleton')).toBeTruthy()

    await user.click(toggle)

    expect(toggle.getAttribute('aria-pressed')).toBe('false')
    expect(container.querySelector('img')).toBeNull()
    expect(screen.getByText('skeleton')).toBeTruthy()
  })

  it('is keyboard operable', async () => {
    const user = userEvent.setup()
    const { container } = render(
      <CameraPreview probe={async () => true}>
        <p>skeleton</p>
      </CameraPreview>,
    )

    const toggle = await screen.findByRole('button', { name: 'Show camera preview (this device only)' })
    toggle.focus()
    expect(document.activeElement).toBe(toggle)

    await user.keyboard('{Enter}')
    expect(toggle.getAttribute('aria-pressed')).toBe('true')
    expect(container.querySelector('img')).not.toBeNull()

    await user.keyboard('{Enter}')
    expect(toggle.getAttribute('aria-pressed')).toBe('false')
    expect(container.querySelector('img')).toBeNull()
  })

  it('uses the given port in the preview image URL', async () => {
    const user = userEvent.setup()
    const { container } = render(
      <CameraPreview port={9999} probe={async () => true}>
        <p>skeleton</p>
      </CameraPreview>,
    )

    await user.click(await screen.findByRole('button', { name: 'Show camera preview (this device only)' }))
    expect(container.querySelector('img')?.getAttribute('src')).toBe('http://127.0.0.1:9999/preview.mjpg')
  })
})
