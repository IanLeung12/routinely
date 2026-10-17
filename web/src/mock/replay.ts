import type { CaptureFrame } from '../contracts.ts'

function pose(centerX: number): CaptureFrame['poses'][number] {
  const landmarks = Array.from({ length: 33 }, () => ({ x: centerX, y: 0.5, z: 0 }))
  landmarks[11] = { x: centerX - 0.05, y: 0.3, z: 0 }
  landmarks[12] = { x: centerX + 0.05, y: 0.3, z: 0 }
  landmarks[13] = { x: centerX - 0.08, y: 0.45, z: 0 }
  landmarks[14] = { x: centerX + 0.08, y: 0.45, z: 0 }
  landmarks[15] = { x: centerX - 0.1, y: 0.6, z: 0 }
  landmarks[16] = { x: centerX + 0.1, y: 0.6, z: 0 }
  landmarks[23] = { x: centerX - 0.05, y: 0.6, z: 0 }
  landmarks[24] = { x: centerX + 0.05, y: 0.6, z: 0 }
  return { landmarks }
}

function frame(sessionId: string, seq: number, t: number, centerX: number): CaptureFrame {
  return { session_id: sessionId, seq, t, source: 'synthetic', poses: [pose(centerX)], hands: [], objects: [] }
}

/** Offline fallback for `fetchReplay` (`evidence/api.ts`): a few seconds of skeleton
 * frames around the mocked alert's first error, so the Evidence card on `AlertView`
 * has something to show without the API. Keyed by alert id. */
export const mockReplays: Record<string, { today: CaptureFrame[]; normal: CaptureFrame[] }> = {
  'mrs-k-change-1': {
    today: [10, 11, 12].map((t, i) => frame('mrs-k-tea-1', i, t, 0.52)),
    normal: [10, 11, 12].map((t, i) => frame('mrs-k-normal', i, t, 0.48)),
  },
}
