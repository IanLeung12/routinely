import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { loadOverviewPrefs, saveOverviewPrefs } from './overviewPrefs.ts'

const STORAGE_KEY = 'rw.overview.prefs'

beforeEach(() => {
  sessionStorage.clear()
})

afterEach(() => {
  sessionStorage.clear()
  vi.restoreAllMocks()
})

describe('overviewPrefs', () => {
  it('defaults to all/default when nothing is stored', () => {
    expect(loadOverviewPrefs()).toEqual({ filter: 'all', sort: 'default' })
  })

  it('round trips a saved choice', () => {
    saveOverviewPrefs({ filter: 'flagged', sort: 'recent' })

    expect(loadOverviewPrefs()).toEqual({ filter: 'flagged', sort: 'recent' })
  })

  it('falls back to defaults on corrupt JSON', () => {
    sessionStorage.setItem(STORAGE_KEY, '{not json')

    expect(loadOverviewPrefs()).toEqual({ filter: 'all', sort: 'default' })
  })

  it('falls back to defaults on an unknown filter value', () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ filter: 'urgent', sort: 'recent' }))

    expect(loadOverviewPrefs()).toEqual({ filter: 'all', sort: 'default' })
  })

  it('falls back to defaults on an unknown sort value', () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ filter: 'watch', sort: 'oldest' }))

    expect(loadOverviewPrefs()).toEqual({ filter: 'all', sort: 'default' })
  })

  it('falls back to defaults when the stored value is not an object', () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify('flagged'))

    expect(loadOverviewPrefs()).toEqual({ filter: 'all', sort: 'default' })
  })

  it('falls back to defaults when sessionStorage.getItem throws', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })

    expect(loadOverviewPrefs()).toEqual({ filter: 'all', sort: 'default' })
  })

  it('does not throw when sessionStorage.setItem throws', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('quota exceeded')
    })

    expect(() => saveOverviewPrefs({ filter: 'paused', sort: 'default' })).not.toThrow()
  })
})
