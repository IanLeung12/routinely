import { configure } from '@testing-library/react'
import { beforeEach } from 'vitest'
import { installFakeWebSocket } from './live/testWebSocket.ts'

/** testing-library's findBy/waitFor default (1000ms) assumes a quiet machine. A lazy
 * screen's first import (T449, T451), or just a loaded box, can outrun that before any
 * test logic is slow, so every test gets more room rather than chasing it file by file
 * (T445, T459). */
configure({ asyncUtilTimeout: 5000 })

/** Node 22 defines its own `localStorage` global as undefined unless the process was
 * started with `--localstorage-file`, and that wins over jsdom's, so web tests have no
 * storage at all. Give them an in-memory one with the same semantics, so a screen that
 * remembers something (`people/api.ts`: the chosen role and who is linked) can be
 * tested the way it runs in a browser. */
function installLocalStorage() {
  if (typeof globalThis.localStorage !== 'undefined' && globalThis.localStorage !== null) return

  const entries = new Map<string, string>()
  const storage: Storage = {
    get length() {
      return entries.size
    },
    key: (index: number) => [...entries.keys()][index] ?? null,
    getItem: (key: string) => entries.get(key) ?? null,
    setItem: (key: string, value: string) => {
      entries.set(key, String(value))
    },
    removeItem: (key: string) => {
      entries.delete(key)
    },
    clear: () => {
      entries.clear()
    },
  }
  Object.defineProperty(globalThis, 'localStorage', {
    value: storage,
    configurable: true,
    writable: true,
  })
}

installLocalStorage()

/** Every web test gets a fake WebSocket by default, so none of them open a real
 * socket to localhost:8000 (T368). A test that stubs its own `WebSocket` later in
 * the same `beforeEach` chain overrides this one. */
beforeEach(() => {
  installFakeWebSocket()
})
