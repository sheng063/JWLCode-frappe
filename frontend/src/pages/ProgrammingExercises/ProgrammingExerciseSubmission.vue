<template>
	<PageHeader v-if="!fromLesson" :breadcrumbs="breadcrumbs" />
	<div
		v-if="falconError"
		class="flex items-center justify-between p-3 text-sm bg-surface-amber-1 text-ink-amber-3"
	>
		<span>
			{{ falconError }}
		</span>
		<Button v-if="user.data?.is_moderator" @click="openSettings('General')">
			<template #prefix>
				<span class="lucide-settings size-4" />
			</template>
			{{ __('Settings') }}
		</Button>
	</div>
	<div class="programming-workspace grid grid-cols-1 lg:grid-cols-2 h-[calc(100vh_-_3rem)] bg-surface-gray-1">
		<div class="border-e py-5 px-8 h-full overflow-y-auto bg-surface-white">
			<h2 class="font-semibold mb-2 text-ink-gray-9">
				{{ __('Problem Statement') }}
			</h2>
			<div
				v-safe-html:rich="exercise.doc?.problem_statement"
				class="ProseMirror prose prose-table:table-fixed prose-td:p-2 prose-th:p-2 prose-td:border prose-th:border prose-td:border-outline-gray-2 prose-th:border-outline-gray-2 prose-td:relative prose-th:relative prose-th:bg-surface-gray-2 prose-sm max-w-none !whitespace-normal"
			></div>
			<section v-if="exercise.doc?.test_cases?.length" class="mt-8 pt-6 border-t">
				<h2 class="font-semibold text-ink-gray-9">{{ __('Test Cases') }}</h2>
				<div class="mt-3 space-y-3">
					<div v-for="(testCase, index) in exercise.doc.test_cases" :key="testCase.name || index" class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-4">
						<div class="text-sm font-medium text-ink-gray-9">{{ __('Test {0}').format(index + 1) }}</div>
						<div class="mt-3 grid gap-3 sm:grid-cols-2">
							<div><div class="text-xs text-ink-gray-6">{{ __('Input') }}</div><pre class="test-case-value">{{ testCase.input || '—' }}</pre></div>
							<div><div class="text-xs text-ink-gray-6">{{ __('Expected Output') }}</div><pre class="test-case-value">{{ testCase.expected_output }}</pre></div>
						</div>
					</div>
				</div>
			</section>
		</div>
		<div class="flex min-h-0 flex-col">
			<div class="flex items-center justify-between p-3 bg-surface-white border-b">
				<div class="font-semibold text-ink-gray-9">
					{{ exercise.doc?.language }}
				</div>
				<div class="flex items-center gap-x-2">
					<Badge
						v-if="submission.doc?.status"
						:theme="submission.doc.status == 'Passed' ? 'green' : 'gray'"
					>
						{{ submission.doc.status }}
					</Badge>
					<Button
						v-if="
							(exercise.doc?.evaluation_mode === 'Judge Service' || !falconError) &&
							(submissionID == 'new' ||
								user.data?.name == submission.doc?.owner)
						"
						@click="runCodeOnly"
						:loading="running"
						:disabled="running || submitting"
						class="text-ink-gray-9"
					>
						<template #prefix>
							<span class="lucide-play size-3" />
						</template>
						{{ running ? __('Running') : __('Run') }}
					</Button>
					<Button
						v-if="
							(exercise.doc?.evaluation_mode === 'Judge Service' || !falconError) &&
							(submissionID == 'new' ||
								user.data?.name == submission.doc?.owner)
						"
						@click="submitCode"
						:loading="submitting"
						:disabled="running || submitting"
						class="text-ink-gray-9 !bg-transparent hover:!bg-surface-gray-2"
					>
						<template #prefix>
							<span class="lucide-send size-3" />
						</template>
						{{ submitting ? __('Submitting') : __('Submit') }}
					</Button>
				</div>
			</div>
			<div class="flex flex-col p-4 bg-surface-white border-b">
				<CodeEditor
					v-model="code"
					:type="editorLanguage"
					height="400px"
					:show-line-numbers="true"
				/>

			</div>

			<div ref="testCaseSection" class="min-h-0 flex-1 overflow-y-auto bg-surface-white">
				<div class="flex items-center gap-6 border-b px-5">
					<button class="test-panel-tab" :class="{ 'test-panel-tab-active': activeTestPanel === 'cases' }" @click="activeTestPanel = 'cases'"><span class="lucide-list-checks size-4" />{{ __('Test Cases') }}</button>
					<button class="test-panel-tab" :class="{ 'test-panel-tab-active': activeTestPanel === 'results' }" @click="activeTestPanel = 'results'"><span class="lucide-terminal size-4" />{{ __('Test Results') }}</button>
				</div>
				<div v-if="activeTestPanel === 'cases'" class="p-5">
					<div v-if="exercise.doc?.test_cases?.length" class="divide-y">
						<div v-for="(testCase, index) in exercise.doc.test_cases" :key="testCase.name || index" class="py-3 first:pt-0">
							<div class="font-medium text-ink-gray-9">{{ __('Test {0}').format(index + 1) }}</div>
							<div class="mt-2 grid gap-3 sm:grid-cols-2 text-sm"><div><span class="text-ink-gray-6">{{ __('Input') }}:</span> {{ testCase.input || '—' }}</div><div><span class="text-ink-gray-6">{{ __('Expected Output') }}:</span> {{ testCase.expected_output }}</div></div>
						</div>
					</div>
					<div v-else class="text-sm text-ink-gray-6">{{ __('No test cases available.') }}</div>
				</div>
				<div v-else class="p-5">
					<div v-if="resultMessage" class="result-notice mb-5" :class="`result-notice-${resultMessage.tone}`"><div class="font-semibold">{{ resultMessage.title }}</div><div v-if="resultMessage.detail" class="mt-2 whitespace-pre-wrap font-mono text-sm">{{ resultMessage.detail }}</div></div>
					<div v-if="testCases.length" class="divide-y">
					<div
						v-for="(testCase, index) in testCases"
						:key="testCase.input"
						class="py-3 first:pt-0"
					>
						<div class="flex items-center mb-3">
							<span class="text-ink-gray-9">
								{{ __('Test {0}').format(index + 1) }} -
							</span>
							<span
								class="font-semibold ms-2 me-1"
								:class="
									testCase.status === 'Passed'
										? 'text-ink-green-3'
										: 'text-ink-red-3'
								"
							>
								{{ testCase.status }}
							</span>
						</div>
						<div class="grid gap-4 sm:grid-cols-3">
							<div v-if="testCase.input" class="space-y-2">
								<div class="text-xs text-ink-gray-7">
									{{ __('Input') }}
								</div>
								<div class="text-ink-gray-9">{{ testCase.input }}</div>
							</div>
							<div class="space-y-2">
								<div class="text-xs text-ink-gray-7">
									{{ __('Your Output') }}
								</div>
								<div class="text-ink-gray-9">
									{{ testCase.output }}
								</div>
							</div>
							<div class="space-y-2">
								<div class="text-xs text-ink-gray-7">
									{{ __('Expected Output') }}
								</div>
								<div class="text-ink-gray-9">
									{{ testCase.expected_output }}
								</div>
							</div>
						</div>
					</div>
				</div>
				<div v-else class="text-sm text-ink-gray-6 mt-4">
					{{ __('Run or submit your code to view the test results.') }}
				</div>
			</div>
		</div>
	</div>
	</div>
