import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'

const submissionSource = readFileSync(
	'src/pages/ProgrammingExercises/ProgrammingExerciseSubmission.vue',
	'utf8'
)
const appSource = readFileSync('src/App.vue', 'utf8')

describe('programming exercise answer editor', () => {
	it('renders the registered editable CodeEditor component', () => {
		expect(submissionSource).toContain('<CodeEditor')
		expect(submissionSource).toContain(
			"import CodeEditor from '@/components/Controls/CodeEditor.vue'"
		)
		expect(submissionSource).toContain(':type="editorLanguage"')
		expect(submissionSource).not.toMatch(/<Code\s/)
	})

	it('keeps run and submit as separate actions', () => {
		expect(submissionSource).toContain('@click="runCodeOnly"')
		expect(submissionSource).toContain('@click="submitCode"')
		expect(submissionSource).toContain('run_programming_exercise')
	})

	it('remounts the editor when navigating between exercises', () => {
		expect(appSource).toContain('<router-view :key="pageKey" />')
		expect(appSource).toContain("route.name === 'ProgrammingExerciseSubmission'")
	})

	it('initializes code from starter code and the current submission only', () => {
		expect(submissionSource).toContain('`${boilerplate.value}${submissionCode}`')
		expect(submissionSource).not.toContain('`${boilerplate.value}${code.value}`')
	})
})
