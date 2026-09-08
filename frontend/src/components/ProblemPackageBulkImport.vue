<template>
	<section class="space-y-4" :aria-label="__('Bulk Import')">
		<p class="text-sm text-ink-gray-6">{{ __('Upload the ZIP from Bulk Export, containing one ZIP per problem. Up to 50 problems and 100 MiB; your site upload limit also applies.') }}</p>
		<p class="text-sm text-ink-gray-6">{{ __('Review execution limits before importing. Existing exercises are not overwritten; identical imports may be reused. Programs are not executed during preflight.') }}</p>
		<input type="file" accept=".zip" :disabled="busy" :aria-label="__('Problem bundle')" @change="upload" />
		<p v-if="error" role="alert" class="text-sm text-red-600">{{ error }}</p>
		<div v-if="rows.length" class="flex flex-wrap items-center gap-3">
			<Button :loading="busy" :disabled="busy || !readyCount" @click="importAll">{{ __('Import ready packages') }} ({{ readyCount }})</Button>
			<Button :disabled="busy" @click="refresh">{{ __('Refresh') }}</Button>
			<span role="status" class="text-sm">{{ __('Imported') }}: {{ rows.filter(row => row.published).length }} / {{ rows.length }}</span>
		</div>
		<div v-for="row in rows" :key="row.name" class="space-y-2 rounded-lg border border-outline-gray-2 p-3">
			<div class="flex flex-wrap justify-between gap-2 text-sm font-medium">
				<span>{{ row.report?.title || row.filename }}</span>
				<span>{{ row.published ? __('Imported') : __(row.report?.status || 'Queued') }}</span>
			</div>
			<p class="break-all text-xs text-ink-gray-5">{{ row.filename }}</p>
			<p v-if="row.error" role="alert" class="text-sm text-red-600">{{ row.error }}</p>
			<ul class="text-sm text-ink-gray-6"><li v-for="message in [...(row.report?.errors || []), ...(row.report?.warnings || [])]" :key="message">{{ message }}</li></ul>
			<template v-if="row.report?.status === 'Ready' && !row.published">
				<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
					<label class="text-sm">{{ __('Statement') }}<select v-model="row.statement" :disabled="busy" class="mt-1 block w-full rounded border"><option v-for="path in row.report.statements" :key="path">{{ path }}</option></select></label>
					<label class="text-sm">{{ __('Language') }}<select v-model="row.language" :disabled="busy" class="mt-1 block w-full rounded border"><option>Python</option><option>C++</option></select></label>
					<label class="text-sm">{{ __('Confirmed time limit (seconds)') }}<input v-model="row.seconds" :disabled="busy" type="number" min="0.001" max="30" step="0.001" class="mt-1 block w-full rounded border" /></label>
					<label class="text-sm">{{ __('Memory limit (KiB)') }}<input v-model="row.memory" :disabled="busy" type="number" min="16000" max="1048576" class="mt-1 block w-full rounded border" /></label>
				</div>
			</template>
		</div>
	</section>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { Button, call } from 'frappe-ui'

type Row = {
	name: string; filename: string; language: string; seconds: string | number;
	memory: string | number; statement: string; report?: any; error: string; published: boolean
}
const emit = defineEmits<{ published: [] }>()
const rows = ref<Row[]>([]), busy = ref(false), error = ref('')
const readyCount = computed(() => rows.value.filter(row => !row.published && ['Ready', 'Committed'].includes(row.report?.status)).length)
let timer: ReturnType<typeof setTimeout> | undefined
let disposed = false
onBeforeUnmount(() => { disposed = true; clearTimeout(timer) })
const api = (method: string, args: object) => call(`lms.lms.problem_package.api.${method}`, args)
const message = (e: any) => __(e.messages?.[0] || e.message || String(e))

async function refreshRows() {
	clearTimeout(timer)
	for (const row of rows.value) {
		if (disposed) return
		if (row.published || (row.report && row.report.status !== 'Queued')) continue
		try {
			row.report = await api('get_import', { import_id: row.name })
			row.error = ''
			row.statement ||= row.report.statements?.[0] || ''
			if (row.report.memory_mib != null) row.memory = row.report.memory_mib * 1024
		} catch (e) { row.error = message(e) }
	}
	if (!disposed && rows.value.some(row => !row.error && row.report?.status === 'Queued')) timer = setTimeout(refresh, 2000)
}
async function refresh() {
	if (busy.value || disposed) return
	busy.value = true
	try { await refreshRows() } finally { busy.value = false }
}
async function upload(event: Event) {
	const file = (event.target as HTMLInputElement).files?.[0]
	if (!file || busy.value) return
	clearTimeout(timer)
	busy.value = true; error.value = ''; rows.value = []
	try {
		if (file.size > 100 * 1024 * 1024) throw new Error(__('Upload a ZIP bundle no larger than 100 MiB.'))
		const data = new FormData(); data.append('file', file); data.append('is_private', '1')
		const response = await fetch('/api/method/upload_file', {
			method: 'POST', body: data, headers: { 'X-Frappe-CSRF-Token': (window as any).csrf_token || '' },
		})
		const uploaded = await response.json()
		if (!response.ok) {
			const messages = JSON.parse(uploaded._server_messages || '[]')
			throw new Error(messages[0] ? JSON.parse(messages[0]).message : __('Private package upload failed'))
		}
		if (disposed) return
		const result = await call('lms.lms.problem_package.bulk_import.create_bulk_import', { file_id: uploaded.message.name })
		rows.value = result.imports.map((item: any): Row => ({
			name: item.name, filename: item.filename, language: ['Python', 'C++'].includes(item.options.language) ? item.options.language : 'Python',
			seconds: item.options.time_limit_seconds || '', memory: item.options.memory_limit_kb || 128000,
			statement: '', error: '', published: false,
		}))
		await refreshRows()
	} catch (e) { error.value = message(e) }
	finally { busy.value = false; (event.target as HTMLInputElement).value = '' }
}
async function importAll() {
	if (busy.value) return
	clearTimeout(timer); busy.value = true; error.value = ''
	try {
		for (const row of rows.value) {
			if (disposed) break
			if (row.published || !['Ready', 'Committed'].includes(row.report?.status)) continue
			row.error = ''
			try {
				if (!row.report.package_version) {
					const result = await api('commit_import', { import_id: row.name, options: {
						language: row.language, statement_path: row.statement,
						time_limit_seconds: row.seconds, memory_limit_kb: row.memory,
					} })
					row.report.package_version = result.version; row.report.status = 'Committed'
				}
				await api('publish_version', { version_id: row.report.package_version })
				row.published = true
				emit('published')
			} catch (e) { row.error = message(e) }
		}
	} finally { busy.value = false; if (!disposed) await refresh() }
}
</script>