</template>
<script setup lang="ts">
import {
	Badge,
	Button,
	call,
	createDocumentResource,
	toast,
	usePageMeta,
} from 'frappe-ui'
import { computed, inject, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import PageHeader from '@/components/Layouts/PageHeader.vue'
import CodeEditor from '@/components/Controls/CodeEditor.vue'
import { sessionStore } from '@/stores/session'
import { useRouter } from 'vue-router'
import { openSettings } from '@/utils'
import { useSettings } from '@/stores/settings'
import { getLmsRoute } from '@/utils/basePath'
import { provideStudentView } from '@/composables/useStudentView'

const realUser = inject<any>('$user')

// Rendered in an iframe from the lesson preview, so provide/inject can't reach
// this app instance; Student View arrives as a query param instead, exactly as
// it does for assignment submissions. Unlike AssignmentSubmission, this page
// reads the instructor flags in its *own* template (the settings button, the
// view-someone-else's-submission branch), so it uses the masked user itself
// rather than only providing it to children.
const studentView = ref(
	new URLSearchParams(window.location.search).get('studentView') === '1'
)
const { mockedUser: user } = provideStudentView(
	realUser,
	() => studentView.value
)
const code = ref<string | null>('')
const output = ref<string | null>(null)
const error = ref<boolean | null>(null)
const errorMessage = ref<string | null>(null)
const testCaseSection = ref<HTMLElement | null>(null)
const testCases = ref<TestCase[]>([])
const activeTestPanel = ref<'cases' | 'results'>('cases')
const resultMessage = ref<{ tone: 'success' | 'error' | 'info'; title: string; detail?: string | null } | null>(null)
const boilerplate = ref<string>('')
const { brand } = sessionStore()
const { settings } = useSettings()
const router = useRouter()
const fromLesson = ref(false)
const falconURL = ref<string>('https://falcon.frappe.io')
const falconError = ref<string | null>(null)
const running = ref<boolean>(false)
const submitting = ref<boolean>(false)
let statusTimer: ReturnType<typeof setTimeout> | null = null

const props = withDefaults(
	defineProps<{
		exerciseID: string
		submissionID?: string
	}>(),
	{
		submissionID: 'new',
	}
)

onMounted(() => {
	loadFalcon()
	checkIfUserIsPermitted()
	checkIfInLesson()
	fetchSubmission()
})

onBeforeUnmount(() => {
	if (statusTimer) clearTimeout(statusTimer)
})

const checkIfInLesson = () => {
	if (new URLSearchParams(window.location.search).get('fromLesson')) {
		fromLesson.value = true
	}
}

const fetchSubmission = (name: string = '') => {
	if (name) {
		submission.name = name
		submission.reload()
	} else if (props.submissionID != 'new') {
		submission.reload()
	}
}

const exercise = createDocumentResource({
	doctype: 'LMS Programming Exercise',
	name: props.exerciseID,
	cache: ['programmingExercise', props.exerciseID],
	auto: true,
})

const editorLanguage = computed<'Python' | 'JavaScript' | 'C++'>(() => {
	if (exercise.doc?.language === 'JavaScript') return 'JavaScript'
	if (exercise.doc?.language === 'C++') return 'C++'
	return 'Python'
})

const submission = createDocumentResource({
	doctype: 'LMS Programming Exercise Submission',
	name: props.submissionID,
	auto: false,
	onError(error: any) {
		if (error.messages?.[0].includes('not found')) {
			router.push({
				name: 'ProgrammingExerciseSubmission',
				params: { exerciseID: props.exerciseID, submissionID: 'new' },
			})
		} else {
			toast.error(__(error.messages?.[0] || error))
		}
	},
})

const loadedSubmissionCode = ref('')

const updateCode = () => {
	if (!exercise.doc) return
	updateBoilerPlate()
	const submissionCode = loadedSubmissionCode.value
	code.value =
		exercise.doc.evaluation_mode === 'Judge Service' && submissionCode
			? submissionCode
			: `${boilerplate.value}${submissionCode}`
}

watch(() => exercise.doc, updateCode)

const updateBoilerPlate = () => {
	if (exercise.doc?.language == 'Python') {
		boilerplate.value = exercise.doc?.evaluation_mode === 'Judge Service'
			? `import sys\n\ndata = sys.stdin.read()\ninputs = data.split() if len(data) else []\n\n# inputs is a list of strings\n# write your code below\n\n`
			: `with open("stdin", "r") as f:\n    data = f.read()\n\ninputs = data.split() if len(data) else []\n\n# inputs is a list of strings\n# write your code below\n\n`
	} else if (exercise.doc?.language == 'JavaScript') {
		const inputPath = exercise.doc?.evaluation_mode === 'Judge Service' ? '0' : "'/app/stdin'"
		boilerplate.value = `const fs = require('fs');\n\nlet input = fs.readFileSync(${inputPath}, 'utf8').trim();\nconst inputs = input.split("\\n");\n// inputs is an array of strings\n// write your code below\n`
	} else if (exercise.doc?.language == 'C++') {
		boilerplate.value = `#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n\n    // write your code below\n\n    return 0;\n}\n`
	}
}

const checkIfUserIsPermitted = (doc: any = null) => {
	if (!user.data) {
		const redirectPath = getLmsRoute(
			`programming-exercises/${props.exerciseID}/submission/${props.submissionID}`
		)
		window.location.href = `/login?redirect-to=${redirectPath}`
	}

	if (!doc) return
	if (
		doc.owner != user.data?.name &&
		!user.data?.is_instructor &&
		!user.data?.is_moderator &&
		!user.data.is_evaluator
	) {
		router.push({
			name: 'Courses',
		})
		return
	}
}

const updateTestCases = (doc: any) => {
	if (testCases.value.length === 0) {
		testCases.value = doc.test_cases || []
	}
}

watch(
	() => submission.doc,
	(doc) => {
		if (doc) {
			checkIfUserIsPermitted(doc)
			updateTestCases(doc)
			loadedSubmissionCode.value = doc.code || ''
			updateCode()
		}
	},
	{ immediate: true }
)

const loadFalcon = () => {
	// An unset livecode_url leaves the default in place rather than building
	// `undefined/static/livecode.js`.
	if (settings.data?.livecode_url) {
		falconURL.value = settings.data.livecode_url
	}
	return new Promise((resolve, reject) => {
		const script = document.createElement('script')
		script.src = `${falconURL.value}/static/livecode.js`
		script.onload = resolve
		script.onerror = reject
		document.head.appendChild(script)
	})
}

const submitCode = async () => {
	submitting.value = true
	try {
		if (exercise.doc?.evaluation_mode === 'Judge Service') {
			await createJudgeSubmission()
		} else {
			await runCode()
			await createSubmission()
		}
	} finally {
		submitting.value = false
	}
}

const runCodeOnly = async () => {
	running.value = true
	error.value = false
	errorMessage.value = null
	try {
		if (exercise.doc?.evaluation_mode === 'Judge Service') {
			await runJudgeCode()
		} else {
			await runCode()
		}
	} catch (e: any) {
		error.value = true
		errorMessage.value = e?.messages?.[0] || e?.message || String(e)
		showResult('error', __('Unable to run code'), errorMessage.value)
	} finally {
		running.value = false
	}
}

const runJudgeCode = async () => {
	testCases.value = []
	resultMessage.value = null
	activeTestPanel.value = 'results'
	if (testCaseSection.value) {
		testCaseSection.value.scrollIntoView({ behavior: 'smooth' })
	}
	const result = await call('lms.lms.judge_service.run_programming_exercise', {
		exercise: props.exerciseID,
		code: code.value || '',
	})
	if (result.compiler_message) {
		error.value = true
		errorMessage.value = result.compiler_message
		showResult('error', __('Compilation Error'), result.compiler_message)
	}
	testCases.value = (result.cases || []).map((item: any) => {
		const testCase = exercise.doc?.test_cases?.[item.index - 1]
		return {
			input: testCase?.input || '',
			output: (item.stdout || '').trim(),
			expected_output: testCase?.expected_output || '',
			status: item.status === 'Accepted' ? 'Passed' : 'Failed',
		}
	})
	if (!result.compiler_message) showTestCaseSummary()
}

const createJudgeSubmission = async () => {
	const data = await call('lms.lms.judge_service.submit_programming_exercise', {
		exercise: props.exerciseID,
		submission: props.submissionID,
		code: code.value || '',
		client_request_id: crypto.randomUUID(),
	})
	const submissionName = data.submission
	if (props.submissionID === 'new') {
		await router.push({
			name: 'ProgrammingExerciseSubmission',
			params: { exerciseID: props.exerciseID, submissionID: submissionName },
		})
	}
	fetchSubmission(submissionName)
	pollJudgeStatus(submissionName)
	showResult('info', __('Submission queued'), __('Your code is being evaluated.'))
}

const pollJudgeStatus = (submissionName: string) => {
	if (statusTimer) clearTimeout(statusTimer)
	statusTimer = setTimeout(async () => {
		try {
			const result = await call(
				'lms.lms.judge_service.get_programming_submission_status',
				{ submission: submissionName }
			)
			await submission.reload()
			if (result.compiler_message) {
				error.value = true
				errorMessage.value = result.compiler_message
				showResult('error', __('Compilation Error'), result.compiler_message)
			}
			if (['Queued', 'Compiling', 'Running'].includes(result.status)) {
				pollJudgeStatus(submissionName)
			} else if (!result.compiler_message) {
				showResult(result.status === 'Passed' ? 'success' : 'error', result.status === 'Passed' ? __('All tests passed') : __('Submission failed'))
			}
		} catch (e) {
			console.error('Unable to refresh judge status', e)
		}
	}, 1500)
}

const runCode = async () => {
	if (!exercise.doc?.test_cases?.length) return

	testCases.value = []
	if (testCaseSection.value) {
		testCaseSection.value.scrollIntoView({ behavior: 'smooth' })
	}

	for (const test_case of exercise.doc.test_cases) {
		let result = await execute(test_case.input)
		if (error.value) {
			errorMessage.value = result
			break
		} else {
			output.value = result
		}
		let status =
			result.trim() === test_case.expected_output.trim() ? 'Passed' : 'Failed'
		testCases.value.push({
			input: test_case.input,
			output: result,
			expected_output: test_case.expected_output,
			status: status,
		})
	}
	if (error.value) showResult('error', __('Execution Error'), errorMessage.value)
	else showTestCaseSummary()
}

const showTestCaseSummary = () => {
	const passed = testCases.value.filter((testCase) => testCase.status === 'Passed').length
	showResult(passed === testCases.value.length ? 'success' : 'error', passed === testCases.value.length ? __('All tests passed') : __('Some tests failed'), __('Passed {0} of {1} test cases.').format(passed, testCases.value.length))
}

const showResult = (tone: 'success' | 'error' | 'info', title: string, detail: string | null = null) => {
	activeTestPanel.value = 'results'
	resultMessage.value = { tone, title, detail }
}

const createSubmission = () => {
	if (!testCases.value.length) return
	let codeToSave = code.value?.replace(boilerplate.value, '') || ''

	return call('lms.lms.api.create_programming_exercise_submission', {
		exercise: props.exerciseID,
		submission: props.submissionID,
		code: codeToSave,
		test_cases: testCases.value,
	})
		.then((data: any) => {
			if (props.submissionID == 'new') {
				router.push({
					name: 'ProgrammingExerciseSubmission',
					params: { exerciseID: props.exerciseID, submissionID: data },
				})
				fetchSubmission(data)
			} else {
				fetchSubmission(props.submissionID)
			}
			showTestCaseSummary()
		})
		.catch((error: any) => {
			console.error('Error creating submission:', error)
			showResult('error', __('Unable to submit code'), String(error))
		})
}

const execute = (stdin = ''): Promise<string> => {
	return new Promise((resolve, reject) => {
		let outputChunks: string[] = []
		let hasExited = false
		let hasError = false

		let session = new LiveCodeSession({
			base_url: falconURL.value,
			runtime: exercise.doc?.language.toLowerCase() || 'python',
			code: code.value,
			files: [{ filename: 'stdin', contents: stdin }],
			onMessage: (msg: any) => {
				console.log('msg', msg)

				if (msg.msgtype === 'write' && msg.file === 'stdout') {
					outputChunks.push(msg.data)
				}

				if (msg.msgtype === 'write' && msg.file === 'stderr') {
					hasError = true
					errorMessage.value = msg.data
				}

				if (msg.msgtype === 'exitstatus') {
					hasExited = true
					if (msg.exitstatus !== 0) {
						error.value = true
					} else {
						error.value = false
					}
					resolve(outputChunks.join('').trim())
				}
			},
		})

		setTimeout(() => {
			if (!hasExited) {
				running.value = false
				error.value = true
				errorMessage.value = 'Execution timed out.'
				reject('Execution timed out.')
			}
		}, 20000)
	})
}

const breadcrumbs = computed(() => {
	return [
		{
			label: __('Programming Exercise Submissions'),
			route: { name: 'ProgrammingExerciseSubmissions' },
		},
		{ label: exercise.doc?.title },
	]
})

usePageMeta(() => {
	return {
		title: __('Programming Exercise Submission'),
		icon: brand.favicon,
	}
})
</script>
<style>
.ProseMirror pre {
	background: theme('colors.gray.200');
	color: theme('colors.gray.900');
}

.test-case-value { margin: 0.35rem 0 0; padding: 0.5rem 0.625rem; white-space: pre-wrap; word-break: break-word; border-radius: 0.375rem; background: theme('colors.gray.100'); color: theme('colors.gray.900'); font-size: 0.8125rem; }
.test-panel-tab { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.875rem 0; border-bottom: 2px solid transparent; color: theme('colors.gray.600'); font-size: 0.875rem; font-weight: 500; }
.test-panel-tab-active { border-color: theme('colors.green.500'); color: theme('colors.gray.900'); }
.result-notice { border-radius: 0.5rem; padding: 1rem; }
.result-notice-success { background: theme('colors.green.100'); color: theme('colors.green.800'); }
.result-notice-error { background: theme('colors.red.100'); color: theme('colors.red.700'); }
.result-notice-info { background: theme('colors.blue.100'); color: theme('colors.blue.800'); }
</style>
