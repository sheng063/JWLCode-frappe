<template>
	<div class="creation-page">
		<header class="creation-header">
			<h1 class="shrink-0 font-semibold">创作</h1>
			<label class="creation-title"
				><span class="sr-only">作品名称</span
				><input
					v-model="title"
					:disabled="saving || loading"
					maxlength="140"
					placeholder="为作品起个名字"
			/></label>
			<span role="status" class="save-status">{{
				dirty ? '有未保存的更改' : saved ? '已保存到服务器' : ''
			}}</span>
			<RouterLink
				:to="{ name: 'MyCreations' }"
				class="ms-auto shrink-0 text-sm text-ink-gray-7"
				>我的作品</RouterLink
			>
		</header>
		<p v-if="loading" role="status" class="p-4">正在加载作品…</p>
		<p
			v-if="error"
			role="alert"
			class="shrink-0 bg-surface-red-1 p-3 text-sm text-ink-red-4"
		>
			{{ error }}
		</p>
		<div
			v-if="!loading && !loadFailed"
			class="creation-workspace"
			:class="{ 'expand-code': expandedCode }"
		>
			<div class="io-column">
				<section
					class="workspace-panel input-panel"
					aria-labelledby="creation-input-heading"
				>
					<div class="workspace-panel-heading">
						<span class="lucide-log-in size-4 text-blue-500" />
						<h2 id="creation-input-heading">输入</h2>
						<span class="ms-auto text-xs font-normal text-ink-gray-5"
							>运行前填写</span
						>
					</div>
					<label class="input-body"
						><span class="sr-only">标准输入</span
						><textarea
							v-model="stdin"
							:disabled="saving"
							rows="7"
							spellcheck="false"
							placeholder="在此输入 input() / cin 需要读取的数据"
						/>
					</label>
				</section>
				<section
					class="workspace-panel output-panel"
					aria-labelledby="creation-output-heading"
				>
					<div class="workspace-panel-heading">
						<span class="lucide-terminal size-4 text-green-500" />
						<h2 id="creation-output-heading">输出</h2>
						<span
							v-if="running"
							class="lucide-loader-circle ms-auto size-4 animate-spin"
						/>
					</div>
					<div aria-live="polite" class="output-body">
						<p class="text-sm text-ink-gray-6">
							{{
								running
									? '正在运行…'
									: result
										? statusText
										: '点击运行查看输出。'
							}}
						</p>
						<pre v-if="result" class="mt-3 whitespace-pre-wrap break-words">{{
							result.stdout || '（无输出）'
						}}</pre>
						<pre
							v-if="result?.stderr"
							class="mt-3 whitespace-pre-wrap break-words text-ink-red-4"
							>{{ result.stderr }}</pre
						>
					</div>
				</section>
			</div>
			<section
				class="workspace-panel code-column"
				aria-labelledby="creation-code-heading"
			>
				<div class="workspace-panel-heading">
					<span class="lucide-code-xml size-4 text-green-500" />
					<h2 id="creation-code-heading">代码</h2>
					<button
						class="pane-icon ms-auto"
						aria-label="代码格式化"
						title="代码格式化"
						:disabled="formatting || running || saving || !code.trim()"
						@click="formatCode"
					>
						<span
							:class="
								formatting
									? 'lucide-loader-circle size-4 animate-spin'
									: 'lucide-braces size-4'
							"
						/>
					</button>
					<button
						class="pane-icon"
						:aria-label="expandedCode ? '还原代码编辑器' : '展开代码编辑器'"
						:aria-pressed="expandedCode"
						@click="expandedCode = !expandedCode"
					>
						<span
							:class="
								expandedCode
									? 'lucide-minimize size-4'
									: 'lucide-maximize size-4'
							"
						/>
					</button>
				</div>
				<div class="code-toolbar">
					<label
						><span class="sr-only">语言</span
						><select
							v-model="language"
							:disabled="saving || running || formatting"
						>
							<option>Python</option>
							<option>C++</option>
						</select></label
					>
					<div class="flex items-center gap-2">
						<Button
							:loading="running"
							:disabled="running || saving || formatting || !code.trim()"
							@click="run"
							><template #prefix><span class="lucide-play size-3" /></template
							>运行</Button
						>
						<Button
							:loading="saving"
							:disabled="saving || formatting || !title.trim()"
							class="!bg-green-50 !text-green-700 hover:!bg-green-100"
							@click="save"
							><template #prefix><span class="lucide-save size-3" /></template
							>保存</Button
						>
					</div>
				</div>
				<div
					class="editor-fill"
					:style="{
						backgroundColor:
							editorPreferences.theme === 'dark' ? '#141414' : '#fff',
					}"
				>
					<CodeEditor
						ref="codeEditor"
						v-model="code"
						:readonly="saving"
						:type="language"
						:preferences="editorPreferences"
						:show-line-numbers="true"
						:font-size="14"
						fill
						@cursor-change="editorCursor = $event"
					/>
				</div>
				<div class="editor-status">
					<span>{{ language }}</span
					><span>行 {{ editorCursor.row }}，列 {{ editorCursor.column }}</span>
				</div>
			</section>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
	onBeforeRouteLeave,
	onBeforeRouteUpdate,
	useRoute,
	useRouter,
} from 'vue-router'
import { Button, call } from 'frappe-ui'
import CodeEditor from '@/components/Controls/CodeEditor.vue'
import { readEditorPreferences } from '@/utils/editorPreferences'

