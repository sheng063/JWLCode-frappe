<template>
	<PageHeader v-if="!fromLesson" :breadcrumbs="breadcrumbs" :full-breadcrumbs="testingExercise" class="z-30" />
	<div v-if="exerciseLoadError" role="alert" class="shrink-0 bg-surface-red-1 p-3 text-ink-red-3">{{ exerciseLoadError }}</div>
	<div
		v-if="falconError && exercise.doc?.evaluation_mode !== 'Judge Service'"
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
		class="programming-workspace flex flex-col md:flex-row h-[calc(100vh_-_3rem)] bg-surface-gray-1"
		:class="{ resizing: horizontalDragging || verticalDragging, 'lesson-workspace': fromLesson, 'expand-problem': expandedPane === 'problem', 'expand-code': expandedPane === 'code' }"
	>
		<div
			class="problem-pane bg-surface-white shrink-0"
			:style="isDesktop ? { width: leftPanelWidth + 'px' } : null"
		>
			<div class="workspace-panel-heading problem-tabs">
				<button class="problem-tab" :class="{ active: activeProblemTab === 'description' && !activeSubmission }" :aria-pressed="activeProblemTab === 'description' && !activeSubmission" @click="selectProblemTab('description')"><span class="lucide-file-text size-4 text-blue-500" />{{ __('题目描述') }}</button>
                <template v-for="name in submissionTabs" :key="name">
                    <span class="tab-divider" aria-hidden="true">｜</span>
                    <div class="submission-tab">
                        <button class="problem-tab" :class="{ active: activeSubmission === name }" :aria-pressed="activeSubmission === name" @click="activeSubmission = name"><span class="lucide-history size-4 text-blue-500" />{{ submissionStatusLabels[submissionStatuses[name]] || submissionStatuses[name] || '加载中' }}</button>
                        <button class="pane-icon" :aria-label="'关闭提交记录 ' + name" @click="closeSubmission(name)">×</button>
                    </div>
                </template>
                <span class="tab-divider" aria-hidden="true">｜</span>
				<button class="problem-tab" :class="{ active: activeProblemTab === 'submissions' && !activeSubmission }" :aria-pressed="activeProblemTab === 'submissions' && !activeSubmission" @click="selectProblemTab('submissions')"><span class="lucide-history size-4 text-blue-500" />{{ __('提交记录') }}</button>
				<button class="pane-icon ms-auto" :aria-label="__('展开题目描述')" :aria-pressed="expandedPane === 'problem'" @click="togglePane('problem')"><span :class="expandedPane === 'problem' ? 'lucide-minimize size-4' : 'lucide-maximize size-4'" /></button>
			</div>
			<ProgrammingSubmissionHistory v-if="activeProblemTab === 'submissions' && !activeSubmission" :exercise="exerciseID" :member="user.data?.name" :revision="submission.doc?.modified" @select="openSubmission" />
			<ProgrammingSubmissionDetail v-for="name in submissionTabs" v-show="activeSubmission === name" :key="name" :name="name" :revision="submission.doc?.modified" @restore="restoreSubmissionCode" @loaded="updateSubmissionStatus" />
			<div v-show="activeProblemTab === 'description' && !activeSubmission" class="problem-content">
			<div class="flex items-start justify-between gap-4 mb-5">
				<h1 class="problem-title">{{ exercise.doc?.title || __('Problem Statement') }}</h1>
				<span v-if="isSolved" class="solved-label"><span class="lucide-circle-check size-4" />{{ __('已解答') }}</span>
			</div>
			<ProgrammingStatement
				:html="exercise.doc?.problem_statement"
				:icpc="exercise.doc?.source_type === 'icpc'"
				class="ProseMirror prose prose-table:table-fixed prose-td:p-2 prose-th:p-2 prose-td:border prose-th:border prose-td:border-outline-gray-2 prose-th:border-outline-gray-2 prose-td:relative prose-th:relative prose-th:bg-surface-gray-2 prose-sm max-w-none !whitespace-normal"
			/>
			</div>
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

		<div ref="rightColumn" class="code-column flex min-h-0 min-w-0 flex-col flex-1">
			<div ref="rightHeader" class="code-header bg-surface-white shrink-0">
				<div class="workspace-panel-heading"><span class="lucide-code-xml size-4 text-green-500" />{{ __('代码') }}
					<button class="pane-icon ms-auto" aria-label="代码格式化" title="代码格式化 (Alt+Shift+F)" :disabled="formatting || running || submitting" @click="formatCode"><span :class="formatting ? 'lucide-loader-circle size-4 animate-spin' : 'lucide-braces size-4'" /></button>
                    <button class="pane-icon" aria-label="编辑器设置" title="设置" @click="editorSettingsOpen = true"><span class="lucide-settings size-4" /></button>
                    <button class="pane-icon" :aria-label="__('展开代码编辑器')" :aria-pressed="expandedPane === 'code'" @click="togglePane('code')"><span :class="expandedPane === 'code' ? 'lucide-minimize size-4' : 'lucide-maximize size-4'" /></button>
				</div>
				<div class="code-toolbar">
				<div class="language-control">
				<FormControl
					v-model="selectedLanguage"
					@update:model-value="saveProgrammingLanguage"
					data-testid="submission-language"
					type="select"
					:options="codeLanguageOptions"
					:disabled="running || submitting"
					class="w-32"
				/>
				</div>
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
						:disabled="running || submitting || !!exerciseLoadError || !exercise.doc?.test_cases?.length"
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
						:disabled="running || submitting || !!exerciseLoadError || !exercise.doc"
						class="!text-green-700 !bg-green-50 hover:!bg-green-100"
					>
						<template #prefix>
							<span class="lucide-send size-3" />
						</template>
						{{ submitting ? __('Submitting') : __('Submit') }}
					</Button>
				</div>
			</div>
			</div>
			<div
				ref="editorPane"
				:class="[
					'code-pane flex flex-col overflow-hidden bg-surface-white',
					testPanelCollapsed ? 'flex-1 min-h-0' : 'shrink-0',
				]"
				:style="testPanelCollapsed ? null : { height: editorPaneHeight + 'px' }"
			>
				<div class="flex-1 min-h-0 editor-fill" :style="{ backgroundColor: editorPreferences.theme === 'dark' ? '#141414' : '#fff' }">
					<CodeEditor
                        ref="codeEditor"
                        :preferences="editorPreferences"
						v-model="code"
						:type="editorLanguage"
						:show-line-numbers="true"
						:font-size="14"
						@cursor-change="editorCursor = $event"
						fill
					/>
				</div>
				<div class="editor-status"><span>{{ selectedLanguage }}</span><span>{{ __('行 {0}，列 {1}').format(editorCursor.row, editorCursor.column) }}</span></div>
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
					'test-pane bg-surface-white',
					testPanelCollapsed ? 'shrink-0' : 'min-h-0 flex-1 overflow-y-auto',
				]"
			>
				<div class="test-panel-heading flex items-center gap-6 px-4">
					<button class="test-panel-tab" :class="{ 'test-panel-tab-active': activeTestPanel === 'cases' }" @click="selectTestPanel('cases')"><span class="lucide-list-checks size-4" />{{ __('Test Cases') }}</button>
					<button class="test-panel-tab" :class="{ 'test-panel-tab-active': activeTestPanel === 'results' }" @click="selectTestPanel('results')"><span class="lucide-terminal size-4" />{{ __('测试结果') }}</button>
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
					<div v-if="exercise.doc?.test_cases?.length">
						<div class="case-tabs" aria-label="测试用例">
							<button v-for="(testCase, index) in exercise.doc.test_cases" :key="testCase.name || index" class="case-tab" :class="{ 'case-tab-active': selectedCaseIndex === index }" :aria-pressed="selectedCaseIndex === index" @click="selectedCaseIndex = index">
								<span v-if="publicCasePassed(index)" class="lucide-square-check case-passed-icon" role="img" aria-label="已通过" />
								用例 {{ index + 1 }}
							</button>
						</div>
						<div v-if="selectedCase" class="case-fields">
							<div><div class="case-field-label">{{ __('输入') }}</div><pre class="test-case-value">{{ selectedCase.input || '—' }}</pre></div>
							<div><div class="case-field-label">{{ __('样例输出') }}</div><pre class="test-case-value">{{ selectedCase.expected_output }}</pre></div>
						</div>
					</div>
					<div v-else class="text-sm text-ink-gray-6">{{ __('暂无测试用例。') }}</div>
				</div>
				<div v-else class="p-5">
					<div v-if="resultMessage" class="result-notice mb-5" :class="`result-notice-${resultMessage.tone}`"><div class="font-semibold">{{ resultMessage.title }}</div><div v-if="resultMessage.detail" class="mt-2 whitespace-pre-wrap font-mono text-sm">{{ resultMessage.detail }}</div></div>
					<ProgrammingErrorDiagnostic v-if="error" :message="errorMessage" :code="executedCode" />
					<div v-if="testCases.length" class="test-results">
					<div class="case-tabs" aria-label="测试结果用例">
						<button v-for="(result, index) in testCases" :key="index" class="case-tab" :class="{ 'case-tab-active': selectedResultIndex === index }" :aria-pressed="selectedResultIndex === index" @click="selectedResultIndex = index">
							<span v-if="!result.hidden && result.status === 'Passed'" class="lucide-square-check case-passed-icon" role="img" aria-label="已通过" />
							{{ result.hidden ? __('失败用例') : __('用例 {0}').format(index + 1) }}
						</button>
					</div>
					<div v-if="selectedTestResult">
						<div class="flex items-center mb-3">
							<span class="text-ink-gray-9">
								{{ selectedTestResult.hidden ? __('失败用例') : __('测试用例 {0}').format(selectedResultIndex + 1) }} -
							</span>
							<span
								class="font-semibold ms-2 me-1"
								:class="
									selectedTestResult.status === 'Passed'
										? 'text-ink-green-3'
										: 'text-ink-red-3'
								"
							>
								{{ submissionStatusLabel(selectedTestResult.status) }}
							</span>
						</div>
						<div class="case-fields test-result-fields">
							<div v-if="selectedTestResult.input != null" class="space-y-2">
								<div class="text-xs text-ink-gray-7">
									{{ __('输入') }}
								</div>
								<pre class="test-case-value">{{ selectedTestResult.input }}</pre>
							</div>
							<div class="space-y-2">
								<div class="text-xs text-ink-gray-7">
									{{ __('我的输出') }}
								</div>
								<pre class="test-case-value">{{ selectedTestResult.output || '—' }}</pre>
							</div>
							<div class="space-y-2">
								<div class="text-xs text-ink-gray-7">
									{{ __('样例输出') }}
								</div>
								<pre class="test-case-value">{{ selectedTestResult.expected_output }}</pre>
							</div>
						</div>
					</div>
				</div>
				<div v-else-if="!resultMessage" class="text-sm text-ink-gray-6 mt-4">
					{{ __('运行或提交代码以查看测试结果。') }}
				</div>
				</div>
				</template>
			</div>
		</div>
	</div>
