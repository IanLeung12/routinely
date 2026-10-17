import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { MOCK_STEPS } from './mockLiveStream.ts'
import TaskMap from './TaskMap.tsx'

afterEach(cleanup)

/** What each row says, without the node's number or icon. */
function labels(): (string | null)[] {
  return Array.from(document.querySelectorAll('.step__label')).map((el) => el.textContent)
}

function nodes(): (string | null)[] {
  return Array.from(document.querySelectorAll('.task-map .step__node')).map((el) => el.textContent)
}

describe('TaskMap', () => {
  it('renders labels in the supplied order, numbered down one rail', () => {
    render(<TaskMap steps={[{ id: 'wash', label: 'Wash hands' }, { id: 'dry', label: 'Dry hands' }]} states={{}} />)

    expect(screen.getAllByRole('listitem')).toHaveLength(2)
    expect(labels()).toEqual(['Wash hands', 'Dry hands'])
    // Nothing has happened yet, so each node carries its step's number.
    expect(nodes()).toEqual(['1', '2'])
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

  it('renders an empty list, and no progress line, for no steps', () => {
    render(<TaskMap steps={[]} states={{}} />)

    expect(screen.queryAllByRole('listitem')).toHaveLength(0)
    // Nothing has been sent yet, so there is no "0 of 0" to report.
    expect(screen.queryByRole('progressbar')).toBeNull()
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

  it('swaps the step number for the state icon once something has happened to it', () => {
    render(<TaskMap steps={[{ id: 'wash', label: 'Wash hands' }]} states={{ wash: 'pending' }} />)
    expect(nodes()).toEqual(['1'])
    expect(document.querySelector('.step__node')?.getAttribute('aria-hidden')).toBe('true')

    cleanup()
    render(<TaskMap steps={[{ id: 'wash', label: 'Wash hands' }]} states={{ wash: 'omission' }} />)
    expect(nodes()).toEqual(['✕'])
  })

  it.each([
    ['done', 'Done', 'pill--positive'],
    ['omission', 'Missed', 'pill--negative'],
    ['repeat', 'Repeated', 'pill--watch'],
    ['sequence', 'Out of order', 'pill--watch'],
  ] as const)('says %s in words, in a %s pill', (state, word, tone) => {
    render(<TaskMap steps={[{ id: 'wash', label: 'Wash hands' }]} states={{ wash: state }} />)

    const pill = screen.getByText(word)
    expect(pill.className).toContain(tone)
    // The pill is the second signal; the row's accessible name already says it.
    expect(screen.getByRole('listitem').textContent).toContain(word)
  })

  it('leaves a step nothing has happened to without a pill', () => {
    render(<TaskMap steps={[{ id: 'wash', label: 'Wash hands' }]} states={{}} />)

    expect(document.querySelector('.step__pill')).toBeNull()
  })
})

/** How far through the routine, above the list: a count and a slim track, so the
 * progress is read before any of the rows are. */
describe('TaskMap progress', () => {
  it('counts only the done steps, and reports the same number to a screen reader', () => {
    render(
      <TaskMap
        steps={MOCK_STEPS}
        states={{ fill_kettle: 'done', boil: 'done', teabag_in_cup: 'omission', pour: 'repeat' }}
      />,
    )

    expect(screen.getByText(`2 of ${MOCK_STEPS.length}`)).toBeTruthy()
    const track = screen.getByRole('progressbar', { name: 'Steps done' })
    expect(track.getAttribute('aria-valuenow')).toBe('2')
    expect(track.getAttribute('aria-valuemax')).toBe(String(MOCK_STEPS.length))
    expect(track.getAttribute('aria-valuetext')).toBe(`2 of ${MOCK_STEPS.length} steps done`)
  })

  it('fills the track in step with the count', () => {
    render(<TaskMap steps={[{ id: 'a', label: 'A' }, { id: 'b', label: 'B' }]} states={{ a: 'done' }} />)

    expect((document.querySelector('.task-map__track-fill') as HTMLElement).style.width).toBe('50%')
  })
})

/** The card the task map sits in is about 400 px wide, so the wrapping grid of boxes
 * this replaced hid the steps that turn red and amber (T120, T406). `taskMap.css` is
 * loaded into jsdom for these tests; see the `css` option in vite.config.ts. */
describe('TaskMap layout', () => {
  it('stacks the steps in one column instead of a wrapping grid', () => {
    render(<TaskMap steps={MOCK_STEPS} states={{}} />)

    const map = getComputedStyle(screen.getByRole('list'))
    expect(map.display).toBe('flex')
    expect(map.flexDirection).toBe('column')
    expect(map.overflowX).toBe('visible')
  })

  it('lets a long label give way inside the row while the node keeps its size', () => {
    render(<TaskMap steps={MOCK_STEPS} states={{ fill_kettle: 'done' }} />)

    const label = getComputedStyle(document.querySelector('.step__label') as HTMLElement)
    expect(label.flexGrow).toBe('1')
    expect(label.minWidth).toBe('0px')
    expect(getComputedStyle(document.querySelector('.step__node') as HTMLElement).flexShrink).toBe('0')
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