const codeEditor = ref<InstanceType<typeof CodeEditor> | null>(null)
const editorPreferences = readEditorPreferences()
const editorCursor = ref({ row: 1, column: 1 })
const expandedCode = ref(false)
const formatting = ref(false)
const route = useRoute()
const router = useRouter()
const title = ref('未命名作品')
const language = ref<'Python' | 'C++'>('Python')
const code = ref('')
const stdin = ref('')
const name = ref<string>()
const modified = ref<string>()
const loading = ref(false)
const loadFailed = ref(false)
const saving = ref(false)
const running = ref(false)
const error = ref('')
const saved = ref(false)
const result = ref<{ status: string; stdout: string; stderr: string } | null>(
	null,
)
const snapshot = () =>
	JSON.stringify([title.value, language.value, code.value, stdin.value])
const baseline = ref(snapshot())
const dirty = computed(() => snapshot() !== baseline.value)
const statusText = computed(
	() =>
		({
			COMPLETED: '运行完成',
			COMPILE_ERROR: '编译错误',
			RUNTIME_ERROR: '运行错误',
			TIME_LIMIT_EXCEEDED: '运行超时',
			MEMORY_LIMIT_EXCEEDED: '内存超限',
			SYSTEM_ERROR: '运行服务错误',
			OUTPUT_LIMIT_EXCEEDED: '输出超限',
		})[result.value?.status || ''] || '运行未完成，请稍后重试。',
)
let generation = 0
watch(
	() => route.params.creationId,
	async (id) => {
		if (id && id === name.value) return
		const current = ++generation
		loading.value = !!id
		formatting.value = false
		loadFailed.value = false
		error.value = ''
		result.value = null
		running.value = false
		saving.value = false
		title.value = '未命名作品'
		language.value = 'Python'
		code.value = ''
		stdin.value = ''
		name.value = undefined
		modified.value = undefined
		saved.value = false
		baseline.value = snapshot()
		if (!id) return
		try {
			const doc = await call('lms.lms.creation.get_creation', { name: id })
			if (current !== generation) return
			title.value = doc.title
			language.value = doc.language
			code.value = doc.code || ''
			stdin.value = doc.stdin || ''
			name.value = doc.name
			modified.value = doc.modified
			saved.value = true
			baseline.value = snapshot()
		} catch (e: any) {
			if (current !== generation) return
			error.value = e.message || '作品加载失败，请刷新重试。'
			loadFailed.value = true
		} finally {
			if (current === generation) loading.value = false
		}
	},
	{ immediate: true },
)

