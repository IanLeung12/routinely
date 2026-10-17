import type { SortMode } from './ResidentSort.tsx'

export type UnitFilter = 'all' | 'flagged' | 'watch' | 'paused'

export interface OverviewPrefs {
  filter: UnitFilter
  sort: SortMode
}

const STORAGE_KEY = 'rw.overview.prefs'
const DEFAULT_PREFS: OverviewPrefs = { filter: 'all', sort: 'default' }
const VALID_FILTERS: UnitFilter[] = ['all', 'flagged', 'watch', 'paused']
const VALID_SORTS: SortMode[] = ['default', 'recent']

function isOverviewPrefs(value: unknown): value is OverviewPrefs {
  if (!value || typeof value !== 'object') return false
  const candidate = value as Record<string, unknown>
  return (
    VALID_FILTERS.includes(candidate.filter as UnitFilter) &&
    VALID_SORTS.includes(candidate.sort as SortMode)
  )
}

/** Unit overview filter + sort, remembered for the tab (SPEC section 9): a nurse who
 * picks "Flagged" and opens a resident shouldn't lose that choice on the way back.
 * Any missing, corrupt or unrecognised stored value falls back to the defaults. */
export function loadOverviewPrefs(): OverviewPrefs {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULT_PREFS
    const parsed = JSON.parse(raw)
    return isOverviewPrefs(parsed) ? parsed : DEFAULT_PREFS
  } catch {
    return DEFAULT_PREFS
  }
}

export function saveOverviewPrefs(prefs: OverviewPrefs): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(prefs))
  } catch {
    // sessionStorage unavailable (private mode, quota, etc) — the choice just won't persist.
  }
}
