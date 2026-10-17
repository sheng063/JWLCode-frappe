import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import GameUnlockCondition from '@/components/GameUnlockCondition.vue'
const { api } = vi.hoisted(() => ({ api: vi.fn() }))
vi.mock('frappe-ui', () => ({ call: api }))

describe('Game unlock lesson options', () => {
	it('discards delayed lesson options after switching courses', async () => {
		let resolveOld: (value: unknown) => void = () => {}
		api.mockImplementation((_method, args) =>
			args.course === 'old'
				? new Promise((resolve) => {
						resolveOld = resolve
					})
				: Promise.resolve([
						{ name: 'new-lesson', title: '新课时', chapter_title: '新章节' },
					]),
		)
		const w = mount(GameUnlockCondition, { props: { course: 'old' } })
		await w.setProps({ course: 'new' })
		await flushPromises()
		resolveOld([
			{ name: 'old-lesson', title: '旧课时', chapter_title: '旧章节' },
		])
		await flushPromises()
		expect(w.text()).toContain('新课时')
		expect(w.text()).not.toContain('旧课时')
		w.unmount()
	})
	it('preserves an existing target when loading fails and offers retry', async () => {
		api.mockReset()
		api
			.mockRejectedValueOnce(new Error('offline'))
			.mockResolvedValueOnce([
				{ name: 'lesson', title: '课时', chapter_title: '章节' },
			])
		const w = mount(GameUnlockCondition, {
			props: { course: 'course', modelValue: 'lesson' },
		})
		await flushPromises()
		expect(w.get('[role=alert]').text()).toContain('无法加载课时')
		expect((w.get('select').element as HTMLSelectElement).value).toBe('lesson')
		expect(w.emitted('update:modelValue')).toBeUndefined()
		await w.get('button').trigger('click')
		await flushPromises()
		expect(w.find('[role=alert]').exists()).toBe(false)
		expect(w.text()).toContain('完成课时：章节 / 课时')
		w.unmount()
	})
})
