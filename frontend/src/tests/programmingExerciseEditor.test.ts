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

	it('offers Python and C++ templates and restores saved code', () => {
		expect(submissionSource).toContain('#include <bits/stdc++.h>')
		expect(submissionSource).toContain('using namespace std;')
		expect(submissionSource).toContain('def solve() -> None:')
		expect(submissionSource).toContain('data-testid="submission-language"')
		expect(submissionSource).toContain('language: selectedLanguage.value')
		expect(submissionSource).toContain('code.value = saved?.code ?? starterCode.value')
		expect(submissionSource).not.toContain('cout')
	})

	it('saves submitted code locally without overwriting historical submissions', () => {
		expect(submissionSource).toContain('await createSubmission()')
		expect(submissionSource).toContain('saveProgrammingCode(user.data?.name, props.exerciseID,')
		expect(submissionSource).not.toContain('save_programming_exercise_code')
		expect(submissionSource).toContain('msg.file || msg.stream || msg.channel')
		expect(submissionSource).toContain("selectedTestResult.output || '—'")
	})
})
