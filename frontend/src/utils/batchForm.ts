import type { LMSBatch } from '@/types/lms/LMSBatch'

const CHECKBOX_FIELDS: (keyof LMSBatch)[] = [
	'published',
	'paid_batch',
	'allow_self_enrollment',
	'certification',
	'evaluation',
]

const SEPARATELY_MANAGED_CHILD_TABLES: (keyof LMSBatch)[] = [
	'courses',
	'assessment',
	'timetable',
	'timetable_legends',
]

const formatTime = (time: string): string => {
	const [hours, minutes] = time.split(':')
	return `${hours.padStart(2, '0')}:${minutes}`
}

// Normalize server values before createDocumentResource stores its baseline.
// Mutating time/check fields later inside a deep watcher made the form dirty
// immediately after every response and started an endless autosave cycle.
export function normalizeBatchDoc(doc: LMSBatch): LMSBatch {
	const normalized = {
		...doc,
		start_time: formatTime(doc.start_time),
		end_time: formatTime(doc.end_time),
	} as LMSBatch
	for (const key of CHECKBOX_FIELDS) {
		;(normalized as unknown as Record<string, unknown>)[key] = Boolean(doc[key])
	}
	return normalized
}

// Courses, assessments and timetables have their own resources and save flows.
// A settings form can stay mounted with an older snapshot while one of those
// resources changes; never send its stale child arrays back to the parent.
export function batchSettingsPayload(
	doc: LMSBatch,
	instructors: readonly string[]
): Record<string, unknown> {
	const payload = { ...doc } as Record<string, unknown>
	for (const field of SEPARATELY_MANAGED_CHILD_TABLES) delete payload[field]
	payload.instructors = instructors.map((instructor) => ({ instructor }))
	return payload
}

// Client-side mirror of LMS Batch's mandatory fields (lms_batch.json `reqd`).
// `batch_details` is a Text Editor field, so an "empty" editor still serializes
// to markup like "<p></p>", so strip tags before treating it as filled.
interface BatchValidationInput {
	doc: Pick<
		LMSBatch,
		| 'title'
		| 'start_date'
		| 'end_date'
		| 'start_time'
		| 'end_time'
		| 'timezone'
		| 'description'
		| 'batch_details'
		| 'paid_batch'
		| 'amount'
		| 'currency'
	> | null
	instructors: readonly string[]
}

function hasText(value: string | null | undefined): boolean {
	if (!value) return false
	return value.replace(/<[^>]*>/g, '').trim().length > 0
}

// Returns a single actionable message for the first unmet requirement, or null
// when the batch can be saved. Field labels match the form labels.
export function validateBatch(input: BatchValidationInput): string | null {
	const { doc, instructors } = input
	if (!doc) return null

	const required: [string, string | null | undefined][] = [
		[__('Title'), doc.title],
		[__('Batch Start Date'), doc.start_date],
		[__('Batch End Date'), doc.end_date],
		[__('Session Start Time'), doc.start_time],
		[__('Session End Time'), doc.end_time],
		[__('Timezone'), doc.timezone],
		[__('Short Description'), doc.description],
		[__('Batch Details'), doc.batch_details],
	]
	for (const [label, value] of required) {
		if (!hasText(value)) {
			return __('Add a {0} before saving.').format(label)
		}
	}
	if (!instructors.length) {
		return __('Add at least one {0} before saving.').format(__('Instructor'))
	}

	if (!doc.paid_batch) return null
	if (!doc.currency) {
		return __('Currency is required for {0}.').format(__('paid batches'))
	}
	if (!(Number(doc.amount) > 0)) {
		return __('Amount must be a positive number for {0}.').format(
			__('paid batches')
		)
	}
	return null
}
