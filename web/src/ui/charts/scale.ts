/** Dependency-free scales. Times are UTC epoch milliseconds (or Date objects). */
export type Domain = readonly [number, number]

export function linearScale(domain: Domain, range: Domain) {
  const [start, end] = domain
  return (value: number) => start === end
    ? (range[0] + range[1]) / 2
    : range[0] + ((value - start) / (end - start)) * (range[1] - range[0])
}

export function timeScale(domain: readonly [number | Date, number | Date], range: Domain) {
  const scale = linearScale([+domain[0], +domain[1]], range)
  return (value: number | Date) => scale(+value)
}

/** Approximately count readable ticks, including reversed and constant domains. */
export function niceTicks([start, end]: Domain, count = 4): number[] {
  if (!Number.isFinite(start) || !Number.isFinite(end) || count < 2) return []
  if (start === end) return [start]
  if (start > end) return niceTicks([end, start], count).reverse()
  const raw = (end - start) / (count - 1)
  const power = 10 ** Math.floor(Math.log10(raw))
  const fraction = raw / power
  const step = (fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 5 ? 5 : 10) * power
  const first = Math.ceil(start / step)
  const last = Math.floor(end / step)
  return Array.from({ length: Math.max(0, last - first + 1) }, (_, i) =>
    Number(((first + i) * step).toPrecision(12)))
}

/** UTC-aligned time ticks; fixed durations avoid local daylight-saving shifts. */
export function timeTicks(domain: Domain, count = 4): number[] {
  const [start, end] = domain
  if (!Number.isFinite(start) || !Number.isFinite(end) || count < 2) return []
  if (start === end) return [start]
  if (start > end) return timeTicks([end, start], count).reverse()
  const intervals = [1000, 5000, 15000, 60000, 300000, 900000, 3600000,
    10800000, 21600000, 43200000, 86400000, 172800000, 604800000,
    1209600000, 2592000000, 7776000000, 31536000000]
  const raw = (end - start) / (count - 1)
  const step = intervals.find((interval) => interval >= raw) ?? (niceTicks([0, end - start], count)[1] || end - start)
  const first = Math.ceil(start / step)
  return Array.from({ length: Math.max(0, Math.floor(end / step) - first + 1) },
    (_, i) => (first + i) * step)
}
