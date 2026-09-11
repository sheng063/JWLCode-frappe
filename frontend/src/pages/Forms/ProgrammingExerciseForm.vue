<template>
	<FormShell :title="showPackageImport ? __('Upload problem') : title" size="4xl" @close="showPackageImport ? showPackageImport = false : close()">
		<template #header-action>
			<Badge v-if="exerciseDoc?.doc?.exercise_number">{{ exerciseDoc.doc.exercise_number }}</Badge>
			<Badge v-if="isDirty && canManageExercise" theme="orange">
				{{ __('Not Saved') }}
			</Badge>
		</template>
		<template #default>
			<ProblemPackageImport v-if="showPackageImport && canManageExercise" :exercise="exerciseID" :active-version="exerciseDoc?.doc?.active_package_version" @published="packagePublished" />
			<div v-else-if="!canManageExercise" class="p-4 text-base text-ink-gray-6">
				{{ __('You are not permitted to manage programming exercises.') }}
			</div>
			<div
				v-else
				data-testid="programming-exercise-fields"
				class="grid grid-cols-1 sm:grid-cols-2 gap-10"
			>
				<div class="space-y-4">
					<FormControl
						v-model="exercise.title"
						:label="__('Title')"
						:required="true"
					/>
					<ChildTable
						v-model="testCases.data"
						:label="__('Public samples')"
						:columns="testCaseColumns"
						:multiline="true"
						:required="true"
						:addable="true"
						:deletable="true"
						:editable="true"
						:placeholder="__('Add Test Case')"
					/>

				</div>
				<div>
					<div class="space-y-1.5">
						<InputLabel
							:id="problemStatementLabelId"
							:label="__('Problem Statement')"
							:required="true"
						/>
						<ProgrammingStatementEditor v-model="exercise.problem_statement" :icpc="exerciseDoc?.doc?.source_type === 'icpc'" />
					</div>
				</div>
				<details v-if="exerciseID !== 'new'" class="sm:col-span-2 rounded-md border p-4" data-testid="hidden-test-cases" @toggle="toggleHiddenCases">
					<summary class="cursor-pointer font-medium">{{ __('Hidden Test Cases') }} ({{ hiddenCount }})</summary>
					<div class="mt-4 flex flex-wrap items-center gap-3">
						<a :href="hiddenDownloadUrl" class="rounded border px-3 py-2">{{ __('Download all hidden cases') }}</a>
						<label class="rounded border px-3 py-2 cursor-pointer">
							{{ __('Upload hidden cases') }}
							<input type="file" accept=".zip" :disabled="saving || uploadingHidden" class="block mt-2" @change="uploadHiddenCases" />
						</label>
					</div>
					<p class="mt-2 text-sm text-ink-gray-6">{{ __('Upload a ZIP of paired .in and .ans files. This replaces all existing hidden cases immediately.') }}</p>
					<p v-if="uploadingHidden" role="status">{{ __('Uploading hidden cases') }}</p>
					<p v-if="loadingHiddenPreview" role="status">{{ __('Loading...') }}</p>
					<div v-for="(testCase, index) in hiddenPreview" :key="index" class="mt-4 border-t pt-3">
						<p class="text-sm font-medium">{{ __('Hidden Test Cases') }} {{ index + 1 }}</p>
						<div class="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2">
							<div><p class="text-sm">{{ __('Input') }}</p><pre class="max-h-40 overflow-auto rounded bg-surface-gray-2 p-2">{{ testCase.input }}</pre></div>
							<div><p class="text-sm">{{ __('Expected Output') }}</p><pre class="max-h-40 overflow-auto rounded bg-surface-gray-2 p-2">{{ testCase.expected_output }}</pre></div>
						</div>
						<p v-if="testCase.truncated" class="text-sm text-ink-gray-6">{{ __('Preview limited to 2000 characters per field. Download for complete data.') }}</p>
					</div>
				</details>
			</div>
		</template>
		<template #actions>
			<div
				v-if="canManageExercise && !showPackageImport"
				class="flex items-center justify-end gap-2 group"
			>
				<HeaderButton :label="__('Upload problem')" icon="lucide-upload" variant="outline"
					data-testid="programming-exercise-upload" :disabled="saving || uploadingHidden" @click="showPackageImport = true" />
				<HeaderButton
					v-if="exerciseID != 'new'"
					data-testid="programming-exercise-delete"
					:label="__('Delete exercise')"
					icon="lucide-trash-2"
					variant="outline"
					theme="red"
					@click="deleteExercise()"
				/>
				<router-link
					v-if="exerciseID != 'new'"
					:to="{
						name: 'ProgrammingExerciseSubmission',
						query: { testExercise: '1' },
						params: {
							exerciseID: props.exerciseID,
							submissionID: 'new',
						},
					}"
				>
					<HeaderButton
						:label="__('Test this Exercise')"
						icon="lucide-play"
						class="text-p-base-medium"
					/>
				</router-link>
				<router-link
					v-if="exerciseID != 'new'"
					:to="{
						name: 'ProgrammingExerciseSubmissions',
						query: {
							exercise: props.exerciseID,
						},
					}"
				>
					<HeaderButton
						:label="__('Check Submission')"
						icon="lucide-clipboard-list"
					/>
				</router-link>
				<HeaderButton
					:disabled="saving || uploadingHidden"
					data-testid="programming-exercise-save"
					:label="__('Save')"
					variant="solid"
					@click="saveExercise()"
				/>
			</div>
		</template>
	</FormShell>
