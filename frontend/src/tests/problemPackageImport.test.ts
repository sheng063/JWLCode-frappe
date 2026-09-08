import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ProblemPackageImport from '@/components/ProblemPackageImport.vue'

const { call } = vi.hoisted(() => ({ call: vi.fn() }))
vi.mock('frappe-ui', () => ({ call }))
vi.stubGlobal('__', (value: string) => value)
afterEach(() => { vi.clearAllMocks(); vi.unstubAllGlobals() })

describe('problem package import', () => {
	it('uses a private upload, shows preflight and preserves the draft when publication is blocked', async () => {
		vi.stubGlobal('__', (value: string) => value)
		const upload = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ message: { name: 'FILE1' } }) })
		vi.stubGlobal('fetch', upload)
		call.mockImplementation(async (method: string) => {
			if (method.endsWith('create_import')) return { name: 'IMPORT1' }
			if (method.endsWith('get_import')) return { name: 'IMPORT1', status: 'Ready', title: 'Example', statements: ['problem_statement/problem.pdf'], samples: [], hidden_count: 1, warnings: ['Programs not executed'], errors: [] }
			if (method.endsWith('commit_import')) return { version: 'V1' }
			throw new Error('Judge Service capability missing')
		})
		const wrapper = mount(ProblemPackageImport, { global: { mocks: { __: (value: string) => value } }, props: { exercise: 'EX1', activeVersion: 'V0' } })
		const input = wrapper.get('input[type=file]')
		Object.defineProperty(input.element, 'files', { value: [new File(['zip'], 'example.zip')] })
		await input.trigger('change'); await flushPromises()
		expect(upload.mock.calls[0][1].body.get('is_private')).toBe('1')
		expect(wrapper.text()).toContain('Programs not executed')
		await wrapper.get('input[type=number]').setValue('3')
		await wrapper.get('button').trigger('click'); await flushPromises()
		expect(call).toHaveBeenCalledWith(expect.stringContaining('commit_import'), expect.objectContaining({ expected_target_version: 'V0' }))
		await wrapper.get('button').trigger('click'); await flushPromises()
		expect(wrapper.get('[role=alert]').text()).toContain('capability missing')
		expect(wrapper.emitted('published')).toBeUndefined()
		expect(wrapper.text()).toContain('Draft saved; import pending')
		expect(call.mock.calls.filter(([method]) => method.endsWith('commit_import'))).toHaveLength(1)
		wrapper.unmount()
	})

	it('does not offer confirmation for rejected packages', async () => {
		vi.stubGlobal('__', (value: string) => value)
		vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ message: { name: 'FILE1' } }) }))
		call.mockImplementation(async (method: string) => method.endsWith('create_import') ? { name: 'IMPORT1' } : { status: 'Rejected', errors: ['Unsupported format'], warnings: [], samples: [] })
		const wrapper = mount(ProblemPackageImport, { global: { mocks: { __: (value: string) => value } } })
		const input = wrapper.get('input[type=file]')
		Object.defineProperty(input.element, 'files', { value: [new File(['zip'], 'example.zip')] })
		await input.trigger('change'); await flushPromises()
		expect(wrapper.text()).toContain('Unsupported format')
		expect(wrapper.find('button').exists()).toBe(false)
		wrapper.unmount()
	})
	it('imports in one action and shows the permanent number only after publication succeeds', async () => {
		vi.stubGlobal('__', (value: string) => value)
		vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ message: { name: 'FILE1' } }) }))
		call.mockImplementation(async (method: string) => {
			if (method.endsWith('create_import')) return { name: 'IMPORT1' }
			if (method.endsWith('get_import')) return { name: 'IMPORT1', status: 'Ready', statements: ['problem_statement/problem.pdf'], samples: [], memory_mib: 1024 }
			if (method.endsWith('commit_import')) return { version: 'V1' }
			return { exercise: 'EX1', exercise_number: 'P-000123' }
		})
		const wrapper = mount(ProblemPackageImport, { global: { mocks: { __: (v: string) => v } } })
		const input = wrapper.get('input[type=file]')
		Object.defineProperty(input.element, 'files', { value: [new File(['zip'], 'example.zip')] })
		await input.trigger('change'); await flushPromises()
		await wrapper.get('button').trigger('click'); await flushPromises()
		expect(wrapper.emitted('published')).toEqual([['EX1', 'P-000123']])
		expect(wrapper.text()).toContain('P-000123')
		expect(wrapper.find('button').exists()).toBe(false)
		expect(call).toHaveBeenCalledWith(expect.stringContaining('commit_import'), expect.objectContaining({ options: expect.objectContaining({ memory_limit_kb: 1048576 }) }))
		wrapper.unmount()
	})

})
