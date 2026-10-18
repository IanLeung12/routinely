import { useState } from 'react'

/** Big-key PIN pad for a shaky hand (SPEC section 18, T451): large targets, no
 * time pressure of its own - the countdown lives in the card around it, not here.
 * Submits as soon as `length` digits are in, so there is nothing else to tap.
 * `error` reads out immediately (`role="alert"`, like `ui/ErrorState.tsx`) and the
 * countdown keeps running underneath it; it never says which PIN was wrong, because
 * from here there is no way to tell a wrong safety PIN from a wrong duress one. */
export function PinPad({
  length = 4,
  onSubmit,
  error,
  disabled = false,
}: {
  length?: number
  onSubmit: (pin: string) => void
  error?: string
  disabled?: boolean
}) {
  const [digits, setDigits] = useState('')

  function press(digit: string) {
    if (disabled) return
    const next = `${digits}${digit}`.slice(0, length)
    setDigits(next)
    if (next.length === length) {
      setDigits('')
      onSubmit(next)
    }
  }

  function backspace() {
    setDigits((current) => current.slice(0, -1))
  }

  return (
    <div className="pin-pad">
      <div className="pin-pad__dots" aria-hidden="true">
        {Array.from({ length }, (_value, index) => (
          <span
            key={index}
            className={['pin-pad__dot', index < digits.length && 'pin-pad__dot--filled']
              .filter(Boolean)
              .join(' ')}
          />
        ))}
      </div>
      <p className="pin-pad__error" role="alert">{error ?? ''}</p>
      <div className="pin-pad__keys" role="group" aria-label="PIN pad">
        {['1', '2', '3', '4', '5', '6', '7', '8', '9'].map((digit) => (
          <button
            key={digit}
            type="button"
            className="pin-pad__key"
            disabled={disabled}
            onClick={() => press(digit)}
          >
            {digit}
          </button>
        ))}
        <span className="pin-pad__key-spacer" aria-hidden="true" />
        <button type="button" className="pin-pad__key" disabled={disabled} onClick={() => press('0')}>
          0
        </button>
        <button
          type="button"
          className="pin-pad__key pin-pad__key--backspace"
          disabled={disabled || digits.length === 0}
          onClick={backspace}
          aria-label="Delete last digit"
        >
          ⌫
        </button>
      </div>
    </div>
  )
}

export default PinPad
