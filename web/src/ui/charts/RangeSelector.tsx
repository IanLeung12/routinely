import { SegmentedControl } from '../SegmentedControl'

export type ChartRange = '7D' | '14D' | '30D'
const options = (['7D', '14D', '30D'] as const).map((value) => ({ value, label: value }))

/** Controlled range picker; the caller filters its data when the range changes. */
export function RangeSelector({ value, onChange, label = 'Chart time range' }: {
  value: ChartRange
  onChange: (value: ChartRange) => void
  label?: string
}) {
  return <SegmentedControl label={label} options={options} value={value} onChange={onChange} />
}
