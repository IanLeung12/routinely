import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MOCK_STEPS } from './mockLiveStream.ts'
import TaskMap, { type TaskMapStep } from './TaskMap.tsx'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

/** `take_meds` (`pipeline/src/routine_watch/tasks/meds.yaml`): two branches that do not
 * wait on each other, meeting at the step that matters. */
const MEDS_STEPS: TaskMapStep[] = [
  { id: 'get_glass', label: 'Get a glass' },
  { id: 'fill_glass', label: 'Fill the glass with water', deps: ['get_glass'] },
  { id: 'open_organiser', label: 'Open the pill organiser' },
  { id: 'take_pill', label: 'Take the pill out', deps: ['open_organiser'] },
  { id: 'drink_water', label: 'Drink the water', deps: ['take_pill', 'fill_glass'] },
  { id: 'close_organiser', label: 'Close the organiser', deps: ['take_pill'], optional: true },
]

/** What each node says, without its marker or state word. */
function labels(): (string | null)[] {
  return Array.from(document.querySelectorAll('.task-map__label')).map((el) => el.textContent)
}

function markers(): (string | null)[] {
  return Array.from(document.querySelectorAll('.task-map .task-map__dot')).map((el) => el.textContent)
}

function nodes(): HTMLElement[] {
  return Array.from(document.querySelectorAll('.task-map__node'))
}

function levelOf(label: string): number {
  const node = screen.getAllByRole('listitem').find((item) => item.textContent?.includes(label))
  return Number(node?.getAttribute('data-level'))
}

/** Every node's placed rectangle, in rem, as the layout wrote it onto the card. */
function boxes(): { x: number; y: number; w: number; h: number }[] {
  return nodes().map((node) => ({
    x: parseFloat(node.style.left),
    y: parseFloat(node.style.top),
    w: parseFloat(node.style.width),
    h: parseFloat(node.style.height),
  }))
}

function overlap(a: ReturnType<typeof boxes>[number], b: ReturnType<typeof boxes>[number]): boolean {
  return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h
}

function edges(): SVGPathElement[] {
  return Array.from(document.querySelectorAll('.task-map__edge'))
}

/** jsdom has no layout, so the canvas measures 0 and the map falls back to the ~23 rem
 * column the live session gives it. This widens it to a full-width card instead. */
function widen(widthPx: number) {
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
    width: widthPx,
    height: 400,
    top: 0,
    left: 0,
    right: widthPx,
    bottom: 400,
    x: 0,
    y: 0,
    toJSON: () => ({}),
  } as DOMRect)
}

describe('TaskMap', () => {
  it('renders labels in the task\'s own order, numbered until something happens to them', () => {
    render(<TaskMap steps={[{ id: 'wash', label: 'Wash hands' }, { id: 'dry', label: 'Dry hands' }]} states={{}} />)

    expect(screen.getAllByRole('listitem')).toHaveLength(2)
    expect(labels()).toEqual(['Wash hands', 'Dry hands'])
    // Nothing has happened yet, so each node carries its step's number.
    expect(markers()).toEqual(['1', '2'])
  })

  it.each(['pending', 'done', 'omission', 'repeat', 'sequence'] as const)('maps %s to its class and data attribute', (state) => {
    render(<TaskMap steps={[{ id: 'wash', label: 'Wash hands' }]} states={{ wash: state }} />)

    const step = screen.getByRole('listitem')
    expect(step.className).toBe(`task-map__node task-map__node--${state}`)
    expect(step.getAttribute('data-state')).toBe(state)
  })

  it('defaults missing states to pending', () => {
    render(<TaskMap steps={[{ id: 'wash', label: 'Wash hands' }]} states={{}} />)

    expect(screen.getByRole('listitem').className).toBe('task-map__node task-map__node--pending')
    expect(screen.getByRole('listitem').getAttribute('data-state')).toBe('pending')
  })

  it('uses shared styles without injecting a component stylesheet', () => {
    const { container } = render(<TaskMap steps={[{ id: 'wash', label: 'Wash hands' }]} states={{ wash: 'omission' }} />)
    expect(container.querySelector('style')).toBeNull()
    expect(screen.getByRole('list').className).toContain('task-map')
    expect(screen.getByRole('listitem').className).toBe('task-map__node task-map__node--omission')
  })

  it('renders an empty canvas, and no progress line, for no steps', () => {
    render(<TaskMap steps={[]} states={{}} />)

    expect(screen.queryAllByRole('listitem')).toHaveLength(0)
    expect(edges()).toHaveLength(0)
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
    expect(markers()).toEqual(['1'])
    expect(document.querySelector('.task-map__dot')?.getAttribute('aria-hidden')).toBe('true')

    cleanup()
    render(<TaskMap steps={[{ id: 'wash', label: 'Wash hands' }]} states={{ wash: 'omission' }} />)
    expect(markers()).toEqual(['✕'])
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
    // The pill is the second signal; the node's accessible name already says it.
    expect(screen.getByRole('listitem').textContent).toContain(word)
  })

  it('leaves a step nothing has happened to without a pill', () => {
    render(<TaskMap steps={[{ id: 'wash', label: 'Wash hands' }]} states={{}} />)

    expect(document.querySelector('.task-map__pill')).toBeNull()
  })
})

