<template>
	<section
		class="space-y-4 rounded-xl border border-outline-gray-2 bg-surface-gray-1 p-8 text-center"
		role="status"
	>
		<h2 class="text-xl font-semibold">
			{{
				['incomplete', 'incomplete_lesson'].includes(access?.reason_code)
					? access?.required_lesson
						? '完成指定课时，解锁 Game'
						: '完成课程，解锁 Game'
					: 'Game 暂未解锁'
			}}
		</h2>
		<p>{{ access?.message || '教师尚未开放 Game 模块。' }}</p>
		<template
			v-if="
				access?.required_course &&
				access?.course_title &&
				[
					'incomplete',
					'incomplete_lesson',
					'not_enrolled',
					'empty_course',
					'invalid_lesson',
				].includes(access.reason_code)
			"
		>
			<p class="font-medium">{{ access.course_title }}</p>
			<p v-if="access.required_lesson">
				指定课时：{{ access.lesson_title || '课时已不可用，请联系教师' }}
			</p>
			<p>
				已完成 {{ access.completed_lessons }} / {{ access.total_lessons }} 课时
			</p>
			<progress
				class="mx-auto block h-3 w-64 max-w-full"
				:value="access.completed_lessons"
				:max="access.total_lessons || 1"
			/>
			<Button
				variant="solid"
				@click="
					router.push({
						name: 'CourseDetail',
						params: { courseName: access.required_course },
					})
				"
				>继续学习</Button
			>
		</template>
	</section>
</template>
<script setup>
import { Button } from 'frappe-ui'
import { useRouter } from 'vue-router'
defineProps({ access: { type: Object, default: null } })
const router = useRouter()
</script>