</template>
<script setup lang="ts">
import { computed, inject, ref, watch, useId } from 'vue'
import { InputLabel } from '@/components/Form/labeling'
import { sanitizeOnWrite } from '@/utils/sanitizeOnWrite'
import {
	Badge,
	createDocumentResource,
	createListResource,
	call,
	createResource,
	FormControl,
	toast,
} from 'frappe-ui'
import { ProgrammingExercise, TestCase } from '@/types'
import ChildTable from '@/components/Controls/ChildTable.vue'
import FormShell from '@/components/FormShell.vue'
import HeaderButton from '@/components/HeaderButton.vue'
import ProblemPackageImport from '@/components/ProblemPackageImport.vue'
import ProgrammingStatementEditor from '@/components/ProgrammingStatementEditor.vue'
import { extractStatementSource } from '@/utils/statementEditor'
import { useFormRoute } from '@/composables/useFormRoute'
import { submitResource } from '@/utils/resource'

const packagePublished = async (name: string) => {
	showPackageImport.value = false
	fetchTestCases()
	loadHiddenCount()
	await exercises.reload()
	await exerciseCount.reload()
	if (props.exerciseID === name) await exerciseDoc?.reload()
	else close()
}

const user = inject<any>('$user')
const problemStatementLabelId = useId()
const isDirty = ref(false)
const showPackageImport = ref(false)
const saving = ref(false)
const uploadingHidden = ref(false)
const hiddenCount = ref(0)
const hiddenPreview = ref<{ input: string; expected_output: string; truncated: boolean }[]>([])
const hiddenOpen = ref(false)
const loadingHiddenPreview = ref(false)
async function loadHiddenPreview() {
	loadingHiddenPreview.value = true
	try { hiddenPreview.value = await editorApi('preview_hidden_cases', { exercise: props.exerciseID }) }
	catch (err: any) { toast.error(__(err.messages?.[0] || err.message || String(err))) }
	finally { loadingHiddenPreview.value = false }
}
function toggleHiddenCases(event: Event) {
	hiddenOpen.value = (event.target as HTMLDetailsElement).open
	if (hiddenOpen.value) loadHiddenPreview()
}
const editorApi = (method: string, args: object) => call(`lms.lms.problem_package.editor.${method}`, args)
const hiddenDownloadUrl = computed(() => `/api/method/lms.lms.problem_package.editor.download_hidden_cases?exercise=${encodeURIComponent(props.exerciseID)}`)
const loadHiddenCount = async () => {
	if (props.exerciseID === 'new') return
	try { hiddenCount.value = await editorApi('hidden_case_count', { exercise: props.exerciseID }) }
	catch (err: any) { toast.error(__(err.messages?.[0] || err.message || String(err))) }
}
async function uploadHiddenCases(event: Event) {
	const input = event.target as HTMLInputElement
	const file = input.files?.[0]
	if (!file || uploadingHidden.value || saving.value || !exerciseDoc?.doc) return
	uploadingHidden.value = true
	try {
		if (file.size > 20 * 1024 * 1024) throw new Error('Package exceeds 20 MiB')
		const data = new FormData()
		data.append('file', file); data.append('is_private', '1')
		const response = await fetch('/api/method/upload_file', { method: 'POST', body: data,
			headers: { 'X-Frappe-CSRF-Token': (window as any).csrf_token || '' } })
		if (!response.ok) throw new Error('Private package upload failed')
		const uploaded = await response.json()
		const result = await editorApi('upload_hidden_cases', { exercise: props.exerciseID,
			modified: exerciseDoc.doc.modified, file_id: uploaded.message.name })
		hiddenCount.value = result.count
		hiddenPreview.value = []
		if (hiddenOpen.value) await loadHiddenPreview()
		// Preserve unsaved title, statement and sample edits while refreshing the version token.
		const draft = { ...exercise.value }, dirty = isDirty.value
		await exerciseDoc.reload()
		exercise.value = draft
		isDirty.value = dirty
		toast.success(__('Hidden cases replaced successfully'))
	} catch (err: any) { toast.error(__(err.messages?.[0] || err.message || String(err))) }
	finally { uploadingHidden.value = false; input.value = '' }
}