<ProgrammingEditorSettings v-model="editorPreferences" v-model:open="editorSettingsOpen" />
</template>
<script setup lang="ts">
import ProgrammingStatement from '@/components/ProgrammingStatement.vue'
import ProgrammingErrorDiagnostic from '@/components/ProgrammingErrorDiagnostic.vue'
import { submissionStatusLabel, submissionStatusLabels } from '@/utils/programmingSubmissionStatus'
import ProgrammingSubmissionDetail from '@/components/ProgrammingSubmissionDetail.vue'
import ProgrammingSubmissionHistory from '@/components/ProgrammingSubmissionHistory.vue'
import {
	Badge,
	Button,
	call,
	FormControl,
	createDocumentResource,
	toast,
	usePageMeta,
} from 'frappe-ui'
import { computed, inject, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import PageHeader from '@/components/Layouts/PageHeader.vue'
import CodeEditor from '@/components/Controls/CodeEditor.vue'
import { sessionStore } from '@/stores/session'
import { useRoute, useRouter } from 'vue-router'
import ProgrammingEditorSettings from '@/components/ProgrammingEditorSettings.vue'
import { readEditorPreferences, editorPreferencesKey } from '@/utils/editorPreferences'
import { readProgrammingCode, saveProgrammingCode } from '@/utils/programmingCodeCache'
import { readProgrammingLanguage, saveProgrammingLanguage } from '@/utils/programmingLanguagePreference'
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
const submissionTabs = ref<string[]>([])
const activeSubmission = ref('')
const submissionStatuses = ref<Record<string, string>>({})
function selectProblemTab(tab: 'description' | 'submissions') {
 activeSubmission.value = ''
 activeProblemTab.value = tab
}
function updateSubmissionStatus(doc: any) {
 if (doc.exercise !== props.exerciseID || !submissionTabs.value.includes(doc.name)) return
 submissionStatuses.value[doc.name] = doc.status
}
function openSubmission(name: string) {
 if (!submissionTabs.value.includes(name)) submissionTabs.value.push(name)
 activeSubmission.value = name
 if (expandedPane.value === 'code') expandedPane.value = null
}
function closeSubmission(name: string) {
 submissionTabs.value = submissionTabs.value.filter(item => item !== name)
 if (activeSubmission.value === name) activeSubmission.value = ''
}
async function restoreSubmissionCode(doc: any) {
 selectedLanguage.value = doc.language
 await nextTick()
 code.value = doc.code ?? ''
 if (expandedPane.value === 'problem') expandedPane.value = null
 activeSubmission.value = ''
 activeProblemTab.value = 'description'
}
const activeProblemTab = ref<'description' | 'submissions'>('description')
const code = ref<string | null>('')
const codeEditor = ref<InstanceType<typeof CodeEditor> | null>(null)
const editorSettingsOpen = ref(false)
const editorPreferences = ref(readEditorPreferences())
const formatting = ref(false)
watch(editorPreferences, (value) => {
 try { localStorage.setItem(editorPreferencesKey, JSON.stringify(value)) } catch { /* Private browsing may disable storage. */ }
}, { deep: true })
const formatCode = async () => {
 if (formatting.value || running.value || submitting.value) return
 const source = codeEditor.value?.getValue() ?? code.value ?? ''
 const language = selectedLanguage.value
 formatting.value = true
 try {
  const formatted = await call('lms.lms.programming_editor.format_code', {
   code: source, language, tab_size: editorPreferences.value.tabSize,
  })
  if (selectedLanguage.value !== language || codeEditor.value?.getValue() !== source) {
   toast.info('代码已修改，请重新格式化。')
   return
  }
  codeEditor.value?.replaceCode(formatted)
 } catch (error: any) {
  toast.error(error.messages?.[0] || error.message || '代码格式化失败，请检查语法后重试。')
 } finally { formatting.value = false }
}
const handleEditorShortcut = (event: KeyboardEvent) => {
 if (event.isComposing || event.repeat || editorSettingsOpen.value) return
 const modifier = event.ctrlKey || event.metaKey
 const format = event.altKey && event.shiftKey && event.code === 'KeyF'
 const expand = event.altKey && !event.shiftKey && event.code === 'KeyF'
 const submit = modifier && event.shiftKey && event.key === 'Enter' && editorPreferences.value.submitShortcut
 const run = modifier && !event.shiftKey && event.key === 'Enter' && editorPreferences.value.runShortcut
 if (!format && !expand && !submit && !run) return
 event.preventDefault()
 event.stopPropagation()
 if (expand) { togglePane('code'); return }
 if (format) { void formatCode(); return }
 if (running.value || submitting.value || formatting.value || !exercise.doc) return
 if (props.submissionID !== 'new' && submission.doc?.owner !== user.data?.name) return
 if (exercise.doc.evaluation_mode !== 'Judge Service' && falconError.value) return
 if (submit) void submitCode()
 else if (exercise.doc.test_cases?.length) void runCodeOnly()
}

const expandedPane = ref<'problem' | 'code' | null>(null)
const editorCursor = ref({ row: 1, column: 1 })
const togglePane = (pane: 'problem' | 'code') => {
	expandedPane.value = expandedPane.value === pane ? null : pane
}
const selectedLanguage = ref(readProgrammingLanguage())
const codeLanguageOptions = [
	{ label: 'Python', value: 'Python' },
	{ label: 'C++', value: 'C++' },
]
const output = ref<string | null>(null)
const error = ref<boolean | null>(null)
const errorMessage = ref<string | null>(null)
const executedCode = ref('')
const testCaseSection = ref<HTMLElement | null>(null)
const testCases = ref<TestCase[]>([])
const activeTestPanel = ref<'cases' | 'results'>('cases')
const testPanelCollapsed = ref(false)
const selectedCaseIndex = ref(0)
const selectedResultIndex = ref(0)
const selectedTestResult = computed(() => testCases.value[selectedResultIndex.value])
watch(testCases, () => { selectedResultIndex.value = 0 })
const publicCasePassed = (index: number) => {
	const result = testCases.value[index]
	const sample = exercise.doc?.test_cases?.[index]
	return result?.status === 'Passed' && !result.hidden && sample
		&& (result.input || '') === (sample.input || '')
		&& result.expected_output === sample.expected_output
}
const selectTestPanel = (panel: 'cases' | 'results') => {
	activeTestPanel.value = panel
	testPanelCollapsed.value = false
}
const resultMessage = ref<{ tone: 'success' | 'error' | 'info'; title: string; detail?: string | null } | null>(null)
const { brand } = sessionStore()
const { settings } = useSettings()
const router = useRouter()
const route = useRoute()
const testingExercise = computed(() => route.query.testExercise === '1')
const fromLesson = ref(new URLSearchParams(window.location.search).has('fromLesson'))
const falconURL = ref<string>('https://falcon.frappe.io')
const falconError = ref<string | null>(null)
const running = ref<boolean>(false)
const submitting = ref<boolean>(false)
let workspaceObserver: ResizeObserver | null = null
let statusTimer: ReturnType<typeof setTimeout> | null = null

// Resizable panes: the divider between the problem-statement pane and the
// editor pane (horizontal split), and the divider between the editor pane and
// the test-results pane (vertical split). Both share the same drag mechanics —
// a flagged state that tracks the drag, plus a mousemove/mouseup pair bound to
// the document so the drag keeps tracking even when the pointer leaves the thin
// divider. Sizes are clamped so no pane collapses below a usable minimum.
const { size } = useScreenSize()
const isDesktop = computed(() => size.width >= 768)

const workspace = ref<HTMLElement | null>(null)
const rightColumn = ref<HTMLElement | null>(null)
const rightHeader = ref<HTMLElement | null>(null)
const editorPane = ref<HTMLElement | null>(null)

const leftPanelWidth = ref(480)
const editorPaneHeight = ref(420)
const horizontalDragging = ref(false)
const verticalDragging = ref(false)

const LEFT_PANE_MIN = 280
const RIGHT_PANE_MIN = 360
const EDITOR_PANE_MIN = 120
const TEST_RESULTS_PANE_MIN = 160
const RESIZER_THICKNESS = 8

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
		const maxLeft = workspace.value.clientWidth - RIGHT_PANE_MIN - RESIZER_THICKNESS - 12
		leftPanelWidth.value = clamp(
			Math.round(workspace.value.clientWidth * 0.42),
			LEFT_PANE_MIN,
			Math.max(LEFT_PANE_MIN, maxLeft)
		)
	}
	if (rightColumn.value) {
		const computed = Math.round((rightColumn.value.clientHeight - headerHeight() - RESIZER_THICKNESS) * 0.55)
		editorPaneHeight.value = clamp(computed, EDITOR_PANE_MIN, maxEditorHeight())
	}
}

