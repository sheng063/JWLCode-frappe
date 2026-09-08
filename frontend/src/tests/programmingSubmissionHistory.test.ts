import { mount, flushPromises } from '@vue/test-utils'
import { reactive } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
const mocks = vi.hoisted(() => ({ resource: null as any, create: vi.fn() }))
vi.mock('frappe-ui', () => ({ createListResource: (options: any) => { mocks.create(options); return mocks.resource } }))
import History from '@/components/ProgrammingSubmissionHistory.vue'

describe('inline submission history', () => {
	beforeEach(() => {
		mocks.resource = reactive({ data: [], loading: false, error: null, hasNextPage: false, update: vi.fn(), reload: vi.fn(), next: vi.fn() })
	})
	it('scopes records to the exercise and member and applies filters', async () => {
		const wrapper = mount(History, { props: { exercise: 'exercise-1', member: 'student@example.com' } })
		expect(mocks.resource.update).toHaveBeenLastCalledWith({ filters: { exercise: 'exercise-1', member: 'student@example.com' } })
		await wrapper.find('[aria-label="筛选提交状态"]').setValue('Passed')
		await wrapper.find('[aria-label="筛选提交语言"]').setValue('C++')
		expect(mocks.resource.update).toHaveBeenLastCalledWith({ filters: { exercise: 'exercise-1', member: 'student@example.com', status: 'Passed', language: 'C++' } })
		const count = mocks.resource.reload.mock.calls.length
		await wrapper.setProps({ revision: 'updated' })
		expect(mocks.resource.reload).toHaveBeenCalledTimes(count + 1)
		expect(wrapper.find('a').exists()).toBe(false)
		wrapper.unmount()
	})
	it('renders measured results and missing metrics without navigating', async () => {
		const wrapper = mount(History, { props: { exercise: 'exercise-1', member: 'student@example.com' } })
		mocks.resource.data = [
			{ name: 's1', status: 'Passed', language: 'C++', creation: '2026-09-07 10:00:00', time_ms: 35, memory_kb: 44339 },
			{ name: 's2', status: 'Runtime Error', language: 'Python', creation: '2026-09-07 09:00:00', time_ms: 0, memory_kb: 0 },
		]
		await flushPromises()
		expect(wrapper.text()).toContain('35 ms')
		expect(wrapper.text()).toContain('43.3 MB')
		expect(wrapper.text()).toContain('执行出错')
		expect(wrapper.text()).toContain('N/A')
		await wrapper.find('tbody tr').trigger('click')
		expect(wrapper.emitted('select')?.[0]).toEqual(['s1'])
		wrapper.unmount()
	})
	it('does not query without a member and allows retry after failure', async () => {
		const wrapper = mount(History, { props: { exercise: 'exercise-1' } })
		expect(mocks.resource.reload).not.toHaveBeenCalled()
		mocks.resource.error = new Error('failed')
		await wrapper.setProps({ member: 'student@example.com' })
		expect(wrapper.find('[role="alert"]').exists()).toBe(true)
		await wrapper.find('[aria-label="刷新提交记录"]').trigger('click')
		expect(mocks.resource.reload).toHaveBeenCalledTimes(2)
		wrapper.unmount()
	})
})