const props = withDefaults(
	defineProps<{
		exerciseID: string
	}>(),
	{
		exerciseID: 'new',
	}
)

const { close, saveAndReplace } = useFormRoute({ name: 'ProgrammingExercises' })

// Its own list resource, but every option here is deliberately byte-identical
// to ProgrammingExercises.vue:131-138. createListResource returns whichever
// instance was cached first under this key and DISCARDS the later caller's
// options (listResource.js:15-22), so:
//   - the list page constructs first in the app (a parent route component's
//     setup runs before its child's), which is why the options are duplicated
//     rather than trimmed — on the one path where this call wins the race the
//     list must still get the fields/orderBy/pageLength it relies on (C4b);
//   - a created or deleted exercise reaches the list only because insert and
//     delete refetch THAT instance (listResource.js:123, :161). Disambiguating
//     either key — a filter, a tab, a start — breaks that silently.
// setValue needs none of this: it patches every registered list resource for
// the doctype by name (:144).
const exercises = createListResource({
	doctype: 'LMS Programming Exercise',
	cache: ['programmingExercises'],
	fields: ['name', 'exercise_number', 'title', 'modified'],
	auto: true,
	orderBy: 'modified desc',
	pageLength: 24,
})

// Same shared-instance trick for the header count, which nothing else
// refreshes: createResource caches by key identically (resources.js:10-20).
// The key matches ProgrammingExercises.vue:238. Its `params` carry no filters
// because the filters live in the list page's refs; the list page always
// constructs this first in the app, so its params are the ones that survive.
const exerciseCount = createResource({
	url: 'lms.lms.api.get_programming_exercise_count',
	params: { search: '' },
	cache: ['programming_exercises_count', user.data?.name],
})

// Copied from the gate ProgrammingExercises.vue puts on the Create button
// (:33) and on row click (:152), plus the page-level role check at :119-129.
// A URL goes through neither. This is a UX gate, NOT the authorization
// boundary — Frappe's server-side DocPerms on LMS Programming Exercise are.
const canManageExercise = computed(() => {
	// Cast because Window has no read_only_mode declaration; same shape as
	// NewBatchForm.vue:190.
	if ((window as Window & { read_only_mode?: boolean }).read_only_mode)
		return false
	return Boolean(
		user.data?.is_moderator ||
			user.data?.is_instructor ||
			user.data?.is_evaluator
	)
})

const title = computed(() =>
	props.exerciseID === 'new'
		? __('Create Programming Exercise')
		: __('Edit Programming Exercise')
)

// Only the fields this form edits. Deliberately NOT the whole fetched doc:
// updateExercise spreads this straight into frappe.client.set_value's fieldname
// map, so carrying `owner`/`creation`/`modified` along would write meta fields
// back on every save.
type ExerciseForm = {
	name?: string
	title: string
	language: 'Python' | 'JavaScript' | 'C++'
	problem_statement: string
	test_cases: { input: string; expected_output: string; idx: number }[]
}

const emptyExercise = (): ExerciseForm => ({
	title: '',
	language: 'Python',
	problem_statement: '',
	test_cases: [],
})

const exercise = ref<ExerciseForm>(emptyExercise())

// C4 — edit mode used to be seeded from the list page's in-memory rows, which
// are empty when this route is opened cold. Fetch the record instead, following
// JobForm.vue:182-190.
//
// Constructed conditionally rather than with `name: undefined`, as
// CouponDetails.vue:116-121 does: createDocumentResource bails out and returns
// UNDEFINED for a falsy name (documentResource.js:15), so create mode has no
// resource at all — hence the optional chaining below rather than a plain read.
const exerciseDoc =
	props.exerciseID != 'new'
		? createDocumentResource({
				doctype: 'LMS Programming Exercise',
				name: props.exerciseID,
				auto: true,
				onError(err: any) {
					toast.error(__(err.messages?.[0] || err))
					console.error('Error loading exercise:', err)
				},
		  })
		: undefined

