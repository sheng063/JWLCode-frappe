<template>
	<div class="min-w-0 space-y-1 sm:col-span-2">
		<div class="text-sm text-ink-gray-6">{{ __('Statement') }}</div>
		<div v-if="loading" class="truncate text-sm" role="status">{{ __('Loading statement…') }}</div>
		<div v-else-if="error" class="truncate text-sm text-ink-red-4" role="alert">{{ error }}</div>
		<div v-else-if="path.endsWith('.tex')" class="statement-line w-full min-w-0 overflow-hidden text-ellipsis whitespace-nowrap rounded-md bg-surface-gray-1 px-3 py-2 text-sm" v-html="rendered" />
		<a v-else :href="url" target="_blank" rel="noopener" class="block truncate text-sm underline">{{ __('Preview PDF statement') }}</a>
	</div>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { call } from 'frappe-ui'
import { renderTexStatement } from '@/utils/texStatement'
import 'katex/dist/katex.min.css'
const props = defineProps<{ importId: string; path: string }>()
const source = ref(''), loading = ref(false), error = ref('')
const rendered = computed(() => renderTexStatement(source.value))
const url = computed(() => `/api/method/lms.lms.problem_package.api.preview_statement?import_id=${encodeURIComponent(props.importId)}&statement_path=${encodeURIComponent(props.path)}`)
watch(() => [props.importId, props.path], async (_, __old, onCleanup) => {
	let cancelled = false
	onCleanup(() => { cancelled = true })
	source.value = ''; error.value = ''; loading.value = false
	if (!props.path.endsWith('.tex')) return
	loading.value = true
	try {
		const result = await call('lms.lms.problem_package.api.get_statement_source', { import_id: props.importId, statement_path: props.path })
		if (!cancelled) source.value = result.source
	} catch (e: any) { if (!cancelled) error.value = e.messages?.[0] || e.message || String(e) }
	finally { if (!cancelled) loading.value = false }
}, { immediate: true })
</script>
<style scoped>
.statement-line { white-space: nowrap; }
.statement-line :deep(.katex) { white-space: nowrap; }
</style>
