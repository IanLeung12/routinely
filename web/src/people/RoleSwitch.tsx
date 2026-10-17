import { useId } from 'react'
import { Button } from '../ui/Button.tsx'
import type { RoleId } from './types.ts'
import './people.css'

const OPTIONS: { role: RoleId; label: string }[] = [
  { role: 'person', label: 'Myself' },
  { role: 'supervisor', label: 'Someone I support' },
]

/** The role switch in the shell (SPEC section 17): the demo flips between watching
 * your own routine and supporting someone without clearing anything. Same shape as the
 * live screen's routine picker, so both read as one control. */
export function RoleSwitch({
  role,
  onChange,
}: {
  role: RoleId
  onChange: (role: RoleId) => void
}) {
  const labelId = useId()

  return (
    <div className="role-switch" role="group" aria-labelledby={labelId}>
      <p className="role-switch__label" id={labelId}>Viewing as</p>
      {OPTIONS.map((option) => {
        const active = option.role === role
        return (
          <Button
            key={option.role}
            variant={active ? 'primary' : 'secondary'}
            aria-pressed={active}
            onClick={() => onChange(option.role)}
          >
            {option.label}
          </Button>
        )
      })}
    </div>
  )
}

export default RoleSwitch
