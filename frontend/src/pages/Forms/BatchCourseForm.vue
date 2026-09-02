<template>
	<FormShell :title="__('Add a course to the batch')" size="lg" @close="close">
		<template #default>
			<div v-if="refusal" class="p-4 text-base text-ink-gray-6">
				{{ refusal }}
			</div>
			<div v-else data-testid="batch-course-fields" class="flex flex-col gap-4">
				<Link
					doctype="LMS Course"
					v-model="course"
					:label="__('Course')"
					:required="true"
					:filters="{ published: 1 }"
					variant="outline"
					:onCreate="openNewCourse"
				/>
				<Link
					doctype="Course Evaluator"
					v-model="evaluator"
					:label="__('Evaluator')"
				/>
			</div>
		</template>
		<template #actions>
			<HeaderButton
				v-if="!refusal"
				data-testid="batch-course-save"
				:label="__('Save')"
				variant="solid"
				:loading="addBatchCourse.loading"
				@click="submit"
			/>
		</template>
	</FormShell>
</template>

<script setup>
import { computed, inject, ref } from 'vue'
import { createResource, getCachedListResource, toast } from 'frappe-ui'
import { useOnboarding } from 'frappe-ui/frappe'
import { useRoute, useRouter } from 'vue-router'
import Link from '@/components/Controls/Link.vue'
import FormShell from '@/components/FormShell.vue'
import HeaderButton from '@/components/HeaderButton.vue'
import { batchRouteLocation } from '@/composables/useBatchForms'
import { useFormRoute } from '@/composables/useFormRoute'
import { resourceErrorMessage, submitResource } from '@/utils/resource'

const props = defineProps({
	batchName: {
		type: String,
		required: true,
	},
})

const user = inject('$user')
const route = useRoute()
const router = useRouter()
const readOnlyMode = window.read_only_mode
const { updateOnboardingStep } = useOnboarding('learning')

const course = ref(null)
const evaluator = ref(null)

// The tab hash is carried through close(), same as the other batch forms: a
// close that dropped it lands on the bare path and resets the page to tab 0.
const { close, saveAndReplace } = useFormRoute(
	batchRouteLocation('BatchDetail', props.batchName, route.hash)
)

// Copied from BatchCourses.vue's `isAdmin()` gate on the Add button. A URL does
// not go through a button, so the page has to say no by itself.
//
// UX gate, not an authorization boundary — the server-side permission check on
// Batch Course is.
const refusal = computed(() => {
	if (readOnlyMode) return __('This site is in read-only mode.')
	if (!user.data?.is_moderator && !user.data?.is_instructor) {
		return __('You do not have permission to add courses to this batch.')
	}
	return ''
})

// Use the batch-specific endpoint so the parent is locked and reloaded before
// appending, and the response is the persisted child row rather than the parent.
const addBatchCourse = createResource({
	url: 'lms.lms.api.add_batch_course',
})

// Refresh both views of the batch before navigating back. The courses tab owns
// the cached list, while overview/settings use get_batch_details; leaving the
// latter stale can make a newly saved course appear to vanish on page reuse.
const reloadBatchDetails = inject('reloadBatchDetails', null)

const reloadBatchData = () =>
	Promise.all([
		getCachedListResource(['batchCourses', props.batchName])?.reload(),
		reloadBatchDetails?.(),
	])

// Link calls this with one argument unless it is in `inlineCreate` mode, which
// this field is not — it closes its own dropdown first, so there is no second
// close callback to invoke here.
const openNewCourse = () => {
	router.push({ name: 'NewCourse' })
}

// submitResource, not a bare submit(): createResource rethrows after onError, so
// the rejection would be unhandled, and a throw from onSuccess (updateOnboarding
// Step, when onboarding is not registered) would be toasted as a failed request
// even though the row was inserted.
const submit = () => {
	if (refusal.value) return
	return submitResource(
		addBatchCourse,
		{
			batch: props.batchName,
			course: course.value,
			evaluator: evaluator.value,
		},
		{
			async onSuccess() {
				if (user.data?.is_system_manager) {
					updateOnboardingStep('add_batch_course')
				}
				await reloadBatchData()
				toast.success(__('Course added to batch successfully'))
				saveAndReplace(
					batchRouteLocation('BatchDetail', props.batchName, route.hash)
				)
			},
			onError(err) {
				toast.error(resourceErrorMessage(err))
			},
		}
	)
}
</script>
