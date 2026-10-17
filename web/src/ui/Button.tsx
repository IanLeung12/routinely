import type { ButtonHTMLAttributes } from 'react'

export type ButtonVariant = 'primary' | 'secondary' | 'danger'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
}

/** The three button looks used across screens: primary for the main action,
 * secondary for everything else, danger for destructive or false-alarm actions. */
export function Button({ variant = 'secondary', className, type = 'button', ...props }: ButtonProps) {
  const classes = ['btn', `btn--${variant}`, className].filter(Boolean).join(' ')
  return <button type={type} className={classes} {...props} />
}

export default Button
