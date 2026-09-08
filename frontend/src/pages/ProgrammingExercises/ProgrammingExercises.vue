<template>
	<ListPage
		:breadcrumbs="breadcrumbs"
		:title="__('{0} Exercises').format(totalExercises.data || 0)"
		layout="list"
		:columns="columns"
		:rows="tableRows"
		:list-options="listOptions"
		:total-count="totalExercises.data ?? 0"
		:loading="exercises.list.loading"
		:has-next-page="exercises.hasNextPage"
		v-model:page-length="pageLength"
		empty-name="Programming Exercises"
		empty-icon="lucide-code"
		@load-more="exercises.next()"
	>
		<template #actions>
			<Button v-if="!readOnlyMode" @click="importMode = 'single'">{{ __('Import') }}</Button>
			<Button v-if="!readOnlyMode" @click="importMode = 'bulk'">{{ __('Bulk Import') }}</Button>
			<router-link
				v-if="exercises.data?.length"
				class="hidden md:block"
				:to="{
					name: 'ProgrammingExerciseSubmissions',
				}"
			>
				<Button class="text-p-base-medium">
					<template #prefix>
						<span class="lucide-clipboard-list size-4" />
					</template>
					{{ __('Check All Submissions') }}
				</Button>
			</router-link>
			<Button
				v-if="!readOnlyMode"
				variant="solid"
				@click="openExerciseForm('new')"
			>
				<template #prefix>
					<span class="lucide-plus size-4" />
				</template>
				{{ __('Create') }}
			</Button>
		</template>

		<template #filters>
			<FormControl
				v-model="titleFilter"
				:placeholder="__('Search by title or exercise number')"
				:aria-label="__('Search by title or exercise number')"
			>
				<template #prefix>
					<span class="lucide-search size-4 text-ink-gray-5" />
				</template>
			</FormControl>
		</template>

		<template #cell="{ column, value }">
			<div v-if="column.key == 'modified'" class="text-sm text-ink-gray-5">
				{{ dayjs(value as string).format('MMM D, YYYY') }}
			</div>
			<div v-else>{{ value }}</div>
		</template>

		<template #selection-actions="{ unselectAll, selections }">
			<Button
				variant="solid"
				:loading="exporting"
				:disabled="exporting"
				@click="exportSelectedExercises(selections)"
			>
				<template #prefix>
					<span class="lucide-download size-4" aria-hidden="true" />
				</template>
				{{ exporting ? __('Exporting…') : __('Bulk Export') }}
			</Button>
			<Button
				variant="ghost"
				:label="__('Delete')"
				@click="showDeleteConfirmation(selections, unselectAll)"
			>
				<template #icon>
					<span class="lucide-trash-2 size-4" aria-hidden="true" />
				</template>
			</Button>
		</template>
	</ListPage>

	<FormShell v-if="importMode" :title="importMode === 'bulk' ? __('Bulk Import') : __('Import')" size="4xl" @close="importMode = null">
		<ProblemPackageBulkImport v-if="importMode === 'bulk'" @published="updateList" />
		<ProblemPackageImport v-else @published="singlePackagePublished" />
	</FormShell>
	<router-view />
</template>
<script setup lang="ts">
import { computed, getCurrentInstance, inject, onMounted, ref, watch } from 'vue'
import type dayjsType from 'dayjs'
import {
	Button,
	call,
	createResource,
	createListResource,
	FormControl,
	toast,
	usePageMeta,
} from 'frappe-ui'
import ListPage from '@/components/Layouts/ListPage.vue'
import FormShell from '@/components/FormShell.vue'
import ProblemPackageImport from '@/components/ProblemPackageImport.vue'
import ProblemPackageBulkImport from '@/components/ProblemPackageBulkImport.vue'
import type { ListRow } from '@/types'

import { sessionStore } from '@/stores/session'
import { useRouter } from 'vue-router'
import { openFormRoute } from '@/composables/useFormRoute'
import { exportProgrammingExercises } from '@/utils/exportProgrammingExercises'

const importMode = ref<'single' | 'bulk' | null>(null)
const singlePackagePublished = (_exercise: string, exerciseNumber?: string) => {
	toast.success(exerciseNumber ? `${__("Imported")}: ${exerciseNumber}` : __("Imported"))
	titleFilter.value = ''
	importMode.value = null
	updateList()
}
const exporting = ref(false)
const exportSelectedExercises = async (selections: Set<string>) => {
	if (exporting.value) return
	exporting.value = true
	try {
		await exportProgrammingExercises(Array.from(selections))
		toast.success(__('Export downloaded successfully'))
	} catch (error: any) {
		toast.error(error.message || __('Export failed'))
	} finally {
		exporting.value = false
	}
}