/** How far through the routine, above the canvas: a count and a slim track, so the
 * progress is read before any of the nodes are. */
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

/** The canvas: steps laid out in levels read off their `deps`, so two steps that may
 * happen in either order sit beside each other rather than one above the other
 * (SPEC section 7). `taskMap.css` is loaded into jsdom for these; see `css` in
 * vite.config.ts. */
describe('TaskMap layout', () => {
  it('puts steps that wait on nothing but each other on the same level', () => {
    render(<TaskMap steps={MOCK_STEPS} states={{}} />)

    // Fill the kettle ∥ get a cup, then boil ∥ teabag in the cup, then pour.
    expect(levelOf('Fill the kettle')).toBe(levelOf('Get a cup'))
    expect(levelOf('Boil the kettle')).toBe(levelOf('Put the teabag in the cup'))
    expect(levelOf('Boil the kettle')).toBe(levelOf('Fill the kettle') + 1)
    expect(levelOf('Pour the water')).toBe(levelOf('Boil the kettle') + 1)
    // Everything that only waits on the pour shares the level after it.
    expect(levelOf('Add milk')).toBe(levelOf('Stir'))
    expect(levelOf('Take the teabag out')).toBe(levelOf('Pour the water') + 1)
  })

  it('places the two branches of the meds task side by side, and the step both feed into after them', () => {
    render(<TaskMap steps={MEDS_STEPS} states={{}} />)

    expect(levelOf('Get a glass')).toBe(levelOf('Open the pill organiser'))
    expect(levelOf('Fill the glass with water')).toBe(levelOf('Take the pill out'))
    expect(levelOf('Drink the water')).toBe(levelOf('Take the pill out') + 1)
    expect(levelOf('Close the organiser')).toBe(levelOf('Drink the water'))
  })

  it.each([
    ['tea', MOCK_STEPS],
    ['meds', MEDS_STEPS],
  ])('lays the %s graph out without overlapping two nodes', (_name, steps) => {
    render(<TaskMap steps={steps} states={{}} />)

    const placed = boxes()
    expect(placed).toHaveLength(steps.length)
    placed.forEach((box, i) => {
      expect(box.x).toBeGreaterThanOrEqual(0)
      expect(box.y).toBeGreaterThanOrEqual(0)
      placed.slice(i + 1).forEach((other) => expect(overlap(box, other)).toBe(false))
    })
  })

  it('draws one edge per dependency, and ports on the nodes they join', () => {
    render(<TaskMap steps={MEDS_STEPS} states={{}} />)

    const wires = MEDS_STEPS.reduce((count, step) => count + (step.deps?.length ?? 0), 0)
    expect(edges()).toHaveLength(wires)
    expect(document.querySelectorAll('.task-map__port').length).toBeGreaterThan(0)
    // The wiring is decoration: the nodes are the list a screen reader walks.
    expect(document.querySelector('.task-map__edges')?.getAttribute('aria-hidden')).toBe('true')
  })

  it('flows left to right once the levels fit, and top to bottom when they do not', () => {
    render(<TaskMap steps={MOCK_STEPS} states={{}} />)
    // The live session's ~23 rem column: four levels of tea can only go downwards.
    expect(screen.getByRole('list').className).toContain('task-map--column')
    const down = boxes()
    expect(down.filter((box) => box.x === down[0].x).length).toBeLessThan(down.length)

    cleanup()
    widen(960)
    render(<TaskMap steps={MOCK_STEPS} states={{}} />)
    expect(screen.getByRole('list').className).toContain('task-map--row')
    const across = boxes()
    // Fill the kettle and get a cup share a column; boil comes after them, to the right.
    expect(across[2].x).toBe(across[0].x)
    expect(across[1].x).toBeGreaterThan(across[0].x)
  })

  it('reads a list of steps with no dependencies as a chain, one level each', () => {
    render(
      <TaskMap
        steps={[{ id: 'a', label: 'Toothbrush' }, { id: 'b', label: 'Toothpaste' }, { id: 'c', label: 'Brush' }]}
        states={{}}
      />,
    )

    expect(levelOf('Toothbrush')).toBe(0)
    expect(levelOf('Toothpaste')).toBe(1)
    expect(levelOf('Brush')).toBe(2)
    expect(edges()).toHaveLength(2)
  })

  it('survives a dependency on a step that is not in the graph', () => {
    render(<TaskMap steps={[{ id: 'a', label: 'Alone', deps: ['nobody'] }, { id: 'b', label: 'After', deps: ['a'] }]} states={{}} />)

    expect(levelOf('Alone')).toBe(0)
    expect(levelOf('After')).toBe(1)
    expect(edges()).toHaveLength(1)
  })
})

