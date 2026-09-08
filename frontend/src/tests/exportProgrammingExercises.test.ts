import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { exportProgrammingExercises } from '@/utils/exportProgrammingExercises'

describe('programming exercise ZIP download', () => {
	beforeEach(() => {
		vi.stubGlobal('__', (text: string) => text)
		vi.stubGlobal('fetch', vi.fn())
		URL.createObjectURL = vi.fn(() => 'blob:export')
		URL.revokeObjectURL = vi.fn()
		vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
		vi.useFakeTimers()
		;(window as any).csrf_token = 'csrf-test'
	})
	afterEach(() => {
		vi.runAllTimers()
		vi.useRealTimers()
		vi.restoreAllMocks()
		vi.unstubAllGlobals()
	})
	it('posts the selected IDs with CSRF and downloads one ZIP', async () => {
		vi.mocked(fetch).mockResolvedValue(new Response(new Blob(['zip']), {
			headers: { 'Content-Type': 'application/zip' },
		}))
		await exportProgrammingExercises(['EX1', 'EX2'])
		expect(fetch).toHaveBeenCalledWith(expect.any(String), expect.objectContaining({
			method: 'POST',
			body: JSON.stringify({ exercises: ['EX1', 'EX2'] }),
			headers: expect.objectContaining({ 'X-Frappe-CSRF-Token': 'csrf-test' }),
		}))
		expect(HTMLAnchorElement.prototype.click).toHaveBeenCalledOnce()
		expect(document.querySelector('a[download]')).toBeNull()
		vi.runAllTimers()
		expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:export')
	})
	it('displays the actionable Frappe error without downloading', async () => {
		vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({
			_server_messages: JSON.stringify([JSON.stringify({ message: 'Missing accepted solution' })]),
		}), { status: 417 }))
		await expect(exportProgrammingExercises(['EX1'])).rejects.toThrow('Missing accepted solution')
		expect(URL.createObjectURL).not.toHaveBeenCalled()
	})
	it('rejects a login or JSON response masquerading as a successful download', async () => {
		vi.mocked(fetch).mockResolvedValue(new Response('<html>Login</html>'))
		await expect(exportProgrammingExercises(['EX1'])).rejects.toThrow('ZIP')
		expect(HTMLAnchorElement.prototype.click).not.toHaveBeenCalled()
	})
	it('rejects empty and oversized selections before requesting', async () => {
		await expect(exportProgrammingExercises([])).rejects.toThrow('50')
		await expect(exportProgrammingExercises(Array(51).fill('EX1'))).rejects.toThrow('50')
		expect(fetch).not.toHaveBeenCalled()
	})
})
