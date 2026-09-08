import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ProblemPackageBulkImport from '@/components/ProblemPackageBulkImport.vue'

const { call } = vi.hoisted(() => ({ call: vi.fn() }))
vi.mock('frappe-ui', () => ({ call, Button: { props: ['disabled', 'loading'], template: '<button :disabled="disabled"><slot /></button>' } }))
const translate = (value: string) => value
beforeEach(() => {
	vi.stubGlobal('__', translate)
	vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ message: { name: 'BUNDLE' } }) }))
})
afterEach(() => { vi.clearAllMocks(); vi.unstubAllGlobals() })

async function upload(wrapper: any) {
	const input = wrapper.get('input[type=file]')
	Object.defineProperty(input.element, 'files', { value: [new File(['zip'], 'programming-exercises.zip')] })
	await input.trigger('change'); await flushPromises()
}
function responses(method: string, args: any) {
	if (method.endsWith('create_bulk_import')) return { imports: [
		{ name: 'I1', filename: 'p001.zip', options: { language: 'C++', time_limit_seconds: 3, memory_limit_kb: 131072 } },
		{ name: 'I2', filename: 'p002.zip', options: { time_limit_seconds: 2 } },
	] }
	if (method.endsWith('get_import')) return { name: args.import_id, title: args.import_id, status: 'Ready', statements: ['problem_statement/problem.pdf'], warnings: [], errors: [] }
	if (method.endsWith('commit_import')) return { version: args.import_id === 'I1' ? 'V1' : 'V2' }
	if (method.endsWith('publish_version')) return { exercise: args.version_id }
}

describe('bulk problem package import', () => {
	it('uploads privately, restores per-package settings and publishes new exercises', async () => {
		call.mockImplementation(async (method, args) => responses(method, args))
		const wrapper = mount(ProblemPackageBulkImport, { global: { mocks: { __: translate } } })
		await upload(wrapper)
		expect(vi.mocked(fetch).mock.calls[0][1]?.body).toBeInstanceOf(FormData)
		expect((vi.mocked(fetch).mock.calls[0][1]?.body as FormData).get('is_private')).toBe('1')
		await wrapper.get('button').trigger('click'); await flushPromises()
		expect(call).toHaveBeenCalledWith(expect.stringContaining('commit_import'), { import_id: 'I1', options: {
			language: 'C++', statement_path: 'problem_statement/problem.pdf', time_limit_seconds: 3, memory_limit_kb: 131072,
		} })
		expect(wrapper.emitted('published')).toHaveLength(2)
		expect(wrapper.text()).toContain('2 / 2')
		wrapper.unmount()
	})
	it('retains a failed draft and retries only the failed publication', async () => {
		let failed = true
		call.mockImplementation(async (method, args) => {
			if (method.endsWith('publish_version') && args.version_id === 'V2' && failed) throw new Error('Judge unavailable')
			return responses(method, args)
		})
		const wrapper = mount(ProblemPackageBulkImport, { global: { mocks: { __: translate } } })
		await upload(wrapper)
		await wrapper.get('button').trigger('click'); await flushPromises()
		expect(wrapper.text()).toContain('Judge unavailable')
		expect(wrapper.text()).toContain('1 / 2')
		failed = false
		await wrapper.get('button').trigger('click'); await flushPromises()
		expect(call.mock.calls.filter(([method]) => method.endsWith('commit_import'))).toHaveLength(2)
		expect(call.mock.calls.filter(([method, args]) => method.endsWith('publish_version') && args.version_id === 'V1')).toHaveLength(1)
		expect(wrapper.emitted('published')).toHaveLength(2)
		wrapper.unmount()
	})
	it('does not import rejected packages', async () => {
		call.mockImplementation(async (method, args) => method.endsWith('get_import') ? { status: 'Rejected', errors: ['Missing input validator'] } : responses(method, args))
		const wrapper = mount(ProblemPackageBulkImport, { global: { mocks: { __: translate } } })
		await upload(wrapper)
		expect(wrapper.text()).toContain('Missing input validator')
		expect(wrapper.get('button').attributes('disabled')).toBeDefined()
		expect(call.mock.calls.some(([method]) => method.endsWith('publish_version'))).toBe(false)
		wrapper.unmount()
	})
})