watch(
	() => exerciseDoc?.doc,
	(doc: ProgrammingExercise | undefined) => {
		if (!doc) return
		exercise.value = {
			name: doc.name,
			title: doc.title,
			language: doc.language,
			problem_statement: doc.problem_statement || '',
			test_cases: [],
		}
		isDirty.value = false
	},
	{ immediate: true }
)

const testCases = createListResource({
	doctype: 'LMS Test Case',
	fields: ['input', 'expected_output', 'name'],
	parent: 'LMS Programming Exercise',
	pageLength: 100,
	orderBy: 'idx',
	onSuccess(data: TestCase[]) {
		isDirty.value = false
	},
	onError(err: any) {
		toast.error(__(err.messages?.[0] || err))
		console.error('Error loading testCases:', err)
	},
})

const fetchTestCases = () => {
	testCases.update({
		filters: {
			parent: props.exerciseID,
			parenttype: 'LMS Programming Exercise',
			parentfield: 'test_cases',
		},
	})
	testCases.reload()
}

// C3 — this watch had no `immediate`, so the test cases were fetched only when
// the id CHANGED under an already-mounted parent. Mounted straight from a URL
// the exercise rendered with an empty Test Cases table, and saving it would
// have written that emptiness back.
watch(
	() => props.exerciseID,
	(id) => {
		if (id === 'new') {
			exercise.value = emptyExercise()
			testCases.data = []
			isDirty.value = false
			return
		}
		fetchTestCases()
		loadHiddenCount()
	},
	{ immediate: true }
)

const validateTitle = () => {
	exercise.value.title = sanitizeOnWrite(exercise.value.title.trim())
}

watch(
	exercise,
	() => {
		isDirty.value = true
	},
	{ deep: true }
)

watch(() => testCases.data, () => { isDirty.value = true }, { deep: true })

const updateTestCasesInExercise = () => {
	exercise.value.test_cases = (testCases.data || []).map(
		(tc: TestCase, index: number) => ({
			input: tc.input,
			expected_output: tc.expected_output,
			idx: index + 1,
		})
	)
}

const saveExercise = () => {
	if (!canManageExercise.value || saving.value || uploadingHidden.value) return
	validateTitle()
	updateTestCasesInExercise()
	if (props.exerciseID == 'new') createNewExercise()
	else updateExercise()
}

const createNewExercise = () => {
	submitResource(
		exercises.insert,
		{
			...exercise.value,
		},
		{
			onSuccess() {
				isDirty.value = false
				// insert already refetched the list itself (listResource.js:123);
				// only the header count needs telling.
				exerciseCount.reload()
				toast.success(__('Programming Exercise created successfully'))
				// replace, not push: the form entry is consumed so Back reaches
				// whatever preceded the list rather than a stale empty form.
				saveAndReplace({ name: 'ProgrammingExercises' })
			},
			onError(err: any) {
				toast.warning(__(err.messages?.[0] || err))
			},
		}
	)
}

const updateExercise = async () => {
	if (!exerciseDoc?.doc) return
	saving.value = true
	try {
		await editorApi('save_exercise', {
			exercise: props.exerciseID, modified: exerciseDoc.doc.modified,
			title: exercise.value.title, problem_statement: exercise.value.problem_statement,
			test_cases: exercise.value.test_cases,
			statement_source: exerciseDoc.doc.source_type === 'icpc' ? extractStatementSource(exercise.value.problem_statement) : null,
		})
		isDirty.value = false
		await exercises.reload()
		toast.success(__('Programming Exercise updated successfully'))
		saveAndReplace({ name: 'ProgrammingExercises' })
	} catch (err: any) { toast.warning(__(err.messages?.[0] || err.message || String(err))) }
	finally { saving.value = false }
}

const testCaseColumns = computed(() => {
	return ['Input', 'Expected Output']
})

const deleteExercise = () => {
	if (props.exerciseID == 'new') return
	if (!canManageExercise.value) return
	submitResource(exercises.delete, props.exerciseID, {
		onSuccess() {
			// delete refetches the list (listResource.js:161); the count was
			// left stale by the modal this form replaces.
			exerciseCount.reload()
			toast.success(__('Programming Exercise deleted successfully'))
			close()
		},
		onError(err: any) {
			toast.warning(__(err.messages?.[0] || err))
		},
	})
}
</script>
