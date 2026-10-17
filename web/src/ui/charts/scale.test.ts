import { describe, expect, it } from 'vitest'
import { linearScale, niceTicks, timeScale, timeTicks } from './scale'

describe('chart scales', () => {
  it('maps endpoints, reversed ranges and constant domains', () => {
    const scale = linearScale([10, 20], [100, 0])
    expect([scale(10), scale(15), scale(20)]).toEqual([100, 50, 0])
    expect(linearScale([5, 5], [0, 100])(5)).toBe(50)
  })
  it('uses readable ticks within the domain without floating-point noise', () => {
    expect(niceTicks([1, 9], 5)).toEqual([2, 4, 6, 8])
    expect(niceTicks([-0.3, 0.3], 4)).toEqual([-0.2, 0, 0.2])
    expect(niceTicks([9, 1], 5)).toEqual([8, 6, 4, 2])
    expect(niceTicks([7, 7])).toEqual([7])
    expect(niceTicks([NaN, 10])).toEqual([])
    expect(niceTicks([0, 10], 1)).toEqual([])
  })
  it('maps Dates and epoch times identically', () => {
    const start = Date.UTC(2026, 9, 1)
    const end = start + 86400000
    const scale = timeScale([new Date(start), new Date(end)], [0, 10])
    expect(scale(start)).toBe(0)
    expect(scale(new Date(end))).toBe(10)
    expect(scale(start + 43200000)).toBe(5)
  })
  it('produces sparse UTC-aligned time ticks across a daylight-saving boundary', () => {
    const start = Date.UTC(2026, 9, 31)
    const end = start + 6 * 86400000
    const ticks = timeTicks([start, end], 4)
    expect(ticks.length).toBeGreaterThan(1)
    expect(ticks.length).toBeLessThanOrEqual(4)
    for (const tick of ticks) {
      expect(tick % 86400000).toBe(0)
      expect(tick).toBeGreaterThanOrEqual(start)
      expect(tick).toBeLessThanOrEqual(end)
    }
    expect(timeTicks([end, start], 4)).toEqual([...ticks].reverse())
    expect(timeTicks([start, start])).toEqual([start])
    expect(timeTicks([NaN, end])).toEqual([])
  })
})
