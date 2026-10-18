import { useLayoutEffect, useRef, useState, type RefObject } from 'react'
import { Pill, type PillTone } from '../ui/Pill.tsx'
import './taskMap.css'

export type StepState = 'pending' | 'done' | 'omission' | 'repeat' | 'sequence'

/** One step as the map draws it. The live socket's `session_start` steps
 * (`useLiveSession.LiveStep`) and the routine builder's draft both fit this shape.
 * `deps` is the step's own `deps:` list from the task YAML - a task is a graph of
 * dependencies, not a fixed order (SPEC section 7) - and it is what the canvas lays
 * out from. */
export type TaskMapStep = { id: string; label: string; deps?: string[]; optional?: boolean }

type TaskMapProps = {
  steps: TaskMapStep[]
  states: Record<string, StepState>
}

/** Icon, accessible status word and pill per state, shared with `TaskMapLegend`, so a
 * step's state never relies on colour alone (SPEC section 9 accessibility rule).
 * `pending` has no icon, suffix or pill: nothing has happened yet, so the node keeps
 * its number and its label says it all. */
export const STEP_STATUS: Record<
  StepState,
  { legend: string; icon: string; accessible: string; pill: { label: string; tone: PillTone } | null }
> = {
  pending: { legend: 'not yet', icon: '', accessible: '', pill: null },
  done: { legend: 'done', icon: '✓', accessible: 'done', pill: { label: 'Done', tone: 'positive' } },
  omission: {
    legend: 'missed step',
    icon: '✕',
    accessible: 'missed',
    pill: { label: 'Missed', tone: 'negative' },
  },
  repeat: {
    legend: 'repeated step',
    icon: '↻',
    accessible: 'repeated',
    pill: { label: 'Repeated', tone: 'watch' },
  },
  sequence: {
    legend: 'out of order',
    icon: '⇄',
    accessible: 'out of order',
    pill: { label: 'Out of order', tone: 'watch' },
  },
}

/* ------------------------------------------------------------------ the canvas' geometry

   All of it in rem, never px: the SVG's user units are rem as well (the edge layer is
   `width: <W>rem` over `viewBox="0 0 W H"`), so a node placed at x = 3 sits at 3rem and
   the curve drawn to its port lands exactly on it - at any root font size, which is how
   the whole graph scales with the reader's text settings instead of being pinned to a
   pixel grid. These are the graph's measurements, not design values; the colours,
   spacing and type inside a node are tokens like everywhere else (docs/DESIGN.md). */

/** One node card: wide enough for a step label on one or two lines. */
const NODE_W = 10
const NODE_H = 4.875
/** Between two steps that may happen in either order, side by side in one level. */
const CROSS_GAP = 0.75
/** Between one level and the next, along the direction the graph flows. Levels need
 * more room left to right, where the curve has to leave one port and reach the next. */
const FLOW_GAP = { row: 2.5, column: 1.25 }
/** Breathing room between the outermost nodes and the edge of the canvas. */
const PAD = 0.75
const PORT_R = 0.2
/** Stands in until the canvas has been measured, and in tests, which have no layout:
 * the ~23 rem column the live session gives the map (SPEC section 9, screen 3). */
const DEFAULT_WIDTH = 23

/** Left to right like Postman Flows when the levels fit, top to bottom when they don't
 * - the same layered graph either way, with parallel steps side by side across the
 * flow. The task map lives in a ~23 rem column beside the skeleton view, so a nine-step
 * routine four levels deep only fits across a full-width card. */
type Flow = 'row' | 'column'

type PlacedNode = { step: TaskMapStep; index: number; level: number; x: number; y: number }

type Graph = {
  nodes: PlacedNode[]
  /** `deps[i]` holds the indices of the steps step `i` waits on. */
  deps: number[][]
  flow: Flow
  width: number
  height: number
}

/** Each step's dependencies as indices into `steps`, with anything the graph doesn't
 * contain (an unknown id, a step depending on itself) dropped.
 *
 * A set of steps with no `deps` at all - a routine drafted as a plain list, or an API
 * too old to send them - is read as a chain: the order the steps arrived in is then
 * the only ordering anyone has told us about, so the map shows it rather than claiming
 * nine steps may happen in any order. */