const readOnlyMode = window.read_only_mode
const { brand } = sessionStore()
const user = inject<any>('$user')
const dayjs = inject<typeof dayjsType>('$dayjs')!
const titleFilter = ref<string>('')
const router = useRouter()
const app = getCurrentInstance()
const { $dialog } = app?.appContext.config.globalProperties

onMounted(() => {
	validatePermissions()
})

const validatePermissions = () => {
	if (
		!user.data?.is_instructor &&
		!user.data?.is_moderator &&
		!user.data?.is_evaluator
	) {
		router.push({
			name: 'ProgrammingExerciseSubmissions',
		})
	}
}

const exercises = createListResource({
	doctype: 'LMS Programming Exercise',
	cache: ['programmingExercises'],
	fields: ['name', 'exercise_number', 'title', 'modified'],
	auto: true,
	orderBy: 'modified desc',
	pageLength: 24,
})

// openFormRoute, not a bare router.push: it stamps the history entry so the
// form knows it can pop rather than replace when it closes.
const openExerciseForm = (exerciseID: string) => {
	openFormRoute(router, {
		name: 'ProgrammingExerciseForm',
		params: { exerciseID },
	})
}

const listOptions = computed(() => ({
	showTooltip: false,
	selectable: true,
	onRowClick: (row: ListRow) => {
		if (readOnlyMode) return
		openExerciseForm(row.name as string)
	},
}))

const updateList = () => {
	exercises.update({ orFilters: getFilters(), start: 0 })
	exercises.reload()
	totalExercises.update({ params: { search: titleFilter.value.trim() } })
	totalExercises.reload()
}

const getFilters = () => {
	const search = titleFilter.value.trim()
	return search ? { title: ['like', `%${search}%`], exercise_number: ['like', `%${search}%`] } : {}
}

const showDeleteConfirmation = (
	selections: Set<string>,
	unselectAll: () => void
) => {
	$dialog({
		title: __('Confirm Your Action'),
		message: __(
			'Deleting these exercises will permanently remove them from the system, along with all associated submissions. This action is irreversible. Are you sure you want to proceed?'
		),
		actions: [
			{
				label: __('Delete'),
				theme: 'red',
				variant: 'solid',
				onClick(close: () => void) {
					deleteExercises(selections, unselectAll)
					close()
				},
			},
		],
	})
}

const deleteExercises = (selections: Set<string>, unselectAll: () => void) => {
	Array.from(selections).forEach(async (exerciseName) => {
		call('lms.lms.api.delete_programming_exercise', {
			exercise: exerciseName,
		})
			.then(() => {
				toast.success(__('Exercise deleted successfully'))
				updateList()
			})
			.catch((error: any) => {
				toast.error(__(error.message || error))
				console.error('Error deleting exercise:', error)
			})
	})
	unselectAll()
}

const pageLength = computed({
	get: () => exercises.pageLength,
	set: (value) => {
		// reload() ignores a new pageLength while start > 0: it refetches the
		// already loaded rows instead, so paging must be reset for it to apply.
		exercises.update({ pageLength: value, start: 0 })
		exercises.reload()
	},
})

const totalExercises = createResource({
	url: 'lms.lms.api.get_programming_exercise_count',
	params: { search: '' },
	auto: true,
	cache: ['programming_exercises_count', user.data?.name],
	onError(err: any) {
		toast.error(err.messages?.[0] || err)
		console.error(err)
	},
})

// FormControl forwards native input before updating its model; observe the model
// so requests always contain the current text (including paste and clear).
watch(titleFilter, updateList)

const tableRows = computed(() => exercises.data || [])

const columns = computed(() => {
	return [
		{
			label: __('Exercise Number'),
			key: 'exercise_number',
			width: 0.5,
			align: 'left',
		},
		{
			label: __('Title'),
			key: 'title',
			width: 1,
			icon: 'lucide-file-text',
		},
		{
			label: __('Updated On'),
			key: 'modified',
			width: 1,
			icon: 'lucide-clock',
			align: 'left',
		},
	]
})

usePageMeta(() => {
	return {
		title: __('Programming Exercises'),
		icon: brand.favicon,
	}
})

const breadcrumbs = computed(() => {
	return [
		{
			label: __('Programming Exercises'),
			route: { name: 'ProgrammingExercises' },
		},
	]
})
</script>