const reflowPanes = () => {
	if (workspace.value) {
		const maxLeft = workspace.value.clientWidth - RIGHT_PANE_MIN - RESIZER_THICKNESS - 12
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
	const maxLeft = workspace.value.clientWidth - RIGHT_PANE_MIN - RESIZER_THICKNESS - 12

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
	checkIfUserIsPermitted()
	checkIfInLesson()
	fetchSubmission()
	setInitialLayout()
	workspaceObserver = new ResizeObserver(reflowPanes)
	if (workspace.value) workspaceObserver.observe(workspace.value)
	if (rightColumn.value) workspaceObserver.observe(rightColumn.value)
	window.addEventListener('resize', reflowPanes)
	workspace.value?.addEventListener('keydown', handleEditorShortcut, true)
})

onBeforeUnmount(() => {
	workspaceObserver?.disconnect()
	if (statusTimer) clearTimeout(statusTimer)
	window.removeEventListener('resize', reflowPanes)
	workspace.value?.removeEventListener('keydown', handleEditorShortcut, true)
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

const exerciseLoadError = ref('')
const exercise = createDocumentResource({
	doctype: 'LMS Programming Exercise',
	name: props.exerciseID,
	cache: ['programmingExercise', props.exerciseID],
	auto: true,
	onSuccess() { exerciseLoadError.value = '' },
	onError(error: any) {
		exerciseLoadError.value = error.messages?.[0] || __('Unable to load this exercise. Refresh the lesson or select an existing exercise.')
	},
})

watch(() => exercise.doc?.evaluation_mode, (mode) => {
	if (mode && mode !== 'Judge Service') {
		loadFalcon().catch(() => { falconError.value = '代码运行服务加载失败。' })
	}
}, { immediate: true })

const selectedCase = computed(() => exercise.doc?.test_cases?.[selectedCaseIndex.value])

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

const isSolved = computed(() => {
 const doc = submission.doc
 return Boolean(user.data?.name && doc?.exercise === props.exerciseID &&
  doc?.member === user.data.name && doc?.status === 'Passed')
})
watch(() => [props.exerciseID, user.data?.name], () => {
 submissionTabs.value = []
 submissionStatuses.value = {}
 activeSubmission.value = ''
 activeProblemTab.value = 'description'
})

const loadedSubmissionCode = ref('')
const loadedSubmissionName = ref('')

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

const restoreExerciseCode = () => {
	selectedLanguage.value = readProgrammingLanguage()
	const saved = readProgrammingCode(user.data?.name, props.exerciseID, selectedLanguage.value)
	code.value = saved?.code ?? starterCode.value
}

const updateCode = () => {
	if (loadedSubmissionName.value) {
		code.value = loadedSubmissionCode.value
	} else {
		restoreExerciseCode()
	}
}

// Restore even when the resource was already cached before this page mounted.
watch(() => exercise.doc?.name, updateCode, { immediate: true })
watch(() => user.data?.name, () => {
	if (props.submissionID === 'new') restoreExerciseCode()
})

watch(selectedLanguage, () => {
	const saved = readProgrammingCode(user.data?.name, props.exerciseID, selectedLanguage.value)
	code.value = saved?.language === selectedLanguage.value ? saved.code : starterCode.value
}, { flush: 'sync' })

// Reset the editor to its language starter template and clear any run output.
const resetCode = () => {
	loadedSubmissionCode.value = ''
	loadedSubmissionName.value = ''
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
		if (doc && doc.exercise === props.exerciseID && doc.name === props.submissionID) {
			checkIfUserIsPermitted(doc)
			updateTestCases(doc)
			if (doc.name !== loadedSubmissionName.value) {
				loadedSubmissionName.value = doc.name
				if (doc.language === 'Python' || doc.language === 'C++') selectedLanguage.value = doc.language
				loadedSubmissionCode.value = doc.code || ''
				updateCode()
			}
		}
	},
	{ immediate: true }
)

watch(isSolved, (solved) => {
	if (solved && window.parent !== window && fromLesson.value && !studentView.value) {
		window.parent.postMessage({ type: 'lms-programming-passed' }, window.location.origin)
	}
}, { immediate: true })

// The page is reused when browser history changes only the submission ID.
watch(() => props.submissionID, (name) => {
 if (statusTimer) clearTimeout(statusTimer)
 testCases.value = []
 resultMessage.value = null
 if (name === 'new') {
  submission.doc = null
  loadedSubmissionName.value = ''
  loadedSubmissionCode.value = ''
  updateCode()
 } else {
  fetchSubmission(name)
 }
})

function loadFalcon() {
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
	if (!exercise.doc || exerciseLoadError.value || running.value || submitting.value) return
	code.value = codeEditor.value?.getValue() ?? code.value
	// Persist the exact submitted source before any asynchronous evaluation/navigation.
	saveProgrammingCode(user.data?.name, props.exerciseID, {
		code: code.value ?? '',
		language: selectedLanguage.value,
	})
	submitting.value = true
	executedCode.value = code.value || ''
	error.value = false
	errorMessage.value = null
	resultMessage.value = null
	try {
		if (exercise.doc?.evaluation_mode === 'Judge Service') {
			await createJudgeSubmission()
		} else {
			await runCode()
			await createSubmission()
		}
	} catch (error: any) {
		toast.error(error.messages?.[0] || error.message || '提交失败，请重试。')
	} finally {
		submitting.value = false
	}
}

const runCodeOnly = async () => {
	if (!exercise.doc || exerciseLoadError.value || running.value || submitting.value) return
	code.value = codeEditor.value?.getValue() ?? code.value
	running.value = true
	executedCode.value = code.value || ''
	error.value = false
	errorMessage.value = null
	try {
		if (exercise.doc?.evaluation_mode === 'Judge Service') {
			await runJudgeCode()
			// Public runs do not overwrite historical submissions.
		} else {
			await runCode()
		}
	} catch (e: any) {
		error.value = true
		errorMessage.value = e?.messages?.[0] || e?.message || String(e)
		showResult('error', __('代码运行失败'), errorMessage.value)
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
		showResult('error', submissionStatusLabel(result.status), result.compiler_message)
	}
	testCases.value = (result.cases || []).map((item: any) => {
		const testCase = exercise.doc?.test_cases?.[item.index - 1]
		return {
			input: testCase?.input || '',
			output: item.stdout || '',
			expected_output: testCase?.expected_output || '',
			status: item.status === 'Accepted' ? 'Passed' : item.status,
		}
	})
	if (!result.compiler_message) {
		if (!testCases.value.length || !['ACCEPTED', 'WRONG_ANSWER'].includes(result.status)) {
			const status = result.status
			error.value = true
			errorMessage.value = (result.cases || [])
				.filter((item: any) => item.status !== 'Accepted' && (item.stderr || item.compile_output))
				.map((item: any) => `测试用例 ${item.index}：\n${item.stderr || item.compile_output}`)
				.join('\n\n') || null
			showResult('error', submissionStatusLabel(status), errorMessage.value)
		} else showTestCaseSummary()
	}
}

const createJudgeSubmission = async () => {
	// A previous public run may have populated this panel. Clear it so the
	// revealed failed hidden case from this submission can replace it.
	testCases.value = []
	const data = await call('lms.lms.judge_service.submit_programming_exercise', {
		exercise: props.exerciseID,
		submission: 'new',
		code: code.value || '',
		language: selectedLanguage.value,
		client_request_id: globalThis.crypto?.randomUUID?.() ?? `submission-${Date.now()}-${Math.random().toString(36).slice(2)}`,
	})
	const submissionName = data.submission
	if (submissionName) openSubmission(submissionName)
	fetchSubmission(submissionName)
	pollJudgeStatus(submissionName)
	showResult('info', __('提交已进入队列'), __('代码正在评测中。'))
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
				showResult('error', submissionStatusLabel(result.status), result.compiler_message)
			}
			if (['Queued', 'Compiling', 'Running'].includes(result.status)) {
				pollJudgeStatus(submissionName)
			} else if (!result.compiler_message) {
				error.value = ['Runtime Error', 'Compilation Error'].includes(result.status)
				showResult(result.status === 'Passed' ? 'success' : 'error', submissionStatusLabel(result.status))
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
		errorMessage.value = null
		let result = await execute(test_case.input)
		if (error.value) {
			testCases.value.push({ input: test_case.input, output: result, expected_output: test_case.expected_output, status: 'Failed' })
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
	if (error.value) showResult('error', __('运行出错'), errorMessage.value)
	else showTestCaseSummary()
}

const showTestCaseSummary = () => {
	const passed = testCases.value.filter((testCase) => testCase.status === 'Passed').length
	showResult(passed === testCases.value.length ? 'success' : 'error', passed === testCases.value.length ? __('全部测试通过') : __('部分测试未通过'), __('通过 {0} / {1} 个测试用例。').format(passed, testCases.value.length))
}

const showResult = (tone: 'success' | 'error' | 'info', title: string, detail: string | null = null) => {
	selectTestPanel('results')
	resultMessage.value = { tone, title, detail }
}

const createSubmission = async () => {
	if (!testCases.value.length) return
	try {
		const data = await call('lms.lms.api.create_programming_exercise_submission', {
			exercise: props.exerciseID,
			submission: 'new',
			code: code.value || '',
			language: selectedLanguage.value,
			test_cases: testCases.value,
		})
		if (data) {
			openSubmission(data)
			fetchSubmission(data)
		} else {
			fetchSubmission(props.submissionID)
		}
		if (!error.value) showTestCaseSummary()
	} catch (error: any) {
		console.error('Error creating submission:', error)
		showResult('error', __('代码提交失败'), String(error))
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
					errorMessage.value = (errorMessage.value || '') + messageText(msg.data ?? msg.output)
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
				errorMessage.value = '执行超时。'
				reject('执行超时。')
			}
		}, 20000)
	})
}