function dependencies(steps: TaskMapStep[]): number[][] {
  const index = new Map(steps.map((step, i) => [step.id, i]))
  const declared = steps.map((step, i) =>
    (step.deps ?? [])
      .map((id) => index.get(id))
      .filter((dep): dep is number => dep !== undefined && dep !== i),
  )
  if (declared.some((deps) => deps.length > 0)) return declared
  return steps.map((_, i) => (i === 0 ? [] : [i - 1]))
}

/** The level each step sits at: one past the last of the steps it waits on, so steps
 * that wait on nothing share level 0 and parallel branches share a level all the way
 * down. One pass can only push a node past its own dependencies, so a dependency graph
 * settles in at most one pass per step - which is also what stops a `deps:` list that
 * somehow came back cyclic from looping here. */
function levelsOf(deps: number[][]): number[] {
  const levels = deps.map(() => 0)
  for (let pass = 0; pass < deps.length; pass += 1) {
    let moved = false
    deps.forEach((waitsOn, i) => {
      const level = waitsOn.reduce((furthest, dep) => Math.max(furthest, levels[dep] + 1), 0)
      if (level > levels[i]) {
        levels[i] = level
        moved = true
      }
    })
    if (!moved) break
  }
  return levels
}

/** Where every node goes on a canvas `widthRem` wide, and how big that canvas has to
 * be. Levels run left to right while they fit and top to bottom when they don't; a
 * level with more steps than fit across the canvas wraps onto a second row of its own
 * rather than running off the side. */
function layoutGraph(steps: TaskMapStep[], widthRem: number): Graph {
  const deps = dependencies(steps)
  const levels = levelsOf(deps)
  const levelCount = steps.length === 0 ? 0 : Math.max(...levels) + 1
  const members: number[][] = Array.from({ length: levelCount }, () => [])
  levels.forEach((level, i) => members[level].push(i))

  const spread = levelCount * NODE_W + Math.max(0, levelCount - 1) * FLOW_GAP.row + 2 * PAD
  const flow: Flow = spread <= widthRem ? 'row' : 'column'
  const nodes: PlacedNode[] = []
  const place = (i: number, x: number, y: number) =>
    nodes.push({ step: steps[i], index: i, level: levels[i], x, y })

  if (flow === 'row') {
    const tallest = Math.max(1, ...members.map((member) => member.length))
    const height = tallest * NODE_H + (tallest - 1) * CROSS_GAP
    members.forEach((member, level) => {
      const span = member.length * NODE_H + (member.length - 1) * CROSS_GAP
      const top = PAD + (height - span) / 2
      member.forEach((i, slot) => {
        place(i, PAD + level * (NODE_W + FLOW_GAP.row), top + slot * (NODE_H + CROSS_GAP))
      })
    })
    nodes.sort((a, b) => a.index - b.index)
    return { nodes, deps, flow, width: spread, height: height + 2 * PAD }
  }

  const usable = Math.max(widthRem - 2 * PAD, NODE_W)
  const across = Math.max(1, Math.floor((usable + CROSS_GAP) / (NODE_W + CROSS_GAP)))
  let y = PAD
  members.forEach((member) => {
    for (let start = 0; start < member.length; start += across) {
      const row = member.slice(start, start + across)
      const span = row.length * NODE_W + (row.length - 1) * CROSS_GAP
      const left = PAD + Math.max(0, (usable - span) / 2)
      row.forEach((i, slot) => place(i, left + slot * (NODE_W + CROSS_GAP), y))
      const lastRow = start + across >= member.length
      y += NODE_H + (lastRow ? FLOW_GAP.column : CROSS_GAP)
    }
  })
  nodes.sort((a, b) => a.index - b.index)
  const height = nodes.length === 0 ? 0 : y - FLOW_GAP.column + PAD
  return { nodes, deps, flow, width: Math.max(widthRem, NODE_W + 2 * PAD), height }
}

/** Where an edge leaves a node and where it arrives: out of the far side in the
 * direction the graph flows, into the near side of the step that waits on it. */
function port(node: PlacedNode, side: 'in' | 'out', flow: Flow): { x: number; y: number } {
  if (flow === 'row') {
    return { x: node.x + (side === 'in' ? 0 : NODE_W), y: node.y + NODE_H / 2 }
  }
  return { x: node.x + NODE_W / 2, y: node.y + (side === 'in' ? 0 : NODE_H) }
}

