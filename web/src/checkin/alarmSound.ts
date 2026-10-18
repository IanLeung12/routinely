/** One oscillator per pulse, with a short envelope to avoid clicks. No audio asset. */
export function createAlarmSound() {
  let context: AudioContext | null = null
  let interval: ReturnType<typeof setInterval> | null = null
  const playing = new Set<OscillatorNode>()

  function stop() {
    if (interval !== null) clearInterval(interval)
    interval = null
    for (const oscillator of playing) {
      oscillator.onended = null
      oscillator.stop()
      oscillator.disconnect()
    }
    playing.clear()
    const previous = context
    context = null
    if (previous) void previous.close().catch(() => {})
  }

  async function start(): Promise<boolean> {
    if (interval !== null) return true
    stop()
    if (typeof AudioContext === 'undefined') return false
    let current: AudioContext | null = null
    try {
      current = new AudioContext()
      context = current
      await current.resume()
      // A mute/unmount while resume was pending must never start a late tone.
      if (context !== current) return false
      if (current.state !== 'running') { stop(); return false }
      const running = current
      function pulse() {
        const oscillator = running.createOscillator()
        const gain = running.createGain()
        const now = running.currentTime
        oscillator.frequency.value = 740
        gain.gain.setValueAtTime(0, now)
        gain.gain.linearRampToValueAtTime(0.12, now + 0.03)
        gain.gain.setValueAtTime(0.12, now + 0.3)
        gain.gain.linearRampToValueAtTime(0, now + 0.4)
        oscillator.connect(gain)
        gain.connect(running.destination)
        playing.add(oscillator)
        oscillator.onended = () => { playing.delete(oscillator); oscillator.disconnect(); gain.disconnect() }
        oscillator.start(now)
        oscillator.stop(now + 0.4)
      }
      pulse()
      interval = setInterval(pulse, 1500)
      return true
    } catch {
      if (context === current) stop()
      return false
    }
  }

  return { start, stop }
}
