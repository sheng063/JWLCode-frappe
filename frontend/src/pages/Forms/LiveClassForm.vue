<template>
	<FormShell
		:title="liveClassName ? __('Edit Live Class') : __('Create a Live Class')"
		size="xl"
		@close="close"
	>
		<template #default>
			<div v-if="loadingBatch" class="p-4 text-base text-ink-gray-6">
				{{ __('Loading...') }}
			</div>
			<div v-else-if="refusal" class="p-4 text-base text-ink-gray-6">
				{{ refusal }}
			</div>
			<div v-else data-testid="live-class-fields" class="flex flex-col gap-4">
				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					<div class="space-y-4">
						<FormControl
							type="text"
							v-model="liveClass.title"
							:label="__('Title')"
							:required="true"
						/>
						<FormControl
							v-model="liveClass.date"
							type="date"
							:label="__('Date')"
							:required="true"
						/>
						<FormControl
							type="number"
							v-model="liveClass.duration"
							:label="__('Duration (in minutes)')"
							:required="true"
						/>
					</div>
					<div class="space-y-4">
						<Tooltip
							:text="
								__(
									'Time must be in 24 hour format (HH:mm). Example 11:30 or 22:00'
								)
							"
						>
							<FormControl
								v-model="liveClass.time"
								type="time"
								:label="__('Time')"
								:required="true"
							/>
						</Tooltip>

						<Combobox
							:modelValue="liveClass.timezone"
							:options="getTimezoneOptions()"
							:label="__('Timezone')"
							:required="true"
							@update:modelValue="(value) => (liveClass.timezone = value)"
						/>
						<FormControl
							v-if="conferencingProvider === 'Zoom'"
							v-model="liveClass.auto_recording"
							type="select"
							:options="getRecordingOptions()"
							:label="__('Auto Recording')"
						/>
					</div>
				</div>
				<FormControl
					v-model="liveClass.description"
					type="textarea"
					:label="__('Description')"
				/>
			</div>
		</template>
		<template #actions>
			<div
				v-if="!refusal && !loadingBatch"
				class="flex items-center justify-end"
			>
				<HeaderButton
					data-testid="live-class-save"
					:label="__('Save')"
					variant="solid"
					:loading="
						createLiveClass.loading ||
						createGoogleMeetLiveClass.loading ||
						updateLiveClass.loading
					"
					@click="submitLiveClass()"
				/>
			</div>
		</template>
	</FormShell>
</template>
<script setup>
import {
	Combobox,
	createResource,
	getCachedListResource,
	Tooltip,
	FormControl,
	toast,
} from 'frappe-ui'
import { computed, reactive, inject, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getTimezones, getUserTimezone } from '@/utils/'
import FormShell from '@/components/FormShell.vue'
import HeaderButton from '@/components/HeaderButton.vue'
import {
	batchRouteLocation,
	useBatchDetails,
} from '@/composables/useBatchForms'
import { useFormRoute } from '@/composables/useFormRoute'
import { resourceErrorMessage, submitResource } from '@/utils/resource'

const props = defineProps({
	liveClassName: { type: String, default: null },
	batchName: {
		type: String,
		required: true,
	},
})

const user = inject('$user')
const dayjs = inject('$dayjs')
const route = useRoute()
const readOnlyMode = window.read_only_mode

// C2: close()'s pop branch restores the hash by itself; its deep-link branch
// replaces to this literal location, so the tab hash has to be carried here or
// a close lands on the bare path and silently resets the page to tab 0.
const { close } = useFormRoute(
	batchRouteLocation('BatchDetail', props.batchName, route.hash)
)

// Parent context a URL cannot carry: the conferencing provider and its account
// pick which endpoint a class is created through. Its own fetch, NOT the page's
// instance — see useBatchForms.ts for why sharing one is not available here.
const batch = useBatchDetails(() => props.batchName)

const loadingBatch = computed(
	() =>
		(!batch.data && batch.loading) ||
		(props.liveClassName && !existingClass.data && !existingClass.error)
)

const conferencingProvider = computed(
	() =>
		existingClass.data?.conferencing_provider ||
		batch.data?.conferencing_provider ||
		null
)

const isAdmin = computed(() =>
	Boolean(user.data?.is_moderator || user.data?.is_evaluator)
)

// Copied from LiveClass.vue's canCreateClass()/hasProviderAccount(), which gate
// the "Add" button. A URL does not go through a button.
//
// UX gate, not an authorization boundary — the server-side permission check in
// lms_batch.create_live_class is.
const hasProviderAccount = computed(() => {
	const data = batch.data
	if (data?.conferencing_provider === 'Zoom' && data?.zoom_account) return true
	if (
		data?.conferencing_provider === 'Google Meet' &&
		data?.google_meet_account
	)
		return true
	return false
})

