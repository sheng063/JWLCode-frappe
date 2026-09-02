<template>
	<Members
		label="Students"
		default-role="LMS Student"
		:show-role-filter="false"
		:edit-on-row-click="true"
	/>
</template>
<script setup lang="ts">
import { inject, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePageMeta } from 'frappe-ui'
import Members from '@/components/Settings/Members.vue'
import { sessionStore } from '@/stores/session'

const user = inject<any>('$user')
const router = useRouter()
const { brand } = sessionStore()

onMounted(() => {
	if (!user.data?.is_moderator) {
		router.replace({ name: 'Courses' })
	}
})

usePageMeta(() => ({
	title: __('Students'),
	icon: brand.favicon,
}))
</script>
