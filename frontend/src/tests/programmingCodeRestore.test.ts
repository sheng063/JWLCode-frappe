import { beforeEach, expect, it, vi } from 'vitest'
import { shallowMount } from '@vue/test-utils'
import { reactive, nextTick } from 'vue'
import { saveProgrammingCode, readProgrammingCode } from '@/utils/programmingCodeCache'
import { readProgrammingLanguage, saveProgrammingLanguage } from '@/utils/programmingLanguagePreference'
const state = vi.hoisted(() => ({ resources: [] as any[] }))
vi.mock('frappe-ui', async () => {
 const { reactive } = await import('vue')
 return {
  Badge: {}, Button: { name: 'Button', template: '<button><slot /></button>' }, FormControl: {}, toast: { error: vi.fn() }, call: vi.fn(), usePageMeta: vi.fn(),
  createDocumentResource: (o: any) => {
   const r = reactive({ name: o.name, doc: o.doctype === 'LMS Programming Exercise' ? { name: o.name, language: 'C++', test_cases: [] } : null, reload: vi.fn() })
   state.resources.push(r); return r
  },
 }
})
vi.mock('vue-router', () => ({ useRoute: () => ({ query: { testExercise: '1' } }), useRouter: () => ({ push: vi.fn() }) }))
vi.mock('@/stores/session', () => ({ sessionStore: () => ({ brand: {} }) }))
vi.mock('@/stores/settings', () => ({ useSettings: () => ({ settings: { data: {} } }) }))
vi.mock('@/utils', () => ({ openSettings: vi.fn() }))
vi.mock('@/utils/composables', () => ({ useScreenSize: () => ({ size: { width: 1024, height: 768 } }) }))
vi.mock('@/components/MathContent.vue', () => ({ default: {} }))
vi.mock('@/components/ProgrammingSubmissionHistory.vue', () => ({ default: {} }))
vi.mock('@/components/Layouts/PageHeader.vue', () => ({ default: {} }))
vi.mock('@/components/ProgrammingEditorSettings.vue', () => ({ default: {} }))
vi.mock('@/components/Controls/CodeEditor.vue', () => ({ default: { props: ['modelValue'], methods: { getValue() { return (this as any).modelValue } }, template: '<textarea :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />' } }))
import Page from '@/pages/ProgrammingExercises/ProgrammingExerciseSubmission.vue'
beforeEach(() => {
 localStorage.clear(); state.resources = []
 vi.stubGlobal('__', (text: string) => text)
 ;(String.prototype as any).format = function (...args: any[]) { return String(this).replace(/\{(\d+)\}/g, (_, i) => args[i]) }
 vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} })
})
function open(exerciseID: string, submissionID = 'new', name = 'alice') {
 return shallowMount(Page, { props: { exerciseID, submissionID }, global: { mocks: { __: (text: string) => text }, provide: { $user: reactive({ data: { name } }) }, stubs: { CodeEditor: false, Button: false } } })
}
const source = (page: any) => page.find('textarea').element.value
it('restores the preferred language across exercises', async () => {
 saveProgrammingLanguage('Python')
 saveProgrammingCode('alice', 'A', { language: 'Python', code: 'print(123)' })
 for (const exercise of ['A', 'B', 'A']) {
  const page = open(exercise); await nextTick()
  if (exercise === 'A') expect(source(page)).toBe('print(123)')
  else expect(source(page)).toContain('def solve() -> None:')
  page.unmount()
 }
})
it('does not read another account’s code or save initialization and typing', async () => {
 saveProgrammingCode('alice', 'A', { language: 'Python', code: 'private' })
 const page = open('A', 'new', 'bob'); await nextTick()
 expect(source(page)).toContain('#include')
 await page.find('textarea').setValue('unsent')
 expect(readProgrammingCode('bob', 'A')).toBeNull()
 page.unmount()
})
it('shows historical code without overwriting the cache and restores cache on returning to new', async () => {
 saveProgrammingLanguage('Python')
 saveProgrammingCode('alice', 'A', { language: 'Python', code: 'latest' })
 const page = open('A', 'SUB-1')
 state.resources[1].doc = { name: 'SUB-1', exercise: 'A', owner: 'alice', language: 'C++', code: 'historical' }
 await nextTick()
 expect(source(page)).toBe('historical')
 expect(readProgrammingLanguage()).toBe('Python')
 expect(readProgrammingCode('alice', 'A')?.code).toBe('latest')
 await page.setProps({ submissionID: 'new' })
 expect(source(page)).toBe('latest')
 page.unmount()
})
it('stores the exact code on submit even if evaluation fails', async () => {
 const page = open('A')
 state.resources[0].doc.evaluation_mode = 'Judge Service'
 await page.find('textarea').setValue('int main() { return 42; }')
 // Run and Submit are the final two toolbar buttons.
 const button = page.findAll('button').find(button => button.text() === 'Submit')!
 await button.trigger('click')
 expect(readProgrammingCode('alice', 'A')).toEqual({ language: 'C++', code: 'int main() { return 42; }' })
 page.unmount()
})

