import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { LiveMessage } from './useLiveSession.ts'
import { mockLiveStream } from './mockLiveStream.ts'

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('mockLiveStream', () => {
  it('emits messages in order, ending with session_end', () => {
    const messages: LiveMessage['type'][] = []
    mockLiveStream(1, (message) => messages.push(message.type))

    vi.runAllTimers()

    expect(messages[0]).toBe('session_start')
    expect(messages[messages.length - 1]).toBe('session_end')
    expect(messages.length).toBeGreaterThan(2)
  })

  it('stops emitting further messages once stopped', () => {
    const messages: LiveMessage['type'][] = []
    const stop = mockLiveStream(1, (message) => messages.push(message.type))

    vi.advanceTimersByTime(250)
    stop()
    const countAtStop = messages.length

    vi.runAllTimers()

    expect(messages.length).toBe(countAtStop)
    expect(messages).not.toContain('session_end')
  })
})
