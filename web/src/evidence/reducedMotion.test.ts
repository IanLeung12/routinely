import { afterEach, describe, expect, it } from 'vitest'
import { prefersReducedMotion } from './reducedMotion.ts'

afterEach(() => {
  delete (window as { matchMedia?: typeof window.matchMedia }).matchMedia
})

describe('prefersReducedMotion', () => {
  it('is false when the OS has not asked for reduced motion', () => {
    window.matchMedia = (() => ({ matches: false })) as unknown as typeof window.matchMedia
    expect(prefersReducedMotion()).toBe(false)
  })

  it('is true when the OS asks for reduced motion', () => {
    window.matchMedia = (() => ({ matches: true })) as unknown as typeof window.matchMedia
    expect(prefersReducedMotion()).toBe(true)
  })

  it('is false when matchMedia is not available', () => {
    delete (window as { matchMedia?: typeof window.matchMedia }).matchMedia
    expect(prefersReducedMotion()).toBe(false)
  })
})
