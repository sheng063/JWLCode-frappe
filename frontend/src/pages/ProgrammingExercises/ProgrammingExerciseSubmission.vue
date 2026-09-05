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
	<div
		ref="workspace"
		class="programming-workspace flex flex-col lg:flex-row h-[calc(100vh_-_3rem)] bg-surface-gray-1"
		:class="{ resizing: horizontalDragging || verticalDragging }"
	>
		<div
			class="border-b lg:border-b-0 lg:border-e py-5 px-8 bg-surface-white shrink-0 lg:h-full lg:overflow-y-auto"
			:style="isDesktop ? { width: leftPanelWidth + 'px' } : null"
		>
			<h2 class="font-semibold mb-2 text-ink-gray-9">
				{{ __('Problem Statement') }}
			</h2>
			<MathContent
				:html="exercise.doc?.problem_statement"
				class="ProseMirror prose prose-table:table-fixed prose-td:p-2 prose-th:p-2 prose-td:border prose-th:border prose-td:border-outline-gray-2 prose-th:border-outline-gray-2 prose-td:relative prose-th:relative prose-th:bg-surface-gray-2 prose-sm max-w-none !whitespace-normal"
			/>
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

		<!-- Resizable divider between the problem-statement pane and the editor pane -->
		<div
			v-if="isDesktop"
			class="programming-resizer resizer-vertical"
			:class="{ dragging: horizontalDragging }"
			@mousedown.prevent="startHorizontalResize"
			role="separator"
			aria-orientation="vertical"
			aria-label="Resize panes"
		></div>

		<div ref="rightColumn" class="flex min-h-0 flex-col flex-1">
			<div ref="rightHeader" class="flex items-center justify-between p-3 bg-surface-white border-b shrink-0">
				<FormControl
					v-model="selectedLanguage"
					data-testid="submission-language"
					type="select"
					:options="codeLanguageOptions"
					:disabled="running || submitting"
					class="w-32"
				/>
				<div class="flex items-center gap-x-2">
					<Badge
						v-if="submission.doc?.status"
						:theme="submission.doc.status == 'Passed' ? 'green' : 'gray'"
					>
						{{ submission.doc.status }}
					</Badge>
					<Button
						v-if="submissionID == 'new' || user.data?.name == submission.doc?.owner"
						@click="resetCode"
						:disabled="running || submitting"
						class="text-ink-gray-9"
					>
						<template #prefix>
							<span class="lucide-rotate-ccw size-3" />
						</template>
						{{ __('Reset') }}
					</Button>
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
			<div
				ref="editorPane"
				:class="[
					'flex flex-col overflow-hidden bg-surface-white',
					testPanelCollapsed ? 'flex-1 min-h-0' : 'shrink-0',
				]"
				:style="testPanelCollapsed ? null : { height: editorPaneHeight + 'px' }"
			>
				<div class="flex-1 min-h-0 p-4 editor-fill">
					<CodeEditor
						v-model="code"
						:type="editorLanguage"
						:show-line-numbers="true"
						fill
					/>
				</div>
			</div>

			<!-- Resizable divider between the editor pane and the test-results pane -->
			<div
				v-if="!testPanelCollapsed"
				class="programming-resizer resizer-horizontal"
				:class="{ dragging: verticalDragging }"
				@mousedown.prevent="startVerticalResize"
				role="separator"
				aria-orientation="horizontal"
				aria-label="Resize editor and test results"
			></div>

			<div
				ref="testCaseSection"
				:class="[
					'bg-surface-white',
					testPanelCollapsed ? 'shrink-0' : 'min-h-0 flex-1 overflow-y-auto',
				]"
			>
				<div class="flex items-center gap-6 border-b px-5">
					<button class="test-panel-tab" :class="{ 'test-panel-tab-active': activeTestPanel === 'cases' }" @click="activeTestPanel = 'cases'"><span class="lucide-list-checks size-4" />{{ __('Test Cases') }}</button>
					<button class="test-panel-tab" :class="{ 'test-panel-tab-active': activeTestPanel === 'results' }" @click="activeTestPanel = 'results'"><span class="lucide-terminal size-4" />{{ __('测试结果') }}</button>
					<button
						class="test-panel-collapse ms-auto"
						:class="{ 'test-panel-collapse-active': testPanelCollapsed }"
						:aria-expanded="!testPanelCollapsed"
						:aria-label="testPanelCollapsed ? __('展开测试结果') : __('折叠测试结果')"
						:title="testPanelCollapsed ? __('展开测试结果') : __('折叠测试结果')"
						@click="toggleTestPanel"
					>
						<span
							:class="[
								testPanelCollapsed ? 'lucide-chevrons-up' : 'lucide-chevrons-down',
								'size-4',
							]"
						/>
					</button>
				</div>
				<template v-if="!testPanelCollapsed">
					<div v-if="activeTestPanel === 'cases'" class="p-5">
					<div v-if="exercise.doc?.test_cases?.length" class="divide-y">
						<div v-for="(testCase, index) in exercise.doc.test_cases" :key="testCase.name || index" class="py-3 first:pt-0">
							<div class="font-medium text-ink-gray-9">{{ __('Test {0}').format(index + 1) }}</div>
							<div class="mt-2 grid gap-3 sm:grid-cols-2 text-sm"><div><span class="text-ink-gray-6">{{ __('Input') }}:</span><pre class="test-case-value">{{ testCase.input || '—' }}</pre></div><div><span class="text-ink-gray-6">{{ __('Expected Output') }}:</span><pre class="test-case-value">{{ testCase.expected_output }}</pre></div></div>
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
								{{ testCase.hidden ? __('Failed hidden test') : __('Test {0}').format(index + 1) }} -
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
								<pre class="test-case-value">{{ testCase.input }}</pre>
							</div>
							<div class="space-y-2">
								<div class="text-xs text-ink-gray-7">
									{{ __('Your Output') }}
								</div>
								<div class="text-ink-gray-9 whitespace-pre-wrap">
									{{ testCase.output || '—' }}
								</div>
							</div>
							<div class="space-y-2">
								<div class="text-xs text-ink-gray-7">
									{{ __('Expected Output') }}
								</div>
								<pre class="test-case-value">{{ testCase.expected_output }}</pre>
							</div>
						</div>
					</div>
				</div>
				<div v-else class="text-sm text-ink-gray-6 mt-4">
					{{ __('Run or submit your code to view the test results.') }}
				</div>
				</div>
				</template>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import MathContent from '@/components/MathContent.vue'
