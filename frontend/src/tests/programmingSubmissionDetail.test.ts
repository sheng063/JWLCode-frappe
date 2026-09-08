import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, expect, it, vi } from 'vitest'
const mocks = vi.hoisted(() => ({ doc: {} as any, call: vi.fn() }))
vi.mock('frappe-ui', () => ({ call: mocks.call }))
import Detail from '@/components/ProgrammingSubmissionDetail.vue'
beforeEach(() => {
 mocks.doc = { name: 'S1', status: 'Passed', code: 'print(42)', language: 'Python', member_name: 'Alice', creation: '2026-09-07 12:34:56', total_tests: 5, passed_tests: 5, time_ms: 12, memory_kb: 2048 }
 mocks.call.mockImplementation(async (method: string) => method === 'frappe.client.get' ? mocks.doc : {})
 Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: vi.fn().mockResolvedValue(undefined) } })
})
it('shows exact result and copies the submitted source or restores it', async () => {
 const wrapper = mount(Detail, { props: { name: 'S1' } }); await flushPromises()
 expect(wrapper.text()).toContain('5 / 5')
 expect(wrapper.text()).toContain('Alice')
 expect(wrapper.text()).toContain('12:34:56')
 expect(wrapper.text()).toContain('12 ms')
 expect(wrapper.text()).toContain('2.00 MB')
 await wrapper.get('[aria-label="复制提交代码"]').trigger('click')
 expect(navigator.clipboard.writeText).toHaveBeenCalledWith('print(42)')
 await wrapper.findAll('button').find(b => b.text() === '复制到编辑器')!.trigger('click')
 expect(wrapper.emitted('restore')?.[0][0]).toMatchObject({ language: 'Python', code: 'print(42)' })
 wrapper.unmount()
})
it('replaces metrics with failure diagnostics and preserves empty input', async () => {
 mocks.doc = { ...mocks.doc, status: 'Runtime Error', passed_tests: 2, compiler_message: 'IndexError', test_cases: [{ status: 'Failed', input: '' }] }
 const wrapper = mount(Detail, { props: { name: 'S1' } }); await flushPromises()
 expect(wrapper.text()).toContain('2 / 5')
 expect(wrapper.text()).toContain('IndexError')
 expect(wrapper.text()).toContain('最后执行的输入')
 expect(wrapper.text()).not.toContain('执行用时')
 expect(wrapper.text()).not.toContain('暂无可展示的输入')
 wrapper.unmount()
})
it('allows retry after loading fails', async () => {
 mocks.call.mockRejectedValueOnce(new Error('offline'))
 const wrapper = mount(Detail, { props: { name: 'S1' } }); await flushPromises()
 expect(wrapper.find('[role="alert"]').exists()).toBe(true)
 await wrapper.get('button').trigger('click'); await flushPromises()
 expect(wrapper.text()).toContain('print(42)')
 wrapper.unmount()
})
