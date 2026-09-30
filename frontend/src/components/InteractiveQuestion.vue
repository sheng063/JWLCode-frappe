<template>
	<div class="mt-4 space-y-3">
		<template v-if="question.type === 'Ordering'">
			<p class="text-sm text-ink-gray-6">
				拖拽条目调整顺序，也可使用上下移动按钮。
			</p>
			<Draggable
				v-model="ordered"
				item-key="id"
				handle=".sort-handle"
				:disabled="disabled"
				@change="saveOrder"
			>
				<template #item="{ element, index }">
					<div
						class="flex items-center gap-3 border rounded-lg p-3 mb-2 bg-surface-gray-2"
					>
						<button
							type="button"
							class="sort-handle cursor-grab touch-none"
							:disabled="disabled"
							:aria-label="'拖拽 ' + quizText(element.text)"
						>
							⠿
						</button>
						<span class="text-ink-gray-5">{{ index + 1 }}.</span>
						<span class="flex-1 whitespace-pre-wrap break-words">{{
							quizText(element.text)
						}}</span>
						<button
							type="button"
							:disabled="disabled || index === 0"
							aria-label="向上移动"
							@click="move(index, -1)"
						>
							↑
						</button>
						<button
							type="button"
							:disabled="disabled || index === ordered.length - 1"
							aria-label="向下移动"
							@click="move(index, 1)"
						>
							↓
						</button>
					</div>
				</template>
			</Draggable>
		</template>
		<template v-else>
			<p class="text-sm text-ink-gray-6">
				分别点击左右两列中的对应内容，先点击哪一列均可。
			</p>
			<div class="grid grid-cols-2 gap-4">
				<div
					v-for="side in ['left', 'right']"
					:key="side"
					class="space-y-2"
					:aria-label="side === 'left' ? '左列' : '右列'"
				>
					<button
						v-for="item in remaining(side)"
						:key="item.id"
						type="button"
						class="w-full border rounded-lg p-3 text-left whitespace-pre-wrap break-words"
						:class="
							selected[side] === item.id
								? 'bg-surface-blue-2 border-outline-blue-3'
								: 'bg-surface-gray-2'
						"
						:aria-pressed="selected[side] === item.id"
						:disabled="disabled || busy"
						@click="select(side, item.id)"
					>
						{{ quizText(item.text) }}
					</button>
				</div>
			</div>
			<p role="status" :class="error ? 'text-ink-red-6' : 'text-ink-green-6'">
				{{ message }}
			</p>
			<p
				v-if="modelValue.length === question.items.length"
				class="text-ink-green-6"
				role="status"
			>
				全部匹配正确，已通过！
			</p>
		</template>
	</div>
</template>
<script setup>
import { ref, reactive, watch, onBeforeUnmount } from 'vue'
import Draggable from 'vuedraggable'
import { call } from 'frappe-ui'
import { quizText } from '@/utils/quizText'
const props = defineProps({
	question: Object,
	quiz: String,
	modelValue: { type: Array, default: () => [] },
	disabled: Boolean,
})
const emit = defineEmits(['update:modelValue'])
let disposed = false
onBeforeUnmount(() => {
	disposed = true
})
const ordered = ref([])
const selected = reactive({ left: null, right: null })
const busy = ref(false)
const message = ref('')
const error = ref(false)
watch(
	() => props.modelValue,
	(answers) => {
		if (props.question.type !== 'Ordering') return
		const items = props.question.items || []
		ordered.value =
			answers.length === items.length
				? answers
						.map((id) => items.find((item) => item.id === id))
						.filter(Boolean)
				: [...items]
	},
	{ immediate: true },
)
function saveOrder() {
	emit(
		'update:modelValue',
		ordered.value.map((item) => item.id),
	)
}
function move(index, delta) {
	if (
		props.disabled ||
		index + delta < 0 ||
		index + delta >= ordered.value.length
	)
		return
	const items = [...ordered.value]
	const [item] = items.splice(index, 1)
	items.splice(index + delta, 0, item)
	ordered.value = items
	saveOrder()
}
function remaining(side) {
	const used = new Set(
		props.modelValue.map((pair) => pair.split(':')[side === 'left' ? 0 : 1]),
	)
	return (
		side === 'left' ? props.question.items : props.question.right_items
	).filter((item) => !used.has(item.id))
}
async function select(side, id) {
	if (props.disabled || busy.value) return
	selected[side] = selected[side] === id ? null : id
	message.value = ''
	if (!selected.left || !selected.right) return
	busy.value = true
	const left = selected.left,
		right = selected.right
	try {
		const correct = await call('lms.lms.quiz_interactions.check_match', {
			quiz: props.quiz,
			question: props.question.name,
			left,
			right,
		})
		if (disposed) return
		error.value = !correct
		message.value = correct ? '匹配正确！' : '匹配错误，请重新选择。'
		if (correct)
			emit('update:modelValue', [...props.modelValue, `${left}:${right}`])
	} catch (err) {
		error.value = true
		message.value = err?.messages?.[0] || '暂时无法检查匹配，请重试。'
	} finally {
		selected.left = null
		selected.right = null
		busy.value = false
	}
}
</script>