import {
	Badge,
	Button,
	call,
	FormControl,
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
import { useScreenSize } from '@/utils/composables'

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
const selectedLanguage = ref<'Python' | 'C++'>('Python')
const codeLanguageOptions = [
	{ label: 'Python', value: 'Python' },
	{ label: 'C++', value: 'C++' },
]
const output = ref<string | null>(null)
const error = ref<boolean | null>(null)
const errorMessage = ref<string | null>(null)
const testCaseSection = ref<HTMLElement | null>(null)
const testCases = ref<TestCase[]>([])
const activeTestPanel = ref<'cases' | 'results'>('cases')
const testPanelCollapsed = ref(false)
const resultMessage = ref<{ tone: 'success' | 'error' | 'info'; title: string; detail?: string | null } | null>(null)
const { brand } = sessionStore()
const { settings } = useSettings()
const router = useRouter()
const fromLesson = ref(false)
const falconURL = ref<string>('https://falcon.frappe.io')
const falconError = ref<string | null>(null)
const running = ref<boolean>(false)
const submitting = ref<boolean>(false)
let statusTimer: ReturnType<typeof setTimeout> | null = null

// Resizable panes: the divider between the problem-statement pane and the
// editor pane (horizontal split), and the divider between the editor pane and
// the test-results pane (vertical split). Both share the same drag mechanics —
// a flagged state that tracks the drag, plus a mousemove/mouseup pair bound to
// the document so the drag keeps tracking even when the pointer leaves the thin
// divider. Sizes are clamped so no pane collapses below a usable minimum.
const { size } = useScreenSize()
const isDesktop = computed(() => size.width >= 1024)

const workspace = ref<HTMLElement | null>(null)
const rightColumn = ref<HTMLElement | null>(null)
const rightHeader = ref<HTMLElement | null>(null)
const editorPane = ref<HTMLElement | null>(null)

const leftPanelWidth = ref(480)
const editorPaneHeight = ref(420)
const horizontalDragging = ref(false)
const verticalDragging = ref(false)

const LEFT_PANE_MIN = 320
const RIGHT_PANE_MIN = 480
const EDITOR_PANE_MIN = 120
const TEST_RESULTS_PANE_MIN = 160
const RESIZER_THICKNESS = 6

const clamp = (value: number, min: number, max: number) =>
	Math.min(Math.max(value, min), max)

const headerHeight = () => rightHeader.value?.offsetHeight || 0

const maxEditorHeight = () => {
	if (!rightColumn.value) return EDITOR_PANE_MIN
	return Math.max(
		EDITOR_PANE_MIN,
		rightColumn.value.clientHeight -
			headerHeight() -
			TEST_RESULTS_PANE_MIN -
			RESIZER_THICKNESS
	)
}

const setInitialLayout = () => {
	if (workspace.value) {
		const maxLeft = workspace.value.clientWidth - RIGHT_PANE_MIN
		leftPanelWidth.value = clamp(
			Math.round(workspace.value.clientWidth * 0.42),
			LEFT_PANE_MIN,
			Math.max(LEFT_PANE_MIN, maxLeft)
		)
	}
	if (rightColumn.value) {
		const computed = Math.round(maxEditorHeight() * 0.55)
		editorPaneHeight.value = clamp(computed, EDITOR_PANE_MIN, maxEditorHeight())
	}
}

const reflowPanes = () => {
	if (!isDesktop.value) return
	if (workspace.value) {
		const maxLeft = workspace.value.clientWidth - RIGHT_PANE_MIN
		leftPanelWidth.value = clamp(
			leftPanelWidth.value,
			LEFT_PANE_MIN,
			Math.max(LEFT_PANE_MIN, maxLeft)
		)
	}
	if (rightColumn.value) {
		editorPaneHeight.value = clamp(
			editorPaneHeight.value,
			EDITOR_PANE_MIN,
			maxEditorHeight()
		)
	}
}

const startHorizontalResize = (event: MouseEvent) => {
	if (!workspace.value || !isDesktop.value) return
	horizontalDragging.value = true
	const startX = event.clientX
	const startWidth = leftPanelWidth.value
	const maxLeft = workspace.value.clientWidth - RIGHT_PANE_MIN

	const onMove = (e: MouseEvent) => {
		leftPanelWidth.value = clamp(
			startWidth + (e.clientX - startX),
			LEFT_PANE_MIN,
			Math.max(LEFT_PANE_MIN, maxLeft)
		)
	}
	const onUp = () => {
		horizontalDragging.value = false
		document.removeEventListener('mousemove', onMove)
		document.removeEventListener('mouseup', onUp)
	}
	document.addEventListener('mousemove', onMove)
	document.addEventListener('mouseup', onUp)
}

const startVerticalResize = (event: MouseEvent) => {
	if (!rightColumn.value) return
	verticalDragging.value = true
	const startY = event.clientY
	const startHeight = editorPaneHeight.value
	const maxHeight = maxEditorHeight()

	const onMove = (e: MouseEvent) => {
		editorPaneHeight.value = clamp(
			startHeight + (e.clientY - startY),
			EDITOR_PANE_MIN,
			maxHeight
		)
	}
	const onUp = () => {
		verticalDragging.value = false
		document.removeEventListener('mousemove', onMove)
		document.removeEventListener('mouseup', onUp)
	}
	document.addEventListener('mousemove', onMove)
	document.addEventListener('mouseup', onUp)
}

// Collapse/expand the test-results pane. When collapsed it becomes a thin bar
// (the tab header) at the bottom of the editor column and the code editor fills
// the freed space; clicking the toggle again expands it back.
const toggleTestPanel = () => {
	testPanelCollapsed.value = !testPanelCollapsed.value
}

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
	setInitialLayout()
	window.addEventListener('resize', reflowPanes)
})