/** One dependency as a smooth cubic curve, flat where it leaves and arrives so the
 * line reads as plugged into the port rather than pointing at it.
 *
 * A curve that reaches past the next level runs in its own step's lane almost the
 * whole way and only swings across at the end (the control points sit at 80/20 rather
 * than halfway). The cards are opaque, so a line straight across the middle would
 * disappear behind the level in between and look like it started there. */
function edgePath(from: PlacedNode, to: PlacedNode, flow: Flow): string {
  const a = port(from, 'out', flow)
  const b = port(to, 'in', flow)
  const span = flow === 'row' ? b.x - a.x : b.y - a.y
  const far = span > FLOW_GAP[flow] * 1.6
  const lead = far ? span * 0.8 : Math.max(span / 2, CROSS_GAP)
  const trail = far ? span * 0.2 : Math.max(span / 2, CROSS_GAP)
  if (flow === 'row') {
    return `M ${r(a.x)} ${r(a.y)} C ${r(a.x + lead)} ${r(a.y)} ${r(b.x - trail)} ${r(b.y)} ${r(b.x)} ${r(b.y)}`
  }
  return `M ${r(a.x)} ${r(a.y)} C ${r(a.x)} ${r(a.y + lead)} ${r(b.x)} ${r(b.y - trail)} ${r(b.x)} ${r(b.y)}`
}

/** Three decimals is well under a device pixel at any sane root font size, and keeps
 * the rendered path data readable. */
function r(value: number): number {
  return Math.round(value * 1000) / 1000
}

function edgeClass(state: StepState, optional: boolean): string {
  const classes = ['task-map__edge', `task-map__edge--${state}`]
  // Dashed, like every other "not required" line in the system (docs/DESIGN.md):
  // skipping an optional step is not a gap in the routine.
  if (optional) classes.push('task-map__edge--optional')
  return classes.join(' ')
}

function stepAccessibleName(step: TaskMapStep, state: StepState, next: boolean): string {
  const parts = [step.label]
  if (step.optional) parts.push('optional')
  const { accessible } = STEP_STATUS[state]
  if (accessible) parts.push(accessible)
  else if (next) parts.push('next up')
  return parts.join(' — ')
}

/** The canvas' own width in rem, remeasured whenever the column it sits in changes
 * size, so the graph can turn from a left-to-right flow into a top-to-bottom one when
 * it has to. 0 until the first measurement, and in jsdom, which has no layout at all. */
function useWidthRem(ref: RefObject<HTMLDivElement | null>): number {
  const [width, setWidth] = useState(0)

  useLayoutEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    const measure = () => {
      const root = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16
      // Rounded, so a sub-pixel reflow can never ping-pong between two layouts.
      setWidth(Math.round((canvas.getBoundingClientRect().width / root) * 100) / 100)
    }
    measure()
    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', measure)
      return () => window.removeEventListener('resize', measure)
    }
    const observer = new ResizeObserver(measure)
    observer.observe(canvas)
    return () => observer.disconnect()
  }, [ref])

  return width
}

/** Screen 3's task graph (SPEC section 9) as a flow canvas: the steps as node cards on
 * a dotted board, joined by curved edges that run from one step's port into the port of
 * every step waiting on it. Steps that wait on nothing but each other share a level and
 * sit side by side, which is the point - "fill the kettle" and "get a cup" may happen in
 * either order, and a map drawn as a numbered list can only ever claim otherwise.
 *
 * Live state rides on the node: done goes green with a tick, a missed step red, a
 * repeated or out-of-order one amber, and the step whose dependencies have all landed
 * glows as the one that comes next. Edges into a flagged step take its colour, so the
 * map going red and amber mid-session (SPEC section 10, demo beat 3) reads from across
 * a room. Every one of those also says its word in the node and in the node's
 * accessible name, so none of it is carried by colour alone. */