const breadcrumbs = computed(() => {
	if (testingExercise.value) return [
		{ label: __('Programming Exercises'), route: { name: 'ProgrammingExercises' } },
		{ label: exercise.doc?.title || props.exerciseID, route: { name: 'ProgrammingExerciseForm', params: { exerciseID: props.exerciseID } } },
		{ label: __('Test this Exercise') },
	]
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
<style scoped>
:deep(.ProseMirror pre) {
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

<style scoped>
.programming-workspace { padding: 6px; background: #f0f0f0; overflow: hidden; box-sizing: border-box; }
.programming-workspace.lesson-workspace { height: 100dvh; }
.problem-pane { background: #fff; display: flex; flex-direction: column; min-height: 0; border: 1px solid #dedede; border-radius: 12px; overflow: hidden; }
.workspace-panel-heading { overflow-x: auto; display: flex; align-items: center; gap: 8px; min-height: 36px; flex-shrink: 0; padding: 0 14px; background: #fafafa; color: #262626; font-size: 14px; font-weight: 600; }
.problem-content { overflow-y: auto; padding: 22px 16px; flex: 1; }
.problem-title { font-size: 24px; font-weight: 650; line-height: 1.4; color: #262626; overflow-wrap: anywhere; }
.tab-divider { flex-shrink: 0; color: var(--outline-gray-3); font-weight: 400; }
.submission-tab { display: flex; align-items: center; flex-shrink: 0; gap: 2px; }
.solved-label { display: inline-flex; align-items: center; gap: 6px; flex-shrink: 0; color: #16a34a; font-size: 13px; padding-top: 8px; }
.problem-content :deep(.prose) { font-size: 14px; line-height: 1.9; }
.problem-content :deep(.prose pre) { white-space: pre-wrap; overflow-wrap: anywhere; }
.code-header { background: #fff; overflow: hidden; border-radius: 12px 12px 0 0; }
.code-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 44px; padding: 6px 12px; border-bottom: 1px solid #ededed; flex-wrap: wrap; }
.code-pane { background: #fff; border-radius: 0 0 12px 12px; }
.editor-fill { padding: 10px 0; }
.editor-fill :deep(.ace_editor) { border: 0; border-radius: 0 !important; line-height: 1.65; box-shadow: none; }
.editor-fill :deep(.ace-chrome .ace_gutter) { background: #fff; color: #77909c; }
.editor-fill :deep(.ace-chrome .ace_marker-layer .ace_active-line) { background: #f7f7f7; }
.test-pane { background: #fff; border-radius: 12px; }
.test-panel-heading { position: sticky; top: 0; background: #fafafa; border-radius: 12px 12px 0 0; z-index: 1; }
.test-panel-tab { border-bottom: 0; min-height: 36px; padding: 10px 0; color: #888; }
.test-panel-tab-active { color: #262626; font-weight: 600; }
.test-panel-tab span { color: #22c55e; }
.case-tabs { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 22px; }
.case-tab { display: inline-flex; align-items: center; gap: 8px; padding: 9px 16px; border-radius: 8px; color: #666; font-size: 14px; font-weight: 500; white-space: nowrap; }
.case-tab:hover, .case-tab-active { background: #f2f2f4; color: #262626; }
.case-fields { display: grid; grid-template-columns: minmax(0, 1fr); gap: 20px; }
.test-result-fields > div { min-width: 0; width: 100%; }
.case-passed-icon { color: #16a34a; font-size: 14px; flex-shrink: 0; }
.case-field-label { color: #888; font-size: 13px; margin-bottom: 9px; }
.test-case-value { min-height: 48px; border-radius: 9px; background: #f3f3f5; padding: 13px 16px; font-size: 14px; line-height: 1.6; }
.programming-resizer { background: transparent; }
.resizer-vertical { width: 8px; }
.resizer-horizontal { height: 8px; }
.resizer-vertical::before { top: calc(50% - 16px); bottom: auto; height: 32px; background: #dcdcdc; border-radius: 2px; }
.resizer-horizontal::before { left: calc(50% - 16px); right: auto; width: 32px; background: #dcdcdc; border-radius: 2px; }
button:focus-visible { outline: 2px solid #3b82f6; outline-offset: 2px; }
@media (max-width: 767px) {
	.programming-workspace, .programming-workspace.lesson-workspace { height: 100dvh; min-height: 0; gap: 8px; }
	.problem-pane { height: 30%; max-height: 30%; min-height: 100px; }
	.code-column { flex: 1; min-height: 0; }
	.problem-content { padding: 20px 16px; }
	.problem-title { font-size: 21px; }
}
[data-theme="dark"] .programming-workspace { background: #171717; }
[data-theme="dark"] .workspace-panel-heading, [data-theme="dark"] .test-panel-heading { background: #242424; color: #eee; }
[data-theme="dark"] .problem-pane, [data-theme="dark"] .code-toolbar { border-color: #383838; }
[data-theme="dark"] .problem-title, [data-theme="dark"] .test-panel-tab-active { color: #eee; }
[data-theme="dark"] .test-case-value, [data-theme="dark"] .case-tab-active, [data-theme="dark"] .case-tab:hover { background: #303030; color: #eee; }
</style>

<style scoped>
.problem-tabs { gap: 0; }
.problem-tab { display: inline-flex; align-items: center; gap: 6px; font-size: 14px; font-weight: 500; color: #888; white-space: nowrap; }
.problem-tab + .problem-tab { margin-left: 10px; padding-left: 10px; border-left: 1px solid #e5e5e5; }
.problem-tab.active { color: #262626; font-weight: 600; }
.pane-icon { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; border-radius: 5px; color: #888; }
.pane-icon:hover { background: #eaeaea; color: #262626; }
.problem-examples { margin-top: 40px; }
.problem-example { padding: 12px 0; }
.example-values { border-left: 2px solid #eee; padding-left: 16px; }
.example-values .test-case-value { padding: 0; background: transparent; border-radius: 0; color: #777; }
.editor-status { display: flex; justify-content: space-between; flex-shrink: 0; padding: 8px 12px; font-size: 12px; color: #aaa; }
.code-toolbar :deep(select) { background-color: transparent; border-color: transparent; box-shadow: none; color: #777; }
.programming-workspace.expand-problem .problem-pane { width: 100% !important; max-height: none; height: 100%; }
.expand-problem .code-column, .expand-problem > .programming-resizer, .expand-code .problem-pane, .expand-code > .programming-resizer { display: none; }
[data-theme="dark"] .problem-tab.active { color: #eee; }
</style>

<style scoped>
.language-control { width: 120px; flex: 0 0 120px; }
[data-theme="dark"] .problem-pane, [data-theme="dark"] .code-header, [data-theme="dark"] .code-pane, [data-theme="dark"] .test-pane { background: #1f1f1f; }

</style>
