import { beforeEach } from 'vitest'
import { installFakeWebSocket } from './live/testWebSocket.ts'

/** Every web test gets a fake WebSocket by default, so none of them open a real
 * socket to localhost:8000 (T368). A test that stubs its own `WebSocket` later in
 * the same `beforeEach` chain overrides this one. */
beforeEach(() => {
  installFakeWebSocket()
})
