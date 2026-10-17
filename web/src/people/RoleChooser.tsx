import type { RoleId } from './types.ts'
import './people.css'

const HEADING_ID = 'role-chooser-heading'

/** The two roles, in the words someone opening the app would use about themselves
 * (SPEC section 17). Each option says what the screen behind it shows, so nobody has
 * to guess which one they are. */
const CHOICES: { role: RoleId; title: string; detail: string }[] = [
  {
    role: 'person',
    title: "I'm setting this up for myself",
    detail:
      'You see your own routine: what is usual for you, how today went, and a gentle note when something looked different.',
  },
  {
    role: 'supervisor',
    title: "I'm supporting someone",
    detail:
      'You see the people who shared their routine with you: family, someone you care for, or a care-home unit.',
  },
]

/** First screen on a browser that has not picked a role yet (SPEC section 17). The
 * choice is remembered, and the switch at the top of every screen changes it later, so
 * this is one tap and never asked again. */
export function RoleChooser({ onChoose }: { onChoose: (role: RoleId) => void }) {
  return (
    <section className="role-chooser" aria-labelledby={HEADING_ID}>
      <h2 className="role-chooser__heading" id={HEADING_ID}>Who is this for?</h2>
      <p className="role-chooser__lead">
        Pick one to start. You can change it at the top of any screen.
      </p>
      <ul className="role-chooser__options">
        {CHOICES.map((choice) => (
          <li key={choice.role}>
            <button
              type="button"
              className="role-chooser__option"
              onClick={() => onChoose(choice.role)}
            >
              <span className="role-chooser__option-title">{choice.title}</span>
              <span className="role-chooser__option-detail">{choice.detail}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}

export default RoleChooser
