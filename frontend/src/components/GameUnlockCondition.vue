<template>
	<div class="unlock-condition">
		<label>
			<span>{{ label }}</span>
			<select
				:value="modelValue"
				:aria-label="label"
				:disabled="disabled || !course || loading"
				@change="$emit('update:modelValue', $event.target.value)"
			>
				<option value="">整门课程完成后解锁</option>
				<option
					v-if="
						modelValue && !lessons.some((lesson) => lesson.name === modelValue)
					"
					:value="modelValue"
				>
					当前指定课时（{{ loading ? '加载中' : '请确认课时' }}）
				</option>
				<option
					v-for="lesson in lessons"
					:key="lesson.name"
					:value="lesson.name"
				>
					完成课时：{{ lesson.chapter_title }} / {{ lesson.title }}
				</option>
			</select>
		</label>
		<p v-if="loading" role="status">正在加载课时…</p>
		<p v-else-if="error" role="alert">
			{{ error }}
			<button type="button" :disabled="disabled" @click="load">重试</button>
		</p>
		<p v-else-if="course && !lessons.length">该课程暂无可选课时。</p>
	</div>
</template>
<script setup>
import { onUnmounted, ref, watch } from 'vue'
import { call } from 'frappe-ui'
const props = defineProps({
	course: { type: String, default: '' },
	modelValue: { type: String, default: '' },
	label: { type: String, default: '解锁条件' },
	disabled: Boolean,
})
defineEmits(['update:modelValue'])
const lessons = ref([])
const loading = ref(false)
const error = ref('')
let version = 0
async function load() {
	const request = ++version
	lessons.value = []
	error.value = ''
	loading.value = !!props.course
	if (!props.course) return
	try {
		const result = await call('lms.lms.game_access.get_course_lessons', {
			course: props.course,
		})
		if (request === version) lessons.value = result || []
	} catch {
		if (request === version) error.value = '无法加载课时，请重试。'
	} finally {
		if (request === version) loading.value = false
	}
}
watch(() => props.course, load, { immediate: true })
onUnmounted(() => {
	version++
})
</script>
<style scoped>
.unlock-condition {
	min-width: 0;
}
label {
	display: flex;
	flex-direction: column;
	gap: 8px;
	font-size: 13px;
}
select {
	width: 100%;
	min-width: 0;
	max-width: 100%;
	min-height: 38px;
	padding: 9px 32px 9px 12px;
	border: 1px solid #dbe3e7;
	border-radius: 7px;
	background: white;
	font-size: 13px;
}
select:focus-visible {
	outline: 2px solid #087f68;
	outline-offset: 3px;
}
select:disabled {
	opacity: 0.5;
	cursor: not-allowed;
}
p {
	color: #748291;
	font-size: 12px;
	margin-top: 6px;
}
button {
	color: #087f68;
	text-decoration: underline;
}
</style>
