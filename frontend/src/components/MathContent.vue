<template>
	<div ref="content" class="math-content"></div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import renderMathInElement from 'katex/contrib/auto-render'
import 'katex/dist/katex.min.css'
import { sanitizeAt } from '@/directives/safeHtmlLevels'

const props = defineProps<{ html?: string | null }>()
const content = ref<HTMLElement | null>(null)

watch([content, () => props.html], ([element, html]) => {
	if (!element) return
	// Sanitize authored HTML first; KaTeX generates its own trusted markup.
	element.innerHTML = sanitizeAt('rich', html)
	renderMathInElement(element, {
		delimiters: [
			{ left: '$$', right: '$$', display: true },
			{ left: '$', right: '$', display: false },
			{ left: '\\(', right: '\\)', display: false },
			{ left: '\\[', right: '\\]', display: true },
		],
		throwOnError: false,
		trust: false,
		ignoredClasses: ['katex'],
	})
}, { flush: 'post' })
</script>

<style scoped>
.math-content :deep(.katex-display) {
	max-width: 100%;
	overflow-x: auto;
	overflow-y: hidden;
	padding-block: 0.25rem;
}
</style>
