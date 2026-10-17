import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { MOCK_STEPS } from './mockLiveStream.ts'
import TaskMap from './TaskMap.tsx'

afterEach(cleanup)

describe('TaskMap', () => {
  it('renders labels in the supplied order with arrows between steps', () => {
    render(<TaskMap steps={[{ id: 'wash', label: 'Wash hands' }, { id: 'dry', label: 'Dry hands' }]} states={{}} />)

    expect(screen.getAllByRole('listitem').map((step) => step.textContent)).toEqual(['Wash hands', 'Dry hands'])
    expect(screen.getAllByText('→')).toHaveLength(1)
  })

  it.each(['pending', 'done', 'omission', 'repeat', 'sequence'] as const)('maps %s to its class and data attribute', (state) => {
    render(<TaskMap steps={[{ id: 'wash', label: 'Wash hands' }]} states={{ wash: state }} />)

    const step = screen.getByRole('listitem')
    expect(step.className).toBe(`step step--${state}`)
    expect(step.getAttribute('data-state')).toBe(state)
  })

  it('defaults missing states to pending', () => {
    render(<TaskMap steps={[{ id: 'wash', label: 'Wash hands' }]} states={{}} />)

    expect(screen.getByRole('listitem').className).toBe('step step--pending')
    expect(screen.getByRole('listitem').getAttribute('data-state')).toBe('pending')
  })

  it('uses shared styles without injecting a component stylesheet', () => {
    const { container } = render(<TaskMap steps={[{ id: 'wash', label: 'Wash hands' }]} states={{ wash: 'omission' }} />)
    expect(container.querySelector('style')).toBeNull()
    expect(screen.getByRole('list').className).toBe('task-map')
    expect(screen.getByRole('listitem').className).toBe('step step--omission')
  })

  it('renders an empty list without arrows for no steps', () => {
    render(<TaskMap steps={[]} states={{}} />)

    expect(screen.queryAllByRole('listitem')).toHaveLength(0)
    expect(screen.queryByText('→')).toBeNull()
  })

  it.each([
    ['pending', 'Wash hands'],
    ['done', 'Wash hands — done'],
    ['omission', 'Wash hands — missed'],
    ['repeat', 'Wash hands — repeated'],
    ['sequence', 'Wash hands — out of order'],
  ] as const)('gives the %s state the accessible name "%s"', (state, name) => {
    render(<TaskMap steps={[{ id: 'wash', label: 'Wash hands' }]} states={{ wash: state }} />)

    expect(screen.getByRole('listitem', { name })).toBeTruthy()
  })

  it('shows a visible icon for every non-pending state, and none for pending', () => {
    render(<TaskMap steps={[{ id: 'wash', label: 'Wash hands' }]} states={{ wash: 'pending' }} />)
    expect(screen.getByRole('listitem').querySelector('[aria-hidden="true"]')).toBeNull()

    cleanup()
    render(<TaskMap steps={[{ id: 'wash', label: 'Wash hands' }]} states={{ wash: 'omission' }} />)
    expect(screen.getByRole('listitem').querySelector('[aria-hidden="true"]')?.textContent).toContain('✕')
  })
})

/** The card the task map sits in is about 400 px wide, so a single row of steps used to
 * scroll sideways and hid the steps that turn red and amber (T120). `taskMap.css` is
 * loaded into jsdom for these tests; see the `css` option in vite.config.ts. */
describe('TaskMap layout', () => {
  it('flows the steps into wrapping rows instead of one scrolling line', () => {
    render(<TaskMap steps={MOCK_STEPS} states={{}} />)

    const map = getComputedStyle(screen.getByRole('list'))
    expect(map.display).toBe('flex')
    expect(map.flexWrap).toBe('wrap')
    expect(map.overflowX).toBe('visible')
  })

  it('lets a long step give way inside the card while the arrows keep their size', () => {
    render(<TaskMap steps={MOCK_STEPS} states={{}} />)

    const step = getComputedStyle(screen.getAllByRole('listitem')[0])
    expect(step.flexShrink).toBe('1')
    expect(step.minWidth).toBe('0px')
    expect(getComputedStyle(screen.getAllByText('→')[0]).flexShrink).toBe('0')
  })

  it('keeps every step of the tea task in the map, flagged ones included', () => {
    render(
      <TaskMap
        steps={MOCK_STEPS}
        states={{ teabag_in_cup: 'omission', pour: 'repeat' }}
      />,
    )

    const steps = screen.getAllByRole('listitem')
    expect(steps).toHaveLength(MOCK_STEPS.length)
    expect(steps.map((step) => step.getAttribute('data-state'))).toContain('omission')
    expect(screen.getByRole('listitem', { name: 'Put the teabag in the cup — missed' }).className)
      .toBe('step step--omission')
    expect(screen.getByRole('listitem', { name: 'Pour the water — repeated' }).className)
      .toBe('step step--repeat')
  })
})