onBeforeUnmount(() => {
	if (statusTimer) clearTimeout(statusTimer)
	window.removeEventListener('resize', reflowPanes)
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

const editorLanguage = computed<'Python' | 'C++'>(() => selectedLanguage.value)

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

const starterCode = computed(() => {
	if (selectedLanguage.value === 'C++') {
		return `#include <bits/stdc++.h>
using namespace std;
int main() {


	return 0;
}`
	}
	return `import sys


def solve() -> None:
	data = sys.stdin.read().strip()
	# Write your solution here.


if __name__ == "__main__":
	solve()
`
})

const updateCode = () => {
	// A new C++ exercise starts from the minimal template. Once a member has
	// run or submitted code, load that saved source instead.
	code.value = loadedSubmissionCode.value || starterCode.value
}

watch(() => exercise.doc, updateCode)

// For an unanswered exercise, changing the language must start from that
// language's template instead of retaining source written for another runtime.
// Saved submissions remain authoritative and are restored unchanged.
watch(selectedLanguage, () => {
	if (!loadedSubmissionCode.value) code.value = starterCode.value
})

// Reset the editor to its language starter template and clear any run output.
const resetCode = () => {
	loadedSubmissionCode.value = ''
	code.value = starterCode.value
	output.value = null
	error.value = null
	errorMessage.value = null
	resultMessage.value = null
	testCases.value = []
	activeTestPanel.value = 'cases'
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
			if (doc.language === 'Python' || doc.language === 'C++') selectedLanguage.value = doc.language
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
			await saveJudgeRunCode()
		} else {
			await runCode()
			await createSubmission()
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
		language: selectedLanguage.value,
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
	// A previous public run may have populated this panel. Clear it so the
	// revealed failed hidden case from this submission can replace it.
	testCases.value = []
	const data = await call('lms.lms.judge_service.submit_programming_exercise', {
		exercise: props.exerciseID,
		submission: props.submissionID,
		code: code.value || '',
		language: selectedLanguage.value,
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

// A public Judge Service run is not sent to the judge queue, but it should
// still retain the member's source just like the local runner does.
const saveJudgeRunCode = async () => {
	const data = await call('lms.lms.api.save_programming_exercise_code', {
		exercise: props.exerciseID,
		submission: props.submissionID,
		code: code.value || '',
		language: selectedLanguage.value,
	})
	const submissionName = data as string
	if (props.submissionID === 'new') {
		await router.push({
			name: 'ProgrammingExerciseSubmission',
			params: { exerciseID: props.exerciseID, submissionID: submissionName },
		})
	}
	fetchSubmission(submissionName)
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

const createSubmission = async () => {
	if (!testCases.value.length) return
	try {
		const data = await call('lms.lms.api.create_programming_exercise_submission', {
			exercise: props.exerciseID,
			submission: props.submissionID,
			code: code.value || '',
			language: selectedLanguage.value,
			test_cases: testCases.value,
		})
		if (props.submissionID == 'new') {
			await router.push({
				name: 'ProgrammingExerciseSubmission',
				params: { exerciseID: props.exerciseID, submissionID: data },
			})
			fetchSubmission(data)
		} else {
			fetchSubmission(props.submissionID)
		}
		showTestCaseSummary()
	} catch (error: any) {
		console.error('Error creating submission:', error)
		showResult('error', __('Unable to submit code'), String(error))
		throw error
	}
}
const execute = (stdin = ''): Promise<string> => {
	return new Promise((resolve, reject) => {
		let outputChunks: string[] = []
		let finalOutput: string | null = null
		let hasExited = false

		const messageText = (value: unknown): string => {
			if (typeof value === 'string') return value
			if (value && typeof value === 'object' && 'text' in value) {
				return String((value as { text: unknown }).text ?? '')
			}
			return value == null ? '' : String(value)
		}

		let session = new LiveCodeSession({
			base_url: falconURL.value,
			runtime: selectedLanguage.value.toLowerCase(),
			code: code.value,
			files: [{ filename: 'stdin', contents: stdin }],
			onMessage: (msg: any) => {
				const stream = msg.file || msg.stream || msg.channel
				if (msg.msgtype === 'stdout' || (msg.msgtype === 'write' && stream === 'stdout')) {
					outputChunks.push(messageText(msg.data ?? msg.output))
				}
				if (typeof msg.stdout !== 'undefined') finalOutput = messageText(msg.stdout)

				if (msg.msgtype === 'stderr' || (msg.msgtype === 'write' && stream === 'stderr')) {
					errorMessage.value = messageText(msg.data ?? msg.output)
				}

				if (msg.msgtype === 'exitstatus') {
					hasExited = true
					error.value = msg.exitstatus !== 0
					resolve((finalOutput ?? outputChunks.join('')).trim())
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

/* Resizable panes. A thin divider sits between the panes; hovering or dragging
   it reveals a blue indicator (a full-length line plus a light blue tint) so the
   user knows the boundary can be dragged to resize each region. */
.programming-workspace.resizing {
	user-select: none;
}
.programming-resizer {
	position: relative;
	flex-shrink: 0;
	display: flex;
	align-items: center;
	justify-content: center;
	background: theme('colors.gray.200');
	z-index: 20;
	user-select: none;
	touch-action: none;
	transition: background 0.15s ease;
}
.programming-resizer:hover,
.programming-resizer.dragging {
	background: theme('colors.blue.100');
}
.resizer-vertical {
	width: 6px;
	cursor: col-resize;
}
.resizer-horizontal {
	height: 6px;
	cursor: row-resize;
}
.resizer-vertical::before,
.resizer-horizontal::before {
	content: '';
	position: absolute;
	background: transparent;
	transition: background 0.15s ease;
}
.resizer-vertical::before {
	top: 0;
	bottom: 0;
	left: 50%;
	width: 2px;
	transform: translateX(-50%);
}
.resizer-horizontal::before {
	left: 0;
	right: 0;
	top: 50%;
	height: 2px;
	transform: translateY(-50%);
}
.programming-resizer:hover::before,
.programming-resizer.dragging::before {
	background: theme('colors.blue.500');
}

/* Make the code editor fill the resizable editor pane so the divider drag
   genuinely changes how much vertical space the editor (and the test-results
   pane below it) gets. The pane's height changes when the splitter is dragged
   or the test-results panel is collapsed, and the editor must track it —
   without this the editor keeps its own height and leaves a gap under it.
   The wrapper is a flex column; the CodeEditor is given `fill` so it grows to
   fill it, and the CodeEditor observes its container and reflows on resize. */
.editor-fill {
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

/* Collapse/expand toggle for the test-results panel, sitting at the right end
   of the tab header. When the panel is collapsed it keeps just this header as a
   thin bar at the bottom; the chevron flips to signal the next action. */
.test-panel-collapse {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	padding: 0.375rem 0.5rem;
	border-radius: 0.375rem;
	color: theme('colors.gray.600');
	transition: color 0.15s ease, background 0.15s ease;
}
.test-panel-collapse:hover {
	color: theme('colors.gray.900');
	background: theme('colors.gray.100');
}
.test-panel-collapse-active {
	color: theme('colors.gray.900');
}
</style>
