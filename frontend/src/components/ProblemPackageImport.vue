<template>
	<section class="space-y-5" :aria-label="__('Import ICPC Problem Package')">
		<div class="flex items-start gap-3">
			<span class="lucide-package mt-1 size-6 text-ink-gray-6" aria-hidden="true" />
			<div><h3 class="font-semibold text-ink-gray-9">{{ __('Import ICPC Problem Package') }}</h3>
				<p class="mt-1 text-sm text-ink-gray-6">{{ __('Upload a package, review the statement and limits, then import it into the exercise library.') }}</p>
			</div>
		</div>
		<ol class="grid grid-cols-3 gap-2 text-sm" :aria-label="__('Import progress')">
			<li class="rounded-lg bg-surface-gray-2 p-3">1 · {{ __('Upload package') }}</li>
			<li class="rounded-lg p-3" :class="report ? 'bg-surface-gray-2' : 'text-ink-gray-5'">2 · {{ __('Review problem') }}</li>
			<li class="rounded-lg p-3" :class="report?.package_version ? 'bg-surface-gray-2' : 'text-ink-gray-5'">3 · {{ __('Import to library') }}</li>
		</ol>
		<label class="relative flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed border-outline-gray-3 bg-surface-gray-1 px-5 py-7 text-center focus-within:ring-2 focus-within:ring-outline-gray-4" :class="{ 'opacity-60': busy }">
			<span class="lucide-upload size-6 text-ink-gray-5" aria-hidden="true" />
			<span class="text-sm font-medium">{{ filename || __('Choose a ZIP or KPP file') }}</span>
			<span class="text-xs text-ink-gray-5">{{ __('Up to 20 MiB upload · 128 MiB expanded · 16 MiB per input · 100 cases') }}</span>
			<input class="absolute inset-0 h-full w-full cursor-pointer opacity-0" type="file" accept=".zip,.kpp" :disabled="busy" :aria-label="__('Problem package')" @change="upload" />
		</label>
		<p v-if="busy" role="status" class="text-sm text-ink-gray-6">{{ activity }}</p>
		<p v-if="error" role="alert" class="rounded-lg bg-surface-red-1 p-3 text-sm text-ink-red-4">{{ error }}</p>
		<div v-if="report" class="space-y-4" aria-live="polite">
			<div class="rounded-lg border border-outline-gray-2 p-4">
				<div class="flex flex-wrap items-center justify-between gap-2"><h4 class="font-semibold">{{ report.title || filename }}</h4><span class="rounded bg-surface-gray-2 px-2 py-1 text-xs">{{ statusText }}</span></div>
				<p class="mt-2 text-sm text-ink-gray-6">{{ __('Public samples') }}: {{ report.samples?.length || 0 }} · {{ __('Hidden cases') }}: {{ report.hidden_count || 0 }}</p>
				<p v-if="report.status === 'Published'" class="mt-2 text-sm text-ink-green-4">{{ __('Imported') }} · {{ report.exercise_number }}</p>
				<p v-if="report.status === 'Ready' || report.status === 'Committed'" class="mt-2 text-sm text-ink-gray-6">{{ __('This problem is not in the library yet. Complete the import below to make it searchable.') }}</p>
				<ul v-if="report.errors?.length" class="mt-3 space-y-1 text-sm text-ink-red-4"><li v-for="message in report.errors" :key="message">{{ __(message) }}</li></ul>
				<details v-if="report.warnings?.length" class="mt-3 text-sm text-ink-gray-6"><summary class="cursor-pointer">{{ __('Inspection notes') }}</summary><ul class="mt-2 space-y-1"><li v-for="message in report.warnings" :key="message">{{ __(message) }}</li></ul></details>
			</div>
			<a v-if="statement" :href="`/api/method/lms.lms.problem_package.api.preview_statement?import_id=${encodeURIComponent(report.name)}&statement_path=${encodeURIComponent(statement)}`" target="_blank" rel="noopener" class="inline-flex items-center gap-2 text-sm underline"><span class="lucide-file-text size-4" />{{ __('Preview PDF statement') }}</a>
			<details v-if="report.samples?.length" class="rounded-lg border border-outline-gray-2 p-3 text-sm">
				<summary class="cursor-pointer font-medium">{{ __('Public samples') }}</summary>
				<div v-for="sample in report.samples" :key="sample.case_id" class="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
					<div><p class="mb-1 text-ink-gray-5">{{ __('Input') }}</p><pre class="max-h-40 overflow-auto rounded bg-surface-gray-2 p-2">{{ sample.input }}</pre></div>
					<div><p class="mb-1 text-ink-gray-5">{{ __('Expected Output') }}</p><pre class="max-h-40 overflow-auto rounded bg-surface-gray-2 p-2">{{ sample.expected_output }}</pre></div>
				</div>
			</details>
			<template v-if="report.status === 'Ready'">
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<label class="text-sm">{{ __('Statement') }}<select v-model="statement" :disabled="busy" class="mt-1 block w-full rounded-lg border border-outline-gray-2 p-2"><option v-for="path in report.statements" :key="path">{{ path }}</option></select></label>
					<label class="text-sm">{{ __('Language') }}<select v-model="language" :disabled="busy" class="mt-1 block w-full rounded-lg border border-outline-gray-2 p-2"><option>Python</option><option>C++</option></select></label>
					<label class="text-sm">{{ __('Confirmed time limit (seconds)') }}<input v-model="seconds" :disabled="busy" type="number" min="0.001" max="30" step="0.001" class="mt-1 block w-full rounded-lg border border-outline-gray-2 p-2" /></label>
					<label class="text-sm">{{ __('Memory limit (KiB)') }}<input v-model="memory" :disabled="busy || report.memory_mib != null" type="number" min="16000" max="1048576" class="mt-1 block w-full rounded-lg border border-outline-gray-2 p-2" /><span v-if="report.memory_mib" class="mt-1 block text-xs text-ink-gray-5">{{ report.memory_mib }} MiB × 1024</span></label>
				</div>
			</template>
			<div class="flex items-center justify-end border-t border-outline-gray-2 pt-4">
				<button v-if="report.status === 'Ready' || report.status === 'Committed'" :disabled="busy || !validOptions" class="rounded-lg bg-surface-gray-10 px-4 py-2 text-sm font-medium text-ink-base hover:bg-surface-gray-9 disabled:cursor-not-allowed disabled:opacity-50" @click="importProblem">{{ report.package_version ? __('Retry import to library') : __('Import to library') }}</button>
				<button v-if="report.status === 'Queued'" :disabled="busy" class="rounded-lg border border-outline-gray-2 px-4 py-2 text-sm" @click="refresh">{{ __('Refresh preflight') }}</button>
			</div>
		</div>
	</section>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { call } from 'frappe-ui'
