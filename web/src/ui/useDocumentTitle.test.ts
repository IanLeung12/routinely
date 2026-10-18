import { renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { useDocumentTitle } from './useDocumentTitle.ts'

describe('useDocumentTitle', () => {
  it('sets document.title', () => {
    renderHook(() => useDocumentTitle('Unit overview — Routinely'))

    expect(document.title).toBe('Unit overview — Routinely')
  })

  it('updates the title when it changes', () => {
    const { rerender } = renderHook(({ title }) => useDocumentTitle(title), {
      initialProps: { title: 'Unit overview — Routinely' },
    })

    rerender({ title: 'Mrs. K — Routinely' })

    expect(document.title).toBe('Mrs. K — Routinely')
  })

  it('restores the previous title on unmount', () => {
    document.title = 'Routinely'

    const { unmount } = renderHook(() => useDocumentTitle('Mrs. K — Routinely'))
    expect(document.title).toBe('Mrs. K — Routinely')

    unmount()

    expect(document.title).toBe('Routinely')
  })
})