const refusal = computed(() => {
	if (readOnlyMode) return __('This site is in read-only mode.')
	if (!isAdmin.value)
		return __('You are not permitted to create a live class for this batch.')
	if (props.liveClassName && existingClass.error)
		return __('Unable to load this live class.')
	if (props.liveClassName && existingClass.data?.batch_name !== props.batchName)
		return __('This live class does not belong to this batch.')
	if (!props.liveClassName && !hasProviderAccount.value)
		return __(
			'Please select a conferencing provider and add an account to the batch to create live classes.'
		)
	return null
})

const liveClass = reactive({
	title: '',
	description: '',
	date: '',
	time: '',
	duration: '',
	timezone: '',
	auto_recording: 'No Recording',
	batch: props.batchName,
	host: user.data?.name,
})

onMounted(() => {
	if (!props.liveClassName) liveClass.timezone = getUserTimezone()
})

const existingClass = createResource({
	url: 'frappe.client.get',
	params: { doctype: 'LMS Live Class', name: props.liveClassName },
	auto: Boolean(props.liveClassName),
	onSuccess(doc) {
		for (const key of [
			'title',
			'description',
			'date',
			'time',
			'duration',
			'timezone',
			'auto_recording',
		]) {
			liveClass[key] = doc[key]
		}
		liveClass.time = String(doc.time)
			.split(':')
			.slice(0, 2)
			.map((v) => v.padStart(2, '0'))
			.join(':')
	},
})
const updateLiveClass = createResource({
	url: 'lms.lms.doctype.lms_live_class.lms_live_class.update_live_class',
	makeParams(values) {
		return {
			name: props.liveClassName,
			values,
			modified: existingClass.data?.modified,
		}
	},
})

const getTimezoneOptions = () => {
	return getTimezones().map((timezone) => {
		return {
			label: timezone,
			value: timezone,
		}
	})
}

const getRecordingOptions = () => {
	return [
		{
			label: 'No Recording',
			value: 'No Recording',
		},
		{
			label: 'Local',
			value: 'Local',
		},
		{
			label: 'Cloud',
			value: 'Cloud',
		},
	]
}

const createLiveClass = createResource({
	url: 'lms.lms.doctype.lms_batch.lms_batch.create_live_class',
	makeParams(values) {
		return {
			doctype: 'LMS Live Class',
			batch_name: values.batch,
			zoom_account: batch.data?.zoom_account,
			...values,
		}
	},
})

const createGoogleMeetLiveClass = createResource({
	url: 'lms.lms.doctype.lms_batch.lms_batch.create_google_meet_live_class',
	makeParams(values) {
		return {
			batch_name: values.batch,
			google_meet_account: batch.data?.google_meet_account,
			...values,
		}
	},
})

// C4: the `reloadLiveClasses` defineModel is gone with the modal, so the tab's
// list is refreshed by name instead. A lookup, NOT createListResource — a
// constructor here would win the cache and hand LiveClass.vue an instance with
// this file's (absent) filters/fields, because createListResource discards the
// second caller's options. Null when the tab is not mounted (deep link), which
// is correct: it fetches on mount anyway. Mirrors stores/notifications.js:35.
const reloadLiveClassList = () => {
	getCachedListResource(['liveClasses', props.batchName])?.reload()
}

const submitLiveClass = () => {
	if (refusal.value) return
	const resource = props.liveClassName
		? updateLiveClass
		: conferencingProvider.value === 'Google Meet'
			? createGoogleMeetLiveClass
			: createLiveClass
	return submitResource(resource, liveClass, {
		validate() {
			return validateFormFields()
		},
		onSuccess() {
			reloadLiveClassList()
			close()
		},
		onError(err) {
			toast.error(resourceErrorMessage(err))
		},
	})
}

const validateFormFields = () => {
	if (!liveClass.title.trim()) {
		return __('Please enter a title.')
	}
	if (!liveClass.date) {
		return __('Please select a date.')
	}
	if (!liveClass.time) {
		return __('Please select a time.')
	}
	if (!liveClass.timezone) {
		return __('Please select a timezone.')
	}
	if (!valideTime()) {
		return __('Please enter a valid time in the format HH:mm.')
	}
	const liveClassDateTime = dayjs(`${liveClass.date}T${liveClass.time}`).tz(
		liveClass.timezone,
		true
	)
	if (
		!props.liveClassName &&
		liveClassDateTime.isSameOrBefore(
			dayjs().tz(liveClass.timezone, false),
			'minute'
		)
	) {
		return __('Please select a future date and time.')
	}
	if (
		!Number.isInteger(Number(liveClass.duration)) ||
		Number(liveClass.duration) <= 0
	) {
		return __('Please enter a positive duration in minutes.')
	}
}

const valideTime = () => /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(liveClass.time)
</script>
