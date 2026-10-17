import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Button } from './Button.tsx'

afterEach(() => {
  cleanup()
})

describe('Button', () => {
  it('defaults to the secondary variant and type="button"', () => {
    render(<Button>Click</Button>)
    const button = screen.getByRole('button', { name: 'Click' })
    expect(button.className).toContain('btn--secondary')
    expect(button.getAttribute('type')).toBe('button')
  })

  it('applies the requested variant', () => {
    render(<Button variant="danger">False alarm</Button>)
    expect(screen.getByRole('button', { name: 'False alarm' }).className).toContain('btn--danger')
  })

  it('calls onClick when pressed', () => {
    const onClick = vi.fn()
    render(<Button onClick={onClick}>Confirm</Button>)
    screen.getByRole('button', { name: 'Confirm' }).click()
    expect(onClick).toHaveBeenCalledOnce()
  })
})