it('restores independent submissions when switching languages and uses a template for a missing language', async () => {
 saveProgrammingCode('alice', 'A', { language: 'Python', code: 'python answer' })
 saveProgrammingCode('alice', 'A', { language: 'C++', code: 'cpp answer' })
 const page = open('A'); await nextTick()
 expect(source(page)).toBe('cpp answer')
 const language = page.findComponent('[data-testid="submission-language"]')
 language.vm.$emit('update:modelValue', 'Python'); await nextTick()
 expect(source(page)).toBe('python answer')
 language.vm.$emit('update:modelValue', 'C++'); await nextTick()
 expect(source(page)).toBe('cpp answer')
 page.unmount()
 saveProgrammingCode('alice', 'B', { language: 'C++', code: 'only cpp' })
 const other = open('B'); await nextTick()
 other.findComponent('[data-testid="submission-language"]').vm.$emit('update:modelValue', 'Python')
 await nextTick()
 expect(source(other)).toContain('def solve() -> None:')
 other.unmount()
})
it('opens and closes inline history and restores the submission language and code', async () => {
 const page = open('A'); await nextTick()
 const vm = page.vm as any
 vm.openSubmission('SUB-1')
 vm.openSubmission('SUB-1')
 await nextTick()
 expect(vm.submissionTabs).toEqual(['SUB-1'])
 expect(vm.activeSubmission).toBe('SUB-1')
 await vm.restoreSubmissionCode({ language: 'Python', code: 'print("restored")' })
 await nextTick()
 expect(source(page)).toBe('print("restored")')
 expect(vm.selectedLanguage).toBe('Python')
 expect(vm.activeSubmission).toBe('')
 vm.openSubmission('SUB-1'); vm.closeSubmission('SUB-1')
 expect(vm.submissionTabs).toEqual([])
 expect(source(page)).toBe('print("restored")')
 page.unmount()
})
it('shows submission status tabs only in the problem pane and keeps the editor visible', async () => {
 const page = open('A'); await nextTick()
 const vm = page.vm as any
 vm.openSubmission('SUB-1'); await nextTick()
 vm.updateSubmissionStatus({ name: 'SUB-1', exercise: 'A', status: 'Passed' }); await nextTick()
 expect(page.find('.problem-pane programming-submission-detail-stub').exists()).toBe(true)
 expect(page.find('.code-column programming-submission-detail-stub').exists()).toBe(false)
 expect(page.find('.submission-tab .problem-tab').text()).toBe('通过')
 expect(page.findAll('.tab-divider')).toHaveLength(2)
 expect(page.find('textarea').isVisible()).toBe(true)
 vm.selectProblemTab('description'); await nextTick()
 expect(vm.activeSubmission).toBe('')
 page.unmount()
})
it('only displays solved for a passed submission by the current user on the current exercise', async () => {
 const page = open('A'); await nextTick()
 for (const doc of [
  { exercise: 'B', member: 'alice', status: 'Passed' },
  { exercise: 'A', member: 'bob', status: 'Passed' },
  { exercise: 'A', member: 'alice', status: 'Failed' },
  { exercise: 'A', member: 'alice', status: 'Queued' },
  null,
 ]) {
  state.resources[1].doc = doc; await nextTick()
  expect(page.find('.solved-label').exists()).toBe(false)
 }
 state.resources[1].doc = { exercise: 'A', member: 'alice', status: 'Passed' }; await nextTick()
 expect(page.find('.solved-label').exists()).toBe(true)
 await page.setProps({ exerciseID: 'B' })
 expect(page.find('.solved-label').exists()).toBe(false)
 page.unmount()
})

it('defaults to C++ even when the last submitted language is Python', async () => {
 saveProgrammingCode('alice', 'A', { language: 'Python', code: 'print(123)' })
 const page = open('A'); await nextTick()
 expect((page.vm as any).selectedLanguage).toBe('C++')
 expect(source(page)).toContain('#include')
 page.unmount()
})
it('persists a dropdown change without submitting and restores it on another exercise', async () => {
 const page = open('A'); await nextTick()
 page.findComponent('[data-testid="submission-language"]').vm.$emit('update:modelValue', 'Python')
 await nextTick()
 expect(readProgrammingLanguage()).toBe('Python')
 page.unmount()
 const other = open('B'); await nextTick()
 expect((other.vm as any).selectedLanguage).toBe('Python')
 expect(source(other)).toContain('def solve() -> None:')
 other.unmount()
})

it('shows the complete teacher test navigation and does not load Falcon for judge exercises', async () => {
 const page = open('A'); await nextTick()
 state.resources[0].doc.evaluation_mode = 'Judge Service'
 state.resources[0].doc.title = 'Sum'
 await nextTick()
 expect((page.vm as any).breadcrumbs.map((item: any) => item.label)).toEqual(['Programming Exercises', 'Sum', 'Test this Exercise'])
 expect((page.vm as any).testingExercise).toBe(true)
 expect(document.querySelector('script[src*="livecode.js"]')).toBeNull()
 page.unmount()
})