async function formatCode() {
	if (formatting.value || saving.value || running.value) return
	const current = generation
	const source = code.value
	const sourceLanguage = language.value
	formatting.value = true
	error.value = ''
	try {
		const formatted = await call('lms.lms.programming_editor.format_code', {
			code: source,
			language: sourceLanguage,
			tab_size: editorPreferences.tabSize,
		})
		if (current !== generation) return
		if (code.value !== source || language.value !== sourceLanguage) {
			error.value = '代码已修改，请重新格式化。'
			return
		}
		codeEditor.value?.replaceCode(formatted)
	} catch (e: any) {
		if (current === generation)
			error.value = e.message || '代码格式化失败，请检查语法后重试。'
	} finally {
		if (current === generation) formatting.value = false
	}
}

async function save() {
	if (saving.value) return
	const current = generation
	const sent = snapshot()
	saving.value = true
	error.value = ''
	try {
		const doc = await call('lms.lms.creation.save_creation', {
			name: name.value,
			modified: modified.value,
			title: title.value,
			language: language.value,
			code: code.value,
			stdin: stdin.value,
		})
		if (current !== generation) return
		name.value = doc.name
		modified.value = doc.modified
		baseline.value = sent
		saved.value = true
		await router.replace({
			name: 'CreationDetail',
			params: { creationId: doc.name },
		})
	} catch (e: any) {
		if (current === generation) error.value = e.message || '保存失败，请重试。'
	} finally {
		if (current === generation) saving.value = false
	}
}
async function run() {
	if (running.value) return
	const current = generation
	running.value = true
	error.value = ''
	result.value = null
	try {
		const output = await call('lms.lms.creation.run_creation', {
			language: language.value,
			code: code.value,
			stdin: stdin.value,
		})
		if (current === generation) result.value = output
	} catch (e: any) {
		if (current === generation) error.value = e.message || '运行失败，请重试。'
	} finally {
		if (current === generation) running.value = false
	}
}
const mayLeave = () =>
	(!saving.value && !dirty.value) ||
	window.confirm(
		saving.value ? '作品正在保存，确定离开？' : '更改尚未保存，确定离开？',
	)
onBeforeRouteLeave(
	(to) =>
		(to.name === 'CreationDetail' && to.params.creationId === name.value) ||
		mayLeave(),
)
onBeforeRouteUpdate((to) => to.params.creationId === name.value || mayLeave())
function beforeUnload(event: BeforeUnloadEvent) {
	if (dirty.value || saving.value) {
		event.preventDefault()
		event.returnValue = ''
	}
}
onMounted(() => window.addEventListener('beforeunload', beforeUnload))
onBeforeUnmount(() => {
	generation++
	window.removeEventListener('beforeunload', beforeUnload)
})
</script>