/** The live state on the canvas: the step that could happen next, the steps that were
 * flagged, and the edges that run into them. */
describe('TaskMap state', () => {
  it('marks the steps whose dependencies have all landed as next, in words', () => {
    render(<TaskMap steps={MOCK_STEPS} states={{ fill_kettle: 'done' }} />)

    expect(screen.getByRole('listitem', { name: 'Boil the kettle — next up' }).className).toContain(
      'task-map__node--next',
    )
    expect(screen.getAllByText('Next').length).toBeGreaterThan(0)
    // Pour waits on the teabag and the boil, so it is not next yet.
    expect(screen.getByRole('listitem', { name: 'Pour the water' }).className).not.toContain('--next')
  })

  it('calls nothing next before the session has started', () => {
    render(<TaskMap steps={MOCK_STEPS} states={{}} />)

    expect(document.querySelector('.task-map__node--next')).toBeNull()
    expect(screen.queryByText('Next')).toBeNull()
  })

  it('turns the edges into a flagged step red or amber, and leaves the rest alone', () => {
    render(<TaskMap steps={MOCK_STEPS} states={{ teabag_in_cup: 'omission', pour: 'repeat' }} />)

    // teabag_in_cup waits on get_cup; pour waits on boil and the teabag.
    expect(document.querySelectorAll('.task-map__edge--omission')).toHaveLength(1)
    expect(document.querySelectorAll('.task-map__edge--repeat')).toHaveLength(2)
    expect(document.querySelectorAll('.task-map__edge--pending').length).toBeGreaterThan(0)
  })

  it('dashes the optional steps and the edges into them, and says "optional" in their names', () => {
    render(<TaskMap steps={MOCK_STEPS} states={{}} />)

    const milk = screen.getByRole('listitem', { name: 'Add milk — optional' })
    expect(milk.className).toContain('task-map__node--optional')
    expect(getComputedStyle(milk).borderStyle).toBe('dashed')
    // Milk and sugar are the two optional steps of the tea task.
    expect(document.querySelectorAll('.task-map__edge--optional')).toHaveLength(2)
  })

  it('keeps every step of the tea task on the canvas, flagged ones included', () => {
    render(<TaskMap steps={MOCK_STEPS} states={{ teabag_in_cup: 'omission', pour: 'repeat' }} />)

    const steps = screen.getAllByRole('listitem')
    expect(steps).toHaveLength(MOCK_STEPS.length)
    expect(steps.map((step) => step.getAttribute('data-state'))).toContain('omission')
    expect(screen.getByRole('listitem', { name: 'Put the teabag in the cup — missed' }).className)
      .toBe('task-map__node task-map__node--omission')
    expect(screen.getByRole('listitem', { name: 'Pour the water — repeated' }).className)
      .toBe('task-map__node task-map__node--repeat')
  })
})
