import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
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
})
