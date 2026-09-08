import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import CoursePublishSettings from '@/pages/Courses/CoursePublishSettings.vue'

vi.hoisted(() => {
	// @/utils pulls in plyr, which touches matchMedia at import time.
	window.matchMedia ??= (() => ({
		matches: false,
		addEventListener: () => {},
		removeEventListener: () => {},
	})) as unknown as typeof window.matchMedia
})

vi.mock('@/stores/settings', () => ({
	useSettings: () => ({
		settings: { data: { is_payments_app_installed: 1 } },
	}),
}))

vi.mock('frappe-ui', () => ({
	Dialog: { template: '<div><slot /></div>' },
	FormControl: { template: '<div />' },
	createResource: () => ({ data: null, reload: vi.fn(), submit: vi.fn() }),
}))

vi.stubGlobal('__', (s: string) => s)

const doc = {
	name: 'COURSE-1',
	is_public: 0,
	upcoming: 0,
	featured: 0,
	disable_self_learning: 0,
	enforce_lesson_completion: 0,
}

describe('CoursePublishSettings', () => {
	it('renders a switch bound to enforce_lesson_completion', () => {
		const markDirty = vi.fn()
		const wrapper = mount(CoursePublishSettings, {
			global: {
				mocks: { __: (s: string) => s },
				provide: {
					courseForm: { resource: { doc }, markDirty },
					$dayjs: (v: unknown) => ({ format: () => String(v) }),
				},
				stubs: {
					CollapsibleSection: { template: '<div><slot /></div>' },
					Link: true,
					NewMemberModal: true,
					BooleanSwitch: {
						props: ['modelValue', 'label'],
						emits: ['update:modelValue'],
						template: `<button
							:data-label="label"
							@click="$emit('update:modelValue', !modelValue)"
						/>`,
					},
				},
			},
		})

		const toggle = wrapper.find('[data-label="Enforce Lesson Completion"]')
		expect(toggle.exists()).toBe(true)
	})

	it.each(['Enforce Lesson Completion', 'Public'])(
		'marks the form dirty when %s is flipped',
		async (label) => {
			const markDirty = vi.fn()
			const wrapper = mount(CoursePublishSettings, {
				global: {
					mocks: { __: (s: string) => s },
					provide: {
						courseForm: { resource: { doc: { ...doc } }, markDirty },
						$dayjs: (v: unknown) => ({ format: () => String(v) }),
					},
					stubs: {
						CollapsibleSection: { template: '<div><slot /></div>' },
						Link: true,
						NewMemberModal: true,
						BooleanSwitch: {
							props: ['modelValue', 'label'],
							emits: ['update:modelValue'],
							template: `<button
							:data-label="label"
							@click="$emit('update:modelValue', !modelValue)"
						/>`,
						},
					},
				},
			})

			await wrapper.find(`[data-label="${label}"]`).trigger('click')
			expect(markDirty).toHaveBeenCalled()
		}
	)
})
