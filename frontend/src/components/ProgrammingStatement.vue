<template>
	<div v-if="statement.tex !== null" class="tex-statement" v-html="renderedTex" />
	<MathContent v-else :html="statement.html" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MathContent from '@/components/MathContent.vue'
import { renderTexStatement } from '@/utils/texStatement'
import 'katex/dist/katex.min.css'

const props = defineProps<{ html?: string | null; icpc?: boolean }>()
const statement = computed(() => {
	if (!props.icpc) return { html: props.html, tex: null }
	const document = new DOMParser().parseFromString(props.html || '', 'text/html')
	const links = [...document.querySelectorAll('a')].filter(link =>
		link.getAttribute('href')?.startsWith('/api/method/lms.lms.problem_package.api.download_statement?')
	)
	const tex = links.some(link => link.textContent?.includes('TeX'))
		? document.querySelector('pre')?.textContent ?? null
		: null
	for (const link of links) {
		if (tex !== null) link.remove()
		else link.textContent = '查看题面 PDF'
	}
	return { html: document.body.innerHTML, tex }
})
const renderedTex = computed(() => renderTexStatement(statement.value.tex || '', false))
</script>

<style scoped>
.tex-statement { white-space: normal; overflow-wrap: anywhere; }
.tex-statement :deep(.katex-display) { overflow-x: auto; overflow-y: hidden; }
.tex-statement :deep(.katex) { white-space: nowrap; }
.tex-statement :deep(ul) { list-style-type: disc; padding-left: 1.5rem; }
.tex-statement :deep(ol) { list-style-type: decimal; padding-left: 1.5rem; }
.tex-statement :deep(pre) { white-space: pre; overflow-x: auto; }
</style>