export function TaskMap({ steps, states }: TaskMapProps) {
  const canvas = useRef<HTMLDivElement>(null)
  const widthRem = useWidthRem(canvas)
  const graph = layoutGraph(steps, widthRem > 0 ? widthRem : DEFAULT_WIDTH)

  const stateOf = (step: TaskMapStep): StepState => states[step.id] ?? 'pending'
  const done = steps.filter((step) => stateOf(step) === 'done').length
  const percent = steps.length > 0 ? Math.round((done / steps.length) * 100) : 0

  /** The steps something else waits on, so only those get an outgoing port. */
  const feedsInto = new Set(graph.deps.flat())

  /** The steps that could be done now: still pending, with everything they wait on
   * already done. Only once the session is under way - before the first step lands
   * nothing is "next", it has simply not started. */
  const ready = new Set(
    done === 0
      ? []
      : graph.nodes
          .filter(
            (node) =>
              stateOf(node.step) === 'pending' &&
              graph.deps[node.index].every((dep) => stateOf(steps[dep]) === 'done'),
          )
          .map((node) => node.step.id),
  )

  return (
    <>
      {steps.length > 0 && (
        <div className="task-map__progress">
          <p className="task-map__progress-label">
            <span className="task-map__progress-count tabular-nums">
              {done} of {steps.length}
            </span>{' '}
            steps done
          </p>
          {/* A slim track rather than a number alone: how far through the routine
              someone is reads off the fill before anyone reads the count. */}
          <div
            className="task-map__track"
            role="progressbar"
            aria-label="Steps done"
            aria-valuemin={0}
            aria-valuemax={steps.length}
            aria-valuenow={done}
            aria-valuetext={`${done} of ${steps.length} steps done`}
          >
            <span className="task-map__track-fill" style={{ width: `${percent}%` }} />
          </div>
        </div>
      )}

      <div
        ref={canvas}
        className={`task-map task-map--${graph.flow}`}
        role="list"
        aria-label="Task steps"
        style={{ height: `${r(graph.height)}rem` }}
      >
        {/* The wiring, behind the cards. Hidden from screen readers: a dependency is
            already in the reading order and in each node's accessible name. */}
        <svg
          className="task-map__edges"
          aria-hidden="true"
          focusable="false"
          viewBox={`0 0 ${r(graph.width)} ${r(graph.height)}`}
          style={{ width: `${r(graph.width)}rem`, height: `${r(graph.height)}rem` }}
        >
          {graph.nodes.flatMap((node) =>
            graph.deps[node.index].map((dep) => (
              /* The edge takes the state of the step it arrives at, so a missed or
                 repeated step pulls its whole dependency in with it. */
              <path
                key={`${steps[dep].id}→${node.step.id}`}
                className={edgeClass(stateOf(node.step), node.step.optional === true)}
                d={edgePath(graph.nodes[dep], node, graph.flow)}
                fill="none"
              />
            )),
          )}
          {graph.nodes.flatMap((node) => {
            const state = stateOf(node.step)
            const sides: ('in' | 'out')[] = []
            if (graph.deps[node.index].length > 0) sides.push('in')
            if (feedsInto.has(node.index)) sides.push('out')
            return sides.map((side) => {
              const { x, y } = port(node, side, graph.flow)
              return (
                <circle
                  key={`${node.step.id}-${side}`}
                  className={`task-map__port task-map__port--${state}`}
                  cx={r(x)}
                  cy={r(y)}
                  r={PORT_R}
                />
              )
            })
          })}
        </svg>

        {graph.nodes.map((node) => {
          const { step, index } = node
          const state = stateOf(step)
          const { icon, pill } = STEP_STATUS[state]
          const next = ready.has(step.id)
          const classes = [
            'task-map__node',
            `task-map__node--${state}`,
            next ? 'task-map__node--next' : '',
            step.optional ? 'task-map__node--optional' : '',
          ]
            .filter(Boolean)
            .join(' ')
          return (
            <div
              role="listitem"
              key={step.id}
              className={classes}
              data-state={state}
              data-level={node.level}
              aria-label={stepAccessibleName(step, state, next)}
              style={{
                left: `${r(node.x)}rem`,
                top: `${r(node.y)}rem`,
                width: `${NODE_W}rem`,
                height: `${NODE_H}rem`,
              }}
            >
              <span className="task-map__head">
                <span className={`task-map__dot task-map__dot--${state}`} aria-hidden="true">
                  {icon || index + 1}
                </span>
                {pill && (
                  <Pill className="task-map__pill" tone={pill.tone}>
                    {pill.label}
                  </Pill>
                )}
                {/* A pending step can't also carry a state pill, so the two never
                    crowd each other. */}
                {!pill && next && <span className="task-map__tag task-map__tag--next">Next</span>}
                {step.optional && <span className="task-map__tag">Optional</span>}
              </span>
              <span className="task-map__label" title={step.label}>
                {step.label}
              </span>
            </div>
          )
        })}
      </div>
    </>
  )
}

export default TaskMap
