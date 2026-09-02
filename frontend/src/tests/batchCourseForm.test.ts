import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import {
	createMemoryHistory,
	createRouter,
	RouterView,
	type Router,
} from 'vue-router'
import { defineComponent, h, provide } from 'vue'

vi.stubGlobal('__', (text: string) => text)
enableAutoUnmount(afterEach)

const {
	addBatchCourse,
	createResourceMock,
	getCachedListResourceMock,
	updateOnboardingStepMock,
	toastMock,
} = vi.hoisted(() => {
	window.matchMedia ??= (() => ({
		matches: false,
		addEventListener: () => {},
		removeEventListener: () => {},
	})) as unknown as typeof window.matchMedia
	return {
		addBatchCourse: { loading: false, submit: vi.fn() },
		createResourceMock: vi.fn(),
		getCachedListResourceMock: vi.fn(),
		updateOnboardingStepMock: vi.fn(),
		toastMock: { success: vi.fn(), error: vi.fn() },
	}
})

vi.mock('@/components/HeaderButton.vue', () => ({
	default: { inheritAttrs: false, template: `<button v-bind="$attrs" />` },
}))

vi.mock('frappe-ui', () => ({
	createResource: createResourceMock,
	getCachedListResource: getCachedListResourceMock,
	toast: toastMock,
	Dialog: {
		props: ['open', 'title'],
		emits: ['update:open'],
		template: `<div v-if="open"><slot /><slot name="actions" /></div>`,
	},
	Button: { template: `<button><slot /></button>` },
}))

vi.mock('frappe-ui/frappe', () => ({
	useOnboarding: () => ({ updateOnboardingStep: updateOnboardingStepMock }),
}))

vi.mock('@/components/Controls/Link.vue', () => ({
	default: {
		props: ['modelValue', 'doctype', 'label'],
		emits: ['update:modelValue'],
		template: `<label :data-testid="'link-' + doctype">{{ label }}
			<input :value="modelValue" @input="$emit('update:modelValue', $event.target.value)" />
		</label>`,
	},
}))

// @ts-expect-error a JS SFC has no generated types (TS7016).
import BatchCourseForm from '@/pages/Forms/BatchCourseForm.vue'

const BatchPage = (reload: () => void) =>
	defineComponent({
		setup() {
			provide('reloadBatchDetails', reload)
			return () => h('div', [h(RouterView)])
		},
	})

const makeRouter = (reload: () => void): Router =>
	createRouter({
		history: createMemoryHistory(),
		routes: [
			{
				path: '/batches/:batchName',
				name: 'BatchDetail',
				component: BatchPage(reload),
				props: true,
				children: [
					{
						path: 'course/new',
						name: 'NewBatchCourse',
						component: BatchCourseForm,
						props: true,
					},
				],
			},
		],
	})

const mountForm = async (router: Router) => {
	const wrapper = mount(defineComponent({ render: () => h(RouterView) }), {
		global: {
			plugins: [router],
			provide: { $user: { data: { is_moderator: true } } },
			stubs: { teleport: true },
			mocks: { __: (text: string) => text },
		},
	})
	await flushPromises()
	return wrapper
}

describe('BatchCourseForm persistence', () => {
	beforeEach(() => {
		addBatchCourse.submit.mockReset()
		createResourceMock.mockReset()
		createResourceMock.mockReturnValue(addBatchCourse)
		getCachedListResourceMock.mockReset()
		updateOnboardingStepMock.mockReset()
		toastMock.success.mockReset()
		toastMock.error.mockReset()
		delete (window as Window & { read_only_mode?: boolean }).read_only_mode
	})

	it('saves through the parent endpoint and refreshes persisted batch data', async () => {
		const reloadCourses = vi.fn()
		const reloadBatch = vi.fn()
		getCachedListResourceMock.mockReturnValue({ reload: reloadCourses })
		addBatchCourse.submit.mockImplementation(
			(_params: unknown, options: { onSuccess: () => void }) => {
				options.onSuccess()
				return Promise.resolve()
			}
		)
		const router = makeRouter(reloadBatch)
		await router.push('/batches/B1/course/new#courses')
		const wrapper = await mountForm(router)

		await wrapper
			.find('[data-testid="link-LMS Course"] input')
			.setValue('COURSE-1')
		await wrapper
			.find('[data-testid="link-Course Evaluator"] input')
			.setValue('evaluator@example.com')
		await wrapper.find('[data-testid="batch-course-save"]').trigger('click')
		await flushPromises()

		expect(createResourceMock).toHaveBeenCalledWith({
			url: 'lms.lms.api.add_batch_course',
		})
		expect(addBatchCourse.submit).toHaveBeenCalledWith(
			{
				batch: 'B1',
				course: 'COURSE-1',
				evaluator: 'evaluator@example.com',
			},
			expect.any(Object)
		)
		expect(getCachedListResourceMock).toHaveBeenCalledWith([
			'batchCourses',
			'B1',
		])
		expect(reloadCourses).toHaveBeenCalledOnce()
		expect(reloadBatch).toHaveBeenCalledOnce()
		expect(router.currentRoute.value.name).toBe('BatchDetail')
		expect(router.currentRoute.value.hash).toBe('#courses')
	})
})
