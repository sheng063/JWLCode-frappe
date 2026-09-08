import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ProgrammingExercises from '@/pages/ProgrammingExercises/ProgrammingExercises.vue'
import ListPage from '@/components/Layouts/ListPage.vue'
const { update, countUpdate, reload, rows } = vi.hoisted(() => ({ update: vi.fn(), countUpdate: vi.fn(), reload: vi.fn(), rows: [{ name: 'EX1', exercise_number: 'P-000042', title: 'Example' }] }))
vi.mock('frappe-ui', () => ({
 Button: { template: '<button><slot /></button>' },
 FormControl: { props: ['modelValue'], emits: ['update:modelValue', 'input'], template: `<input :value="modelValue" @input="$emit('input'); $emit('update:modelValue', $event.target.value)" />` },
 call: vi.fn(), toast: { success: vi.fn(), error: vi.fn() }, usePageMeta: vi.fn(),
 createListResource: () => ({ data: rows, list: {}, update, reload, pageLength: 24 }),
 createResource: () => ({ data: 1, update: countUpdate, reload }),
}))
vi.mock('@/stores/session', () => ({ sessionStore: () => ({ brand: {} }) }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))
vi.mock('@/composables/useFormRoute', () => ({ openFormRoute: vi.fn() }))
vi.mock('@/components/Layouts/ListPage.vue', () => ({ default: { props: ['rows', 'columns'], template: '<div><slot name="filters" /></div>' } }))
vi.mock('@/components/FormShell.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/components/ProblemPackageImport.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/components/ProblemPackageBulkImport.vue', () => ({ default: { template: '<div />' } }))
beforeEach(() => {
 vi.clearAllMocks(); vi.stubGlobal('__', (s: string) => s)
 Object.defineProperty(String.prototype, 'format', { configurable: true, value: function (v: unknown) { return this.replace('{0}', String(v)) } })
})
describe('permanent exercise numbers', () => {
 it('displays stored numbers and searches both title and number with matching count and reset pagination', async () => {
  const wrapper = mount(ProgrammingExercises, { global: { provide: { $user: { data: { is_instructor: true } } }, mocks: { __: (s: string) => s }, stubs: { RouterView: true } } })
  expect(wrapper.getComponent(ListPage).props('rows')[0].exercise_number).toBe('P-000042')
  expect(wrapper.getComponent(ListPage).props('columns')[0].key).toBe('exercise_number')
  await wrapper.get('input').setValue(' P-000042 ')
  expect(update).toHaveBeenLastCalledWith({ start: 0, orFilters: { title: ['like', '%P-000042%'], exercise_number: ['like', '%P-000042%'] } })
  expect(countUpdate).toHaveBeenLastCalledWith({ params: { search: 'P-000042' } })
  await wrapper.get('input').setValue('')
  expect(update).toHaveBeenLastCalledWith({ start: 0, orFilters: {} })
  wrapper.unmount()
 })
})
