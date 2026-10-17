import { SegmentedControl } from '../ui/SegmentedControl.tsx'
import type { RoleId } from './types.ts'
import './people.css'

const OPTIONS: { value: RoleId; label: string }[] = [
  { value: 'person', label: 'Myself' },
  { value: 'supervisor', label: 'Someone I support' },
]

/** The role switch in the shell (SPEC section 17): the demo flips between watching
 * your own routine and supporting someone without clearing anything. */
export function RoleSwitch({
  role,
  onChange,
}: {
  role: RoleId
  onChange: (role: RoleId) => void
}) {
  return (
    <div className="role-switch">
      <p className="role-switch__label" aria-hidden="true">Viewing as</p>
      <SegmentedControl label="Viewing as" options={OPTIONS} value={role} onChange={onChange} />
    </div>
  )
}

export default RoleSwitch
