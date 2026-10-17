import { apiUrl } from '../config.ts'
import { mockPatterns } from './mockPatterns.ts'
import type { PatternLibraryEntry } from './types.ts'

/** The pattern library (`GET /patterns`, SPEC §7.5). Falls back to the mock library
 * so the screen still works offline. */
export async function fetchPatterns(): Promise<PatternLibraryEntry[]> {
  try {
    const response = await fetch(`${apiUrl}/patterns`)
    if (response.ok) return await response.json() as PatternLibraryEntry[]
  } catch { /* Keep the screen usable while offline. */ }
  return mockPatterns
}
