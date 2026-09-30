import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import InteractiveQuestion from '@/components/InteractiveQuestion.vue'
import { quizText } from '@/utils/quizText'
const { check } = vi.hoisted(() => ({ check: vi.fn() }))
vi.mock('frappe-ui', () => ({ call: check }))
const question = {
	name: 'q',
	type: 'Matching',
	items: [
		{ id: 'a', text: '<p>A</p>' },
		{ id: 'b', text: 'B' },
	],
	right_items: [
		{ id: 'x', text: 'X' },
		{ id: 'y', text: 'Y' },
	],
}
function matching() {
	return mount(InteractiveQuestion, {
		props: { question, quiz: 'quiz', modelValue: [] },
	})
}
async function clickText(w: any, text: string) {
	await w
		.findAll('button')
		.find((b: any) => b.text() === text)!
		.trigger('click')
}
describe('quiz plain text', () => {
	it('removes HTML and escaped HTML, retains line breaks and C++ text', () => {
		expect(quizText('<p>Hello <strong>world</strong></p><p>Next</p>')).toBe(
			'Hello world\nNext',
		)
		expect(quizText('&lt;p&gt;Hello&lt;/p&gt;')).toBe('Hello')
		expect(quizText('vector<int> a; x < 3 && y > 1')).toBe(
			'vector<int> a; x < 3 && y > 1',
		)
		expect(quizText('<p>vector&lt;int&gt; a;</p>')).toBe('vector<int> a;')
		expect(quizText('<script>alert(1)</script><p>OK</p>')).toBe('OK')
	})
})
describe('matching', () => {
	it.each([
		['A', 'X'],
		['X', 'A'],
	])('accepts either click order %s then %s', async (first, second) => {
		check.mockResolvedValue(true)
		const w = matching()
		await clickText(w, first)
		expect(w.emitted('update:modelValue')).toBeUndefined()
		await clickText(w, second)
		await flushPromises()
		expect(w.emitted('update:modelValue')![0]).toEqual([['a:x']])
		await w.setProps({ modelValue: ['a:x'] })
		expect(w.findAll('button').map((b) => b.text())).toEqual(['B', 'Y'])
		await w.setProps({ modelValue: ['a:x', 'b:y'] })
		expect(w.findAll('button')).toHaveLength(0)
		expect(w.text()).toContain('全部匹配正确')
		w.unmount()
	})
	it('keeps incorrect pairs visible and reports errors', async () => {
		check.mockResolvedValue(false)
		const w = matching()
		await clickText(w, 'A')
		await clickText(w, 'Y')
		await flushPromises()
		expect(w.emitted('update:modelValue')).toBeUndefined()
		expect(w.findAll('button')).toHaveLength(4)
		expect(w.text()).toContain('匹配错误')
		w.unmount()
	})
	it('does not complete against a different question after navigation', async () => {
		let resolve: any
		check.mockReturnValue(
			new Promise((r) => {
				resolve = r
			}),
		)
		const w = matching()
		await clickText(w, 'A')
		await clickText(w, 'X')
		w.unmount()
		resolve(true)
		await flushPromises()
		expect(w.emitted('update:modelValue')).toBeUndefined()
	})
})
describe('ordering', () => {
	it('moves items and restores saved order', async () => {
		const w = mount(InteractiveQuestion, {
			props: {
				question: { ...question, type: 'Ordering' },
				modelValue: ['b', 'a'],
			},
		})
		expect(w.text().indexOf('B')).toBeLessThan(w.text().indexOf('A'))
		await w.findAll('[aria-label="向上移动"]')[1].trigger('click')
		expect(w.emitted('update:modelValue')![0]).toEqual([['a', 'b']])
		w.unmount()
	})
})
