import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import Creation from '@/pages/Creation.vue'
import MyCreations from '@/pages/MyCreations.vue'
const { api, replace, route, leave } = vi.hoisted(() => ({
	api: vi.fn(),
	replace: vi.fn(),
	route: { params: {} as Record<string, string> },
	leave: vi.fn(),
}))
vi.mock('frappe-ui', () => ({
	call: api,
	Button: { template: '<button><slot /></button>' },
	Dialog: {
		props: ['open'],
		template:
			'<div v-if="open" role="dialog"><slot /><slot name="actions" /></div>',
	},
}))
vi.mock('vue-router', () => ({
	useRoute: () => route,
	useRouter: () => ({ replace }),
	onBeforeRouteLeave: leave,
	onBeforeRouteUpdate: vi.fn(),
}))
vi.mock('@/components/Controls/CodeEditor.vue', () => ({
	default: {
		props: ['modelValue'],
		emits: ['update:modelValue'],
		template:
			'<textarea aria-label="code" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
	},
}))
const options = {
	global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
}
beforeEach(() => {
	api.mockReset()
	replace.mockReset()
	route.params = {}
	leave.mockReset()
})
describe('Creation', () => {
	it('runs custom input and saves a server document without submission', async () => {
		api.mockImplementation(async (method, args) =>
			method.endsWith('run_creation')
				? { status: 'COMPLETED', stdout: '你好' }
				: { ...args, name: 'saved', modified: 'today' },
		)
		const w = mount(Creation, options)
		await w.get('input').setValue('我的代码')
		await w.get('[aria-label=code]').setValue('print(input())')
		await w.get('textarea[rows]').setValue('你好')
		await w
			.findAll('button')
			.find((b) => b.text() === '运行')!
			.trigger('click')
		await flushPromises()
		expect(api).toHaveBeenCalledWith('lms.lms.creation.run_creation', {
			language: 'Python',
			code: 'print(input())',
			stdin: '你好',
		})
		expect(w.text()).toContain('运行完成')
		expect(w.text()).toContain('你好')
		await w
			.findAll('button')
			.find((b) => b.text() === '保存')!
			.trigger('click')
		await flushPromises()
		expect(replace).toHaveBeenCalledWith({
			name: 'CreationDetail',
			params: { creationId: 'saved' },
		})
		expect(w.text()).toContain('已保存到服务器')
		expect(w.text()).not.toContain('提交')
		w.unmount()
	})
	it('restores code and keeps edits when saving fails', async () => {
		route.params = { creationId: 'existing' }
		api.mockResolvedValueOnce({
			name: 'existing',
			title: '之前的作品',
			language: 'C++',
			code: 'int main() {}',
			stdin: '123',
			modified: 'before',
		})
		const w = mount(Creation, options)
		await flushPromises()
		expect(
			(w.get('[aria-label=code]').element as HTMLTextAreaElement).value,
		).toBe('int main() {}')
		await w.get('[aria-label=code]').setValue('new code')
		api.mockRejectedValueOnce(new Error('保存失败'))
		await w
			.findAll('button')
			.find((b) => b.text() === '保存')!
			.trigger('click')
		await flushPromises()
		expect(w.text()).toContain('保存失败')
		expect(w.text()).toContain('有未保存的更改')
		expect(
			(w.get('[aria-label=code]').element as HTMLTextAreaElement).value,
		).toBe('new code')
		w.unmount()
	})
	it('blocks editing when a private work cannot be loaded', async () => {
		route.params = { creationId: 'forbidden' }
		api.mockRejectedValue(new Error('无权访问'))
		const w = mount(Creation, options)
		await flushPromises()
		expect(w.text()).toContain('无权访问')
		expect(w.find('textarea').exists()).toBe(false)
		w.unmount()
	})
	it('paginates and sends server filters without requesting code', async () => {
		api.mockResolvedValue({
			items: [
				{
					name: 'a',
					title: '我的作品一',
					language: 'Python',
					modified: '2026-09-28 10:00:00',
				},
			],
			total: 21,
		})
		const w = mount(MyCreations, options)
		await flushPromises()
		expect(w.find('pre').exists()).toBe(false)
		await w.get('[aria-label="下一页"]').trigger('click')
		await flushPromises()
		expect(api).toHaveBeenLastCalledWith('lms.lms.creation.get_creations', {
			start: 20,
			search: '',
			language: '',
			sort: 'modified',
			with_total: true,
		})
		await w.get('[aria-label="上一页"]').trigger('click')
		await flushPromises()
		await w.get('input').setValue('作品一')
		await w.get('form').trigger('submit')
		await flushPromises()
		await w
			.findAll('button')
			.find((b) => b.text() === 'Python')!
			.trigger('click')
		await w.get('select').setValue('title')
		await flushPromises()
		expect(api).toHaveBeenLastCalledWith('lms.lms.creation.get_creations', {
			start: 0,
			search: '作品一',
			language: 'Python',
			sort: 'title',
			with_total: true,
		})
		w.unmount()
	})
	it('renames metadata and requires confirmation before deleting', async () => {
		const item = {
			name: 'a',
			title: '作品一',
			language: 'Python',
			modified: '2026-09-28 10:00:00',
		}
		api.mockResolvedValue({ items: [item], total: 1 })
		const w = mount(MyCreations, options)
		await flushPromises()
		await w
			.findAll('button')
			.find((b) => b.text() === '重命名')!
			.trigger('click')
		await w.get('[aria-label="新的作品名称"]').setValue('新名称')
		await w
			.findAll('button')
			.find((b) => b.text() === '保存名称')!
			.trigger('click')
		await flushPromises()
		expect(api).toHaveBeenCalledWith('lms.lms.creation.rename_creation', {
			name: 'a',
			modified: item.modified,
			title: '新名称',
		})
		await w
			.findAll('button')
			.find((b) => b.text() === '删除')!
			.trigger('click')
		expect(
			api.mock.calls.some(([method]) => method.endsWith('delete_creation')),
		).toBe(false)
		api.mockRejectedValueOnce(new Error('作品已更新'))
		await w
			.findAll('button')
			.find((b) => b.text() === '确认删除')!
			.trigger('click')
		await flushPromises()
		expect(w.get('[role=dialog]').text()).toContain('作品已更新')
		expect(api).toHaveBeenCalledWith('lms.lms.creation.delete_creation', {
			name: 'a',
			modified: item.modified,
		})
		w.unmount()
	})
})
