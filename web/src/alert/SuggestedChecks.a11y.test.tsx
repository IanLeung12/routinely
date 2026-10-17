import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { SuggestedChecks } from './SuggestedChecks.tsx'

afterEach(cleanup)

describe('SuggestedChecks accessibility', () => {
  it('lists every suggested check, with the check text as the item content', () => {
    render(<SuggestedChecks checks={['hydration', 'cam_screen']} />)

    const list = screen.getByRole('list')
    const items = within(list).getAllByRole('listitem')
    expect(items.map((item) => item.textContent)).toEqual([
      'Check hydration',
      'Run a CAM delirium screen',
    ])
  })
})
