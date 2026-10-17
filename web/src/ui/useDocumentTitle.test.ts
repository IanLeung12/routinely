import { renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { useDocumentTitle } from './useDocumentTitle.ts'

describe('useDocumentTitle', () => {
  it('sets document.title', () => {
    renderHook(() => useDocumentTitle('Unit overview — Routine Watch'))

    expect(document.title).toBe('Unit overview — Routine Watch')
  })

  it('updates the title when it changes', () => {
    const { rerender } = renderHook(({ title }) => useDocumentTitle(title), {
      initialProps: { title: 'Unit overview — Routine Watch' },
    })

    rerender({ title: 'Mrs. K — Routine Watch' })

    expect(document.title).toBe('Mrs. K — Routine Watch')
  })

  it('restores the previous title on unmount', () => {
    document.title = 'Routine Watch'

    const { unmount } = renderHook(() => useDocumentTitle('Mrs. K — Routine Watch'))
    expect(document.title).toBe('Mrs. K — Routine Watch')

    unmount()

    expect(document.title).toBe('Routine Watch')
  })
})
