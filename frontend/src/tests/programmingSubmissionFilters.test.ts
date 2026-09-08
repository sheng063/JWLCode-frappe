import { mount, flushPromises } from '@vue/test-utils'
import { reactive, defineComponent } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import { describe, expect, it, vi } from 'vitest'
vi.stubGlobal('__', (text: string) => text)
const resource = vi.hoisted(() => ({
	update: vi.fn(),
	reload: vi.fn(),
	data: [],
	delete: { submit: vi.fn() },
}))
vi.mock('frappe-ui', () => ({
	createListResource: () => resource,
	usePageMeta: vi.fn(),
	toast: {},
	Avatar: {},
	Badge: {},
	Button: {},
	FormControl: { template: '<div />' },
}))
vi.mock('@/stores/session', () => ({ sessionStore: () => ({ brand: {} }) }))
vi.mock('@/components/Controls/Link.vue', () => ({
	default: { template: '<div />' },
}))
vi.mock('@/components/Layouts/ListPage.vue', () => ({
	default: {
		props: ['listOptions'],
		template: '<div><slot name="filters" /></div>',
	},
}))
import ListPage from '@/components/Layouts/ListPage.vue'
import Submissions from '@/pages/ProgrammingExercises/ProgrammingExerciseSubmissions.vue'
describe('real submission filters', () => {
	it('waits for identity, scopes students to themselves, and follows exercise navigation', async () => {
		const router = createRouter({
			history: createMemoryHistory(),
			routes: [
				{
					path: '/submissions',
					component: defineComponent({ template: '<div />' }),
				},
			],
		})
		await router.push('/submissions?exercise=EX-1&member=someone-else')
		const user = reactive<any>({ data: null })
		resource.reload.mockClear()
		resource.update.mockClear()
		const wrapper = mount(Submissions, {
			global: {
				mocks: { __: (text: string) => text },
				plugins: [router],
				provide: { $user: user, $dayjs: () => ({ fromNow: () => '' }) },
			},
		})
		expect(resource.reload).not.toHaveBeenCalled()
		user.data = { name: 'student@example.com' }
		await flushPromises()
		expect(resource.update).toHaveBeenLastCalledWith({
			filters: { exercise: 'EX-1', member: 'student@example.com' },
			start: 0,
		})
		await router.push('/submissions?exercise=EX-2')
		await flushPromises()
		expect(resource.update).toHaveBeenLastCalledWith({
			filters: { exercise: 'EX-2', member: 'student@example.com' },
			start: 0,
		})
		const route = wrapper
			.findComponent(ListPage)
			.props('listOptions')
			.getRowRoute({ name: 'SUB-42', exercise: 'EX-2' })
		expect(route).toEqual({
			name: 'ProgrammingExerciseSubmission',
			params: { exerciseID: 'EX-2', submissionID: 'SUB-42' },
		})
		user.data.is_instructor = true
		await router.push('/submissions?exercise=EX-2&member=chosen@example.com')
		await flushPromises()
		expect(resource.update).toHaveBeenLastCalledWith({
			filters: { exercise: 'EX-2', member: 'chosen@example.com' },
			start: 0,
		})
		wrapper.unmount()
	})
})
