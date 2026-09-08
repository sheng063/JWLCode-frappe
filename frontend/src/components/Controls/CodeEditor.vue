<template>
	<div
		class="editor isolate flex flex-col gap-1.5"
		:class="{ 'editor-grow': fill }"
		:style="fill ? null : { height: height }"
	>
		<InputLabel
			v-if="label"
			:id="labelId"
			:for-id="inputId"
			:label="label ? __(label) : undefined"
			:required="required"
		/>
		<div
			:id="inputId"
			ref="editor"
			class="h-auto flex-1 overflow-hidden overscroll-none !rounded border border-outline-gray-2 transition-colors hover:border-outline-gray-3 focus-within:border-outline-gray-4 focus-within:shadow-sm"
		/>
		<InputDescription
			v-if="showDescription"
			:id="descriptionId"
			:description="description"
		/>
		<InputError v-if="hasError" :id="errorMessageId" :lines="errorLines" />
		<Button
			v-if="showSaveButton"
			@click="emit('save', aceEditor?.getValue())"
			class="mt-3"
		>
			{{ __('Save') }}
		</Button>
	</div>
</template>
<script setup lang="ts">
import ace from 'ace-builds'
import 'ace-builds/src-min-noconflict/ext-searchbox'
import 'ace-builds/src-noconflict/ext-language_tools'
import 'ace-builds/src-noconflict/keybinding-vim'
import 'ace-builds/src-noconflict/keybinding-emacs'
import type { EditorPreferences } from '@/utils/editorPreferences'
import 'ace-builds/src-min-noconflict/theme-chrome'
import 'ace-builds/src-min-noconflict/theme-twilight'
import { PropType, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Button } from 'frappe-ui'
import {
	InputDescription,
	InputError,
	InputLabel,
	useInputLabeling,
} from '@/components/Form/labeling'

const isDark = ref(false)

const props = defineProps({
	modelValue: {
		type: [Object, String, Array],
	},
	type: {
		type: String as PropType<
			'JSON' | 'HTML' | 'Python' | 'JavaScript' | 'C++' | 'CSS'
		>,
		default: 'JSON',
	},
	label: {
		type: String,
		default: '',
	},
	readonly: {
		type: Boolean,
		default: false,
	},
	height: {
		type: String,
		default: '250px',
	},
	fontSize: { type: Number, default: 12 },
	preferences: {
		type: Object as PropType<EditorPreferences>,
		default: undefined,
	},
	fill: {
		type: Boolean,
		default: false,
	},
	showLineNumbers: {
		type: Boolean,
		default: false,
	},
	autofocus: {
		type: Boolean,
		default: true,
	},
	showSaveButton: {
		type: Boolean,
		default: false,
	},
	description: {
		type: String,
		default: '',
	},
	required: {
		type: Boolean,
		default: false,
	},
	error: {
		type: [String, Object] as PropType<string | Error>,
		default: undefined,
	},
})

const {
	inputId,
	labelId,
	descriptionId,
	errorMessageId,
	hasError,
	errorLines,
	showDescription,
} = useInputLabeling(props)

const emit = defineEmits(['save', 'update:modelValue', 'cursor-change'])
const editor = ref<HTMLElement | null>(null)
let aceEditor = null as ace.Ace.Editor | null
let resizeObserver: ResizeObserver | null = null
let syncingModel = false

onMounted(() => {
	isDark.value = localStorage.getItem('theme') === 'dark'
	setupEditor()
	// ACE only reflows on window resize by default. When the editor container's
	// size changes without a window resize (e.g. a resizable pane, or a collapsed
	// panel that frees space), the editor must be told to re-measure or it keeps
	// its previous dimensions and leaves a gap. Observe the container and resize.
	if (editor.value && typeof ResizeObserver !== 'undefined') {
		resizeObserver = new ResizeObserver(() => {
			aceEditor?.resize()
		})
		resizeObserver.observe(editor.value)
	}
})

onBeforeUnmount(() => {
	resizeObserver?.disconnect()
	aceEditor?.destroy()
	aceEditor = null
})

