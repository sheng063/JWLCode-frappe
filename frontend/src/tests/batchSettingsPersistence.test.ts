import { describe, expect, it } from 'vitest'
import {
	batchSettingsPayload,
	normalizeBatchDoc,
} from '@/utils/batchForm'
import type { LMSBatch } from '@/types/lms/LMSBatch'

const batch = (): LMSBatch =>
	({
		name: 'B1',
		title: 'Batch 1',
		start_time: '0:00:00',
		end_time: '9:30:00',
		published: 1,
		paid_batch: 0,
		allow_self_enrollment: 1,
		certification: 0,
		evaluation: 1,
		courses: [{ course: 'COURSE-OLD' }],
		assessment: [{ assessment_name: 'QUIZ-OLD' }],
		timetable: [{ date: '2026-09-01' }],
		timetable_legends: [{ title: 'Old timetable' }],
		instructors: [{ instructor: 'old@example.com' }],
	} as unknown as LMSBatch)

describe('batch settings persistence boundaries', () => {
	it('normalizes server display values without mutating the fetched document', () => {
		const source = batch()
		const normalized = normalizeBatchDoc(source)

		expect(normalized.start_time).toBe('00:00')
		expect(normalized.end_time).toBe('09:30')
		expect(normalized.published).toBe(true)
		expect(normalized.paid_batch).toBe(false)
		expect(source.start_time).toBe('0:00:00')
		expect(normalizeBatchDoc(normalized)).toEqual(normalized)
	})

	it('never sends independently managed child tables from a stale settings snapshot', () => {
		const payload = batchSettingsPayload(batch(), [
			'fresh-instructor@example.com',
		])

		expect(payload.title).toBe('Batch 1')
		expect(payload.instructors).toEqual([
			{ instructor: 'fresh-instructor@example.com' },
		])
		expect(payload).not.toHaveProperty('courses')
		expect(payload).not.toHaveProperty('assessment')
		expect(payload).not.toHaveProperty('timetable')
		expect(payload).not.toHaveProperty('timetable_legends')
	})
})

