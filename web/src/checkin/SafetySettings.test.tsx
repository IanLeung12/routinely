import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { SafetySettings } from './SafetySettings.tsx'
import * as api from './api.ts'
import type { SafetySettingsData } from './types.ts'

vi.mock('./api.ts', () => ({ fetchSafetySettings: vi.fn(), saveSafetySettings: vi.fn() }))

const settings: SafetySettingsData = {
  person_id: 'mrs-k', name: 'Mrs. K', checkin_window_s: 120, ack_window_s: 120,
  location: 'Room 204, care home', location_simulated: true, safety_pin_set: true, duress_pin_set: true,
  supporters: [
    { id: 'ana', name: 'Ana', relationship: 'nurse', share: { location: false, alert_details: true, replay: false } },
    { id: 'lena', name: 'Lena', relationship: 'family', share: { location: false, alert_details: false, replay: false } },
  ],
}
beforeEach(() => {
  vi.mocked(api.fetchSafetySettings).mockResolvedValue(structuredClone(settings))
  vi.mocked(api.saveSafetySettings).mockImplementation(async (_person, input) => {
    const { safety_pin: _safetyPin, duress_pin: _duressPin, ...changes } = input
    return { ...settings, ...changes }
  })
})
afterEach(() => { cleanup(); vi.clearAllMocks() })

it('edits ordered supporters, permissions and windows, submitting PINs only as password inputs then clearing them', async () => {
  render(<SafetySettings personId="mrs-k" onBack={() => {}} />)
  await screen.findByText('Ana')
  expect((screen.getByLabelText('New safety PIN') as HTMLInputElement).value).toBe('')
  expect(screen.getByLabelText('New safety PIN').getAttribute('type')).toBe('password')
  fireEvent.click(screen.getByRole('button', { name: 'Move Lena up' }))
  const rows = screen.getAllByRole('listitem')
  expect(within(rows[0]).getByText('Lena')).toBeTruthy()
  fireEvent.click(screen.getByLabelText('Simulated location for Lena'))
  fireEvent.change(screen.getByLabelText('Check-in window (seconds)'), { target: { value: '45' } })
  fireEvent.change(screen.getByLabelText('Acknowledgement window (seconds)'), { target: { value: '30' } })
  fireEvent.change(screen.getByLabelText('New safety PIN'), { target: { value: '9876' } })
  fireEvent.change(screen.getByLabelText('New duress PIN'), { target: { value: '6789' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save safety settings' }))
  await screen.findByText('Safety settings saved. PINs are hidden.')
  expect(api.saveSafetySettings).toHaveBeenCalledWith('mrs-k', {
    checkin_window_s: 45, ack_window_s: 30, safety_pin: '9876', duress_pin: '6789',
    supporters: [
      expect.objectContaining({ id: 'lena', share: expect.objectContaining({ location: true }) }),
      expect.objectContaining({ id: 'ana' }),
    ],
  })
  expect((screen.getByLabelText('New safety PIN') as HTMLInputElement).value).toBe('')
  expect((screen.getByLabelText('New duress PIN') as HTMLInputElement).value).toBe('')
  expect(screen.queryByText('9876')).toBeNull()
})

it('leaves existing PINs out of the request if blank and handles no linked supporters', async () => {
  vi.mocked(api.fetchSafetySettings).mockResolvedValue({ ...settings, supporters: [] })
  render(<SafetySettings personId="sam" onBack={() => {}} />)
  expect(await screen.findByText(/No supporters linked/)).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: 'Save safety settings' }))
  await waitFor(() => expect(api.saveSafetySettings).toHaveBeenCalledOnce())
  expect(api.saveSafetySettings).toHaveBeenCalledWith('sam', {
    checkin_window_s: 120, ack_window_s: 120, supporters: [],
  })
})

it('shows a loading failure and allows retry', async () => {
  vi.mocked(api.fetchSafetySettings).mockRejectedValueOnce(new Error('offline'))
  render(<SafetySettings personId="mrs-k" onBack={() => {}} />)
  expect(screen.getByText('Loading safety settings…')).toBeTruthy()
  await screen.findByText('Safety settings could not load. Please retry.')
  fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
  expect(await screen.findByText('Ana')).toBeTruthy()
})

it('rejects identical new PINs and keeps unsaved edits after a server failure', async () => {
  render(<SafetySettings personId="mrs-k" onBack={() => {}} />)
  await screen.findByText('Ana')
  for (const label of ['New safety PIN', 'New duress PIN']) fireEvent.change(screen.getByLabelText(label), { target: { value: '1234' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save safety settings' }))
  expect(await screen.findByText('Choose different safety and duress PINs.')).toBeTruthy()
  expect(api.saveSafetySettings).not.toHaveBeenCalled()
  vi.mocked(api.saveSafetySettings).mockRejectedValueOnce(new Error('permission denied'))
  fireEvent.change(screen.getByLabelText('New duress PIN'), { target: { value: '5678' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save safety settings' }))
  expect(await screen.findByText('Safety settings were not saved. Please try again.')).toBeTruthy()
  expect((screen.getByLabelText('New safety PIN') as HTMLInputElement).value).toBe('1234')
})
