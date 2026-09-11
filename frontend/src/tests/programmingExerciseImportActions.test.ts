import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ProgrammingExercises from '@/pages/ProgrammingExercises/ProgrammingExercises.vue'

const { reload, push } = vi.hoisted(() => ({ reload: vi.fn(), push: vi.fn() }))
vi.mock('frappe-ui', () => ({
	Button: { template: '<button><slot /></button>' }, FormControl: { template: '<input />' },
	call: vi.fn(), toast: { success: vi.fn(), error: vi.fn() }, usePageMeta: vi.fn(),
	createListResource: () => ({ data: [{ name: 'EX1', title: 'Example' }], list: {}, update: vi.fn(), reload, pageLength: 24 }),
	createResource: () => ({ data: 1, update: vi.fn(), reload }),
}))
vi.mock('@/stores/session', () => ({ sessionStore: () => ({ brand: {} }) }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))
vi.mock('@/composables/useFormRoute', () => ({ openFormRoute: vi.fn() }))
vi.mock('@/components/Layouts/ListPage.vue', () => ({ default: { template: '<div><slot name="actions" /></div>' } }))
vi.mock('@/components/FormShell.vue', () => ({ default: { props: ['title'], template: '<section role="dialog"><h2>{{ title }}</h2><slot /></section>' } }))
vi.mock('@/components/ProblemPackageImport.vue', () => ({ default: { template: '<div data-testid="single-import" />' } }))
vi.mock('@/components/ProblemPackageBulkImport.vue', () => ({ default: { template: '<div data-testid="bulk-import" />' } }))

beforeEach(() => {
	vi.clearAllMocks()
	vi.stubGlobal('__', (text: string) => text)
	Object.defineProperty(String.prototype, 'format', { configurable: true, value: function (value: any) { return this.replace('{0}', value) } })
})
function page() {
	return mount(ProgrammingExercises, { global: {
		provide: { $user: { data: { is_instructor: true } } },
		mocks: { __: (text: string) => text },
		stubs: { RouterLink: { template: '<a><slot /></a>' }, RouterView: true },
	} })
}
describe('programming exercise import actions', () => {
	it('places bulk import immediately before submissions and opens an independent single importer', async () => {
		const wrapper = page()
		expect(wrapper.findAll('button').map(b => b.text())).toEqual(['Import', 'Bulk Import', 'Check All Submissions', 'Create'])
		await wrapper.findAll('button')[0].trigger('click')
		expect(wrapper.find('[data-testid=single-import]').exists()).toBe(true)
		expect(wrapper.find('[data-testid=bulk-import]').exists()).toBe(false)
		expect(push).not.toHaveBeenCalled()
		wrapper.unmount()
	})
	it('opens the bulk importer separately', async () => {
		const wrapper = page()
		await wrapper.findAll('button')[1].trigger('click')
		expect(wrapper.get('h2').text()).toBe('Bulk Import')
		expect(wrapper.find('[data-testid=bulk-import]').exists()).toBe(true)
		expect(wrapper.find('[data-testid=single-import]').exists()).toBe(false)
		wrapper.unmount()
	})
})