const setupEditor = () => {
	aceEditor?.destroy()
	aceEditor = ace.edit(editor.value as HTMLElement)
	resetEditor(props.modelValue as string, true)
	aceEditor.setReadOnly(props.readonly)
	aceEditor.setOptions({
		fontSize: props.fontSize,
		useWorker: false,
		showGutter: props.showLineNumbers,
		wrap: props.showLineNumbers,
	})
	applyPreferences()
	loadEditorMode()
	aceEditor.selection.on('changeCursor', () => {
		const cursor = aceEditor?.getCursorPosition()
		if (cursor)
			emit('cursor-change', { row: cursor.row + 1, column: cursor.column + 1 })
	})
	aceEditor.on(props.preferences ? 'change' : 'blur', () => {
		if (syncingModel) return
		try {
			let value = aceEditor?.getValue() || ''
			if (props.type === 'JSON') {
				value = JSON.parse(value)
			}
			if (value === props.modelValue) return
			if (!props.showSaveButton && !props.readonly) {
				emit('update:modelValue', value)
			}
		} catch (e) {
			// do nothing
		}
	})
}

function loadEditorMode() {
	const target = aceEditor
	const type = props.type
	const modes = {
		CSS: ['css', () => import('ace-builds/src-noconflict/mode-css')],
		JavaScript: [
			'javascript',
			() => import('ace-builds/src-noconflict/mode-javascript'),
		],
		Python: ['python', () => import('ace-builds/src-noconflict/mode-python')],
		'C++': ['c_cpp', () => import('ace-builds/src-noconflict/mode-c_cpp')],
		JSON: ['json', () => import('ace-builds/src-noconflict/mode-json')],
		HTML: ['html', () => import('ace-builds/src-noconflict/mode-html')],
	} as const
	const [mode, load] = modes[type] || modes.HTML
	void load().then(() => {
		if (target && aceEditor === target && props.type === type)
			target.session.setMode(`ace/mode/${mode}`)
	})
}

const getModelValue = () => {
	let value = props.modelValue || ''
	try {
		if (props.type === 'JSON' || typeof value === 'object') {
			value = JSON.stringify(value, null, 2)
		}
	} catch (e) {
		// do nothing
	}
	return value as string
}

function resetEditor(value: string, resetHistory = false) {
	value = getModelValue()
	// Ace setValue emits removal and insertion separately. Neither is a user edit.
	syncingModel = true
	try {
		aceEditor?.setValue(value)
	} finally {
		syncingModel = false
	}
	aceEditor?.clearSelection()
	applyTheme()
	props.autofocus && aceEditor?.focus()
	if (resetHistory) {
		aceEditor?.session.getUndoManager().reset()
	}
}

function applyTheme() {
	const dark = props.preferences ? props.preferences.theme === 'dark' : isDark.value
	aceEditor?.setTheme(dark ? 'ace/theme/twilight' : 'ace/theme/chrome')
}
watch(isDark, applyTheme)

watch(
	() => props.type,
	() => {
		loadEditorMode()
	},
)

watch(
	() => props.modelValue,
	() => {
		if (getModelValue() !== aceEditor?.getValue())
			resetEditor(props.modelValue as string)
	},
)

function applyPreferences() {
	const p = props.preferences
	if (!aceEditor || !p) return
	applyTheme()
	aceEditor.setOptions({
		fontSize: p.fontSize,
		fontFamily: p.fontFamily,
		wrap: p.wrap,
		relativeLineNumbers: p.relativeLineNumbers,
		enableBasicAutocompletion: p.autocomplete,
		enableLiveAutocompletion: p.autocomplete,
		tabSize: p.tabSize,
		useSoftTabs: true,
	})
	aceEditor.setKeyboardHandler(
		p.keyboard === 'standard' ? null : `ace/keyboard/${p.keyboard}`,
	)
	if (editor.value)
		editor.value.style.fontVariantLigatures = p.fontLigatures
			? 'normal'
			: 'none'
	aceEditor.resize()
}
watch(() => props.preferences, applyPreferences, { deep: true })
function replaceCode(value: string) {
	if (!aceEditor || props.readonly) return
	const cursor = aceEditor.getCursorPosition()
	aceEditor.session.getUndoManager().startNewGroup()
	const Range = ace.require('ace/range').Range
	aceEditor.session.replace(
		new Range(0, 0, aceEditor.session.getLength(), 0),
		value,
	)
	aceEditor.session.getUndoManager().startNewGroup()
	aceEditor.moveCursorToPosition(cursor)
	aceEditor.clearSelection()
	emit('update:modelValue', value)
	aceEditor.focus()
}
defineExpose({
	resetEditor,
	getValue: () => aceEditor?.getValue() || '',
	replaceCode,
})
</script>

<style>
/* When `fill` is set the editor grows to fill its flex parent instead of using a
   fixed height. The parent must be a flex container with a definite height. */
.editor-grow {
	flex: 1 1 auto;
	min-height: 0;
}
</style>
