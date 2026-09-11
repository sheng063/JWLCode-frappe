<template>
	<div class="space-y-3">
		<FormControl v-if="texSource !== null" type="textarea" :label="__('TeX source')"
			:model-value="texSource" :rows="14" @update:model-value="updateTex" />
		<RichTextEditor v-else :content="modelValue" :editable="true" :fixedMenu="true"
			editorClass="prose-sm max-w-none border rounded-md p-2 min-h-[10rem]"
			@change="(value: string) => emit('update:modelValue', value)" />
		<div class="rounded-md border p-3">
			<p class="mb-2 text-sm text-ink-gray-6">{{ __('Preview') }}</p>
			<ProgrammingStatement :html="modelValue" :icpc="icpc" />
		</div>
	</div>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { FormControl } from 'frappe-ui'
import RichTextEditor from '@/components/RichTextEditor.vue'
import ProgrammingStatement from '@/components/ProgrammingStatement.vue'
import { extractStatementSource, replaceStatementSource } from '@/utils/statementEditor'
const props = defineProps<{ modelValue: string; icpc?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const texSource = computed(() => props.icpc ? extractStatementSource(props.modelValue) : null)
function updateTex(value: string) {
	emit('update:modelValue', replaceStatementSource(props.modelValue, value))
}
</script>