const props = defineProps<{ exercise?: string; activeVersion?: string }>()
const emit = defineEmits<{ published: [exercise: string, exerciseNumber?: string] }>()
const busy = ref(false), error = ref(''), report = ref<any>(null), filename = ref(''), activity = ref('')
const statement = ref(''), language = ref('C++'), seconds = ref('2'), memory = ref(131072)
const validOptions = computed(() => !!report.value?.package_version || (!!statement.value && Number(seconds.value) > 0 && Number(seconds.value) <= 30 && Number(memory.value) >= 16000 && Number(memory.value) <= 1048576))
const statusText = computed(() => __(({ Queued: 'Inspecting package', Ready: 'Ready to import', Rejected: 'Package rejected', Committed: 'Draft saved; import pending', Published: 'Imported' } as Record<string, string>)[report.value?.status] || report.value?.status || ''))
let importId = '', timer: ReturnType<typeof setTimeout> | undefined
let disposed = false
onBeforeUnmount(() => { disposed = true; clearTimeout(timer) })
const api = (method: string, args: object) => call(`lms.lms.problem_package.api.${method}`, args)
async function perform(action: () => Promise<void>) {
	if (busy.value || disposed) return
	busy.value = true; error.value = ''
	try { await action() } catch (e: any) { error.value = __(e.messages?.[0] || e.message || String(e)) }
	finally { busy.value = false }
}
async function refresh() {
	clearTimeout(timer)
	activity.value = __('Inspecting package')
	await perform(async () => {
		report.value = await api('get_import', { import_id: importId })
		statement.value ||= report.value.statements?.[0] || ''
		if (report.value.memory_mib != null) memory.value = report.value.memory_mib * 1024
		if (report.value.status === 'Queued' && !disposed) timer = setTimeout(refresh, 2000)
	})
}
async function upload(event: Event) {
	const input = event.target as HTMLInputElement
	const file = input.files?.[0]
	if (!file || busy.value) return
	clearTimeout(timer); report.value = null; statement.value = ''; filename.value = file.name
	seconds.value = '2'; memory.value = 131072; importId = ''
	activity.value = __('Uploading private package')
	await perform(async () => {
		if (!/\.(zip|kpp)$/i.test(file.name)) throw new Error('Choose a ZIP or KPP file')
		if (file.size > 20 * 1024 * 1024) throw new Error('Package exceeds 20 MiB')
		const data = new FormData(); data.append('file', file); data.append('is_private', '1')
		const response = await fetch('/api/method/upload_file', {
			method: 'POST', body: data, headers: { 'X-Frappe-CSRF-Token': (window as any).csrf_token || '' },
		})
		if (!response.ok) throw new Error('Private package upload failed')
		const uploaded = await response.json()
		const created = await api('create_import', { file_id: uploaded.message.name, target_exercise: props.exercise === 'new' ? null : props.exercise })
		importId = created.name
	})
	input.value = ''
	if (!error.value && !disposed) await refresh()
}
async function importProblem() {
	if (!validOptions.value) return
	activity.value = __('Importing to library')
	await perform(async () => {
		if (!report.value.package_version) {
			const result = await api('commit_import', { import_id: importId, expected_target_version: props.activeVersion || '', options: {
				language: language.value, statement_path: statement.value, time_limit_seconds: seconds.value, memory_limit_kb: memory.value,
			} })
			report.value.package_version = result.version; report.value.status = 'Committed'
		}
		const result = await api('publish_version', { version_id: report.value.package_version })
		report.value.status = 'Published'; report.value.exercise_number = result.exercise_number
		emit('published', result.exercise, result.exercise_number)
	})
}
</script>