<style scoped>
.creation-page {
	display: flex;
	flex-direction: column;
	height: 100%;
	min-height: 0;
}
.creation-header {
	display: flex;
	align-items: center;
	flex-wrap: wrap;
	gap: 12px;
	min-height: 48px;
	padding: 8px 16px;
	border-bottom: 1px solid var(--outline-gray-2);
}
.creation-title {
	flex: 0 1 320px;
	min-width: 140px;
}
.creation-title input {
	width: 100%;
	border: 1px solid var(--outline-gray-2);
	border-radius: 6px;
	padding: 5px 9px;
	font-size: 14px;
	background: var(--surface-base);
}
.save-status {
	font-size: 12px;
	color: var(--ink-gray-5);
}
.creation-workspace {
	display: grid;
	grid-template-columns: minmax(260px, 2fr) minmax(0, 3fr);
	flex: 1;
	min-height: 0;
	gap: 8px;
	padding: 6px;
	background: var(--surface-gray-2);
}
.io-column {
	display: grid;
	grid-template-rows: minmax(0, 1fr) minmax(0, 1fr);
	gap: 8px;
	min-height: 0;
	min-width: 0;
}
.workspace-panel {
	display: flex;
	flex-direction: column;
	min-height: 0;
	min-width: 0;
	overflow: hidden;
	border: 1px solid var(--outline-gray-2);
	border-radius: 12px;
	background: var(--surface-base);
}
.workspace-panel-heading {
	display: flex;
	align-items: center;
	gap: 8px;
	min-height: 36px;
	flex-shrink: 0;
	padding: 0 14px;
	background: var(--surface-gray-1);
	color: var(--ink-gray-9);
	font-size: 14px;
	font-weight: 600;
}
.input-body {
	display: flex;
	flex: 1;
	min-height: 0;
	padding: 12px 16px;
}
.input-body textarea {
	width: 100%;
	min-height: 0;
	resize: none;
	border: 0;
	border-radius: 0;
	padding: 0;
	background: transparent;
	font-family: 'JetBrains Mono', monospace;
	font-size: 14px;
	line-height: 1.65;
}
.input-body textarea:focus {
	box-shadow: none;
	outline: none;
}
.input-panel:focus-within {
	border-color: var(--outline-gray-4);
}
.output-body {
	flex: 1;
	min-height: 0;
	overflow: auto;
	padding: 16px;
	font-family: 'JetBrains Mono', monospace;
	font-size: 14px;
	line-height: 1.65;
}
.code-toolbar {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 8px;
	flex-wrap: wrap;
	min-height: 44px;
	flex-shrink: 0;
	padding: 6px 12px;
	border-bottom: 1px solid var(--outline-gray-2);
}
.code-toolbar select {
	width: 120px;
	background-color: transparent;
	border: 0;
	box-shadow: none;
	font-size: 14px;
	color: var(--ink-gray-7);
}
.editor-fill {
	display: flex;
	flex-direction: column;
	flex: 1;
	min-height: 0;
	overflow: hidden;
	padding: 10px 0;
}
.editor-fill :deep(.ace_editor) {
	border: 0;
	border-radius: 0 !important;
	line-height: 1.65;
	box-shadow: none;
}
.editor-fill :deep(.ace-chrome .ace_gutter) {
	background: #fff;
	color: #77909c;
}
.editor-fill :deep(.ace-chrome .ace_marker-layer .ace_active-line) {
	background: #f7f7f7;
}
.editor-status {
	display: flex;
	justify-content: space-between;
	flex-shrink: 0;
	padding: 8px 12px;
	font-size: 12px;
	color: var(--ink-gray-5);
}
.pane-icon {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 28px;
	height: 28px;
	border-radius: 5px;
	color: var(--ink-gray-5);
}
.pane-icon:hover {
	background: var(--surface-gray-3);
	color: var(--ink-gray-9);
}
.pane-icon:disabled {
	opacity: 0.5;
	cursor: not-allowed;
}
button:focus-visible {
	outline: 2px solid #3b82f6;
	outline-offset: 2px;
}
.expand-code {
	grid-template-columns: minmax(0, 1fr);
}
.expand-code .io-column {
	display: none;
}
@media (max-width: 767px) {
	.creation-page {
		height: auto;
		min-height: 100%;
		flex-shrink: 0;
	}
	.creation-header {
		gap: 8px;
		padding: 10px 12px;
	}
	.creation-title {
		flex: 1;
	}
	.save-status {
		order: 1;
		flex-basis: 100%;
	}
	.save-status:empty {
		display: none;
	}
	.creation-workspace {
		display: flex;
		flex-direction: column;
		flex: none;
	}
	.io-column {
		display: flex;
		flex-direction: column;
		flex: none;
	}
	.input-panel,
	.output-panel {
		height: 220px;
		flex: none;
	}
	.expand-code .io-column {
		display: none;
	}
	.code-column {
		flex: none;
		min-height: 500px;
		height: 65dvh;
	}
}
</style>
