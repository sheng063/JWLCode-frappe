<template>
	<ListPage
		:breadcrumbs="breadcrumbs"
		:title="__('Submissions')"
		layout="list"
		:columns="submissionColumns"
		:rows="submissions.data || []"
		:loading="submissions.loading"
		:has-next-page="submissions.hasNextPage"
		:list-options="listOptions"
		v-model:page-length="pageLength"
		empty-name="Programming Exercise Submissions"
		empty-icon="lucide-file-code"
		@load-more="submissions.next()"
	>
		<template #filters>
			<Link
				doctype="LMS Programming Exercise"
				v-model="filters.exercise"
				:placeholder="__('Filter by Exercise')"
			/>
			<Link
				doctype="User"
				v-model="filters.member"
				:placeholder="__('Filter by Member')"
				:readonly="isStudent"
			/>
			<FormControl
				v-model="filters.status"
				type="select"
				:options="[
					{},
					{ label: __('Passed'), value: 'Passed' },
					{ label: __('Failed'), value: 'Failed' },
				]"
				:placeholder="__('Filter by Status')"
			/>
		</template>

		<template #cell="{ column, row, value }">
			<div v-if="column.key == 'member_name'" class="flex items-center gap-2">
				<Avatar
					:image="row.member_image as string"
					:label="value as string"
					size="sm"
				/>
				<span class="truncate">{{ value }}</span>
			</div>
			<Badge
				v-else-if="column.key == 'status'"
				:theme="value === 'Passed' ? 'green' : 'red'"
			>
				{{ value }}
			</Badge>
			<div v-else-if="column.key == 'modified'" class="text-sm text-ink-gray-5">
				{{ value }}
			</div>
			<div v-else>{{ value }}</div>
		</template>

		<template #selection-actions="{ unselectAll, selections }">
			<Button
				variant="ghost"
				:label="__('Delete')"
				@click="deleteExercises(selections, unselectAll)"
			>
				<template #icon>
					<span class="lucide-trash-2 size-4" aria-hidden="true" />
				</template>
			</Button>
		</template>
	</ListPage>
</template>
<script setup lang="ts">
import {
	Avatar,
	Badge,
	Button,
	createListResource,
	FormControl,
	usePageMeta,
	toast,
} from 'frappe-ui'
import type {
	ProgrammingExerciseSubmission,
	Filters,
	ListRow,
	ListViewOptions,
} from '@/types'
import { computed, inject, ref, watch } from 'vue'
import { sessionStore } from '@/stores/session'
import { useRouter } from 'vue-router'
import Link from '@/components/Controls/Link.vue'
import ListPage from '@/components/Layouts/ListPage.vue'

const { brand } = sessionStore()
const dayjs = inject('$dayjs') as any
const user = inject('$user') as any
const filterFields = ['exercise', 'member', 'status']
const filters = ref<Filters>({
	exercise: '',
	member: '',
	status: '',
})
const router = useRouter()
const pageLength = ref<number>(24)

const submissions = createListResource({
	doctype: 'LMS Programming Exercise Submission',
	fields: [
		'name',
		'exercise',
		'exercise_title',
		'member_name',
		'member_image',
		'status',
		'modified',
	],
	orderBy: 'modified desc',
	pageLength: 24,
	transform(data: ProgrammingExerciseSubmission[]) {
		return data.map((submission: ProgrammingExerciseSubmission) => {
			return {
				...submission,
				modified: dayjs(submission.modified).fromNow(),
			}
		})
	},
})

watch(pageLength, (value: number) => {
	submissions.pageLength = value
	submissions.reload()
})

const deleteExercises = (selections: Set<string>, unselectAll: () => void) => {
	Array.from(selections).forEach(async (submission: string) => {
		await submissions.delete.submit(submission)
	})
	unselectAll()
	toast.success(__('Submissions deleted successfully'))
}

const isStudent = computed(() => {
	return (
		!user.data?.is_instructor &&
		!user.data?.is_moderator &&
		!user.data?.is_evaluator
	)
})

const routeFilters = () => {
	const query = router.currentRoute.value.query
	return Object.fromEntries(
		filterFields.map((field) => [
			field,
			typeof query[field] === 'string' ? query[field] : '',
		]),
	)
}
watch(
	[() => router.currentRoute.value.query, () => user.data?.name, isStudent],
	() => {
		if (!user.data?.name) return
		const next = routeFilters()
		if (isStudent.value) next.member = user.data.name
		Object.assign(filters.value, next)
		const applied = Object.fromEntries(
			Object.entries(next).filter(([, value]) => value),
		)
		submissions.update({ filters: applied, start: 0 })
		submissions.reload()
	},
	{ immediate: true },
)
watch(
	filters,
	(value) => {
		if (!user.data?.name) return
		const query = { ...router.currentRoute.value.query }
		for (const field of filterFields) {
			const selected =
				field === 'member' && isStudent.value
					? user.data.name
					: value[field as keyof Filters]
			if (selected) query[field] = String(selected)
			else delete query[field]
		}
		if (
			filterFields.some(
				(field) => query[field] !== router.currentRoute.value.query[field],
			)
		) {
			void router.replace({ query })
		}
	},
	{ deep: true },
)

const listOptions: ListViewOptions = {
	selectable: true,
	showTooltip: false,
	getRowRoute: (row: ListRow) => ({
		name: 'ProgrammingExerciseSubmission',
		params: {
			exerciseID: String(row.exercise),
			submissionID: String(row.name),
		},
	}),
}

const submissionColumns = computed(() => {
	return [
		{
			label: __('Member'),
			key: 'member_name',
			width: '30%',
			icon: 'lucide-user',
		},
		{
			label: __('Exercise'),
			key: 'exercise_title',
			width: '30%',
			icon: 'lucide-code',
		},
		{
			label: __('Status'),
			key: 'status',
			width: '20%',
			icon: 'lucide-check-circle',
		},
		{
			label: __('Modified'),
			key: 'modified',
			width: '15%',
			icon: 'lucide-clock',
			align: 'left',
		},
	]
})

const breadcrumbs = computed(() => {
	return [
		{
			label: __('Programming Exercises'),
			route: { name: 'ProgrammingExercises' },
		},
		{ label: __('Submissions') },
	]
})

usePageMeta(() => {
	return {
		title: __('Programming Exercises'),
		icon: brand.favicon,
	}
})
</script>
