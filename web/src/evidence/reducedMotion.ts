/** Whether the OS has asked for reduced motion, so replays can skip autoplay (SPEC
 * section 9 accessibility). Safe when `matchMedia` isn't available, e.g. older jsdom
 * environments or browsers without the API. */
export function prefersReducedMotion(): boolean {
  return typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export default prefersReducedMotion
