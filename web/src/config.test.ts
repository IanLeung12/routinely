import { expect, it } from 'vitest'
import { apiUrl } from './config.ts'

it('resolves an absolute pipeline API URL', () => {
  expect(apiUrl).toMatch(/^https?:\/\//)
})
