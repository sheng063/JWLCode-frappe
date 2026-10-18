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
 expect(wrapper.find('[data-testid="failed-case-output"]').exists()).toBe(false)
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
 expect(wrapper.find('[data-testid="failed-case-output"]').exists()).toBe(false)
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

it.each(['Failed', 'Wrong Answer'])('displays the matching failed execution output for %s', async (status) => {
 mocks.doc = { ...mocks.doc, status, passed_tests: 1, test_cases: [
  { status: 'Passed', input: '1 1', output: '2', expected_output: '2' },
  { status: 'Failed', input: '2 3', output: '  4\n5\n', expected_output: '999' },
 ] }
 const wrapper = mount(Detail, { props: { name: 'S1' } }); await flushPromises()
 expect(wrapper.text()).toContain('错误解答')
 const input = wrapper.findAll('h3').find(h => h.text() === '最后执行的输入')!.element.parentElement!.nextElementSibling!
 expect(input.textContent).toBe('2 3')
 expect(input.nextElementSibling!.textContent).toBe('标准输出')
 expect(wrapper.get('[data-testid="failed-case-expected-output"]').element.textContent).toBe('999')
 expect(wrapper.get('[data-testid="failed-case-output"]').element.textContent).toBe('  4\n5\n')
 await wrapper.get('.failed-input-heading button').trigger('click')
 expect(wrapper.emitted('add-test-case')?.[0][0]).toEqual({ input: '2 3', expected_output: '999' })
 wrapper.unmount()
})
it.each([
 [{ status: 'Failed', input: '', output: '' }, '（无输出）'],
 [{ status: 'Failed', input: '' }, '暂无可展示的输出'],
 [undefined, '暂无可展示的输出'],
])('handles empty or unavailable execution output', async (testCase, expected) => {
 mocks.doc = { ...mocks.doc, status: 'Failed', test_cases: testCase ? [testCase] : [] }
 const wrapper = mount(Detail, { props: { name: 'S1' } }); await flushPromises()
 expect(wrapper.get('[data-testid="failed-case-output"]').text()).toBe(expected)
 wrapper.unmount()
})

it('uses versioned feedback for historical cases and disables quick add while running', async () => {
 mocks.doc = { ...mocks.doc, status: 'Failed', test_cases: [{ status: 'Failed', input: '2', expected_output: '', output: '3' }] }
 mocks.call.mockImplementation(async (method: string) => method === 'frappe.client.get' ? mocks.doc : { failed_case: { input: '2', expected_output: '4', output: '3' } })
 const wrapper = mount(Detail, { props: { name: 'S1', addingCaseDisabled: true } }); await flushPromises()
 expect(wrapper.get('[data-testid="failed-case-expected-output"]').text()).toBe('4')
 await wrapper.get('.failed-input-heading button').trigger('click')
 expect(wrapper.emitted('add-test-case')).toBeUndefined()
 wrapper.unmount()
})
