import { describe, expect, it } from 'vitest'
import {
	isProgrammingLesson,
	hasMixedLessonContent,
	lessonBlocks,
} from '@/utils/lessonType'
const program = { type: 'program', data: { exercise: 'exercise-1' } }
const text = { type: 'markdown', data: { text: 'Hello' } }
const lesson = (blocks: any[], lesson_type = '') => ({
	content: JSON.stringify({ blocks }),
	lesson_type,
})
describe('lesson content types', () => {
	it('recognizes legacy programming lessons and empty programming drafts', () => {
		expect(isProgrammingLesson(lesson([program]))).toBe(true)
		expect(isProgrammingLesson(lesson([], 'Programming'))).toBe(true)
		expect(isProgrammingLesson(lesson([], 'Text'))).toBe(false)
	})
	it('does not put mixed legacy content in the programming-only view', () => {
		expect(isProgrammingLesson(lesson([program, text]))).toBe(false)
		expect(hasMixedLessonContent(lesson([program, text]))).toBe(true)
	})
	it('rejects content that conflicts with the selected type', () => {
		expect(hasMixedLessonContent(lesson([program], 'Text'))).toBe(true)
		expect(hasMixedLessonContent(lesson([text], 'Programming'))).toBe(true)
		expect(hasMixedLessonContent(lesson([text], 'Text'))).toBe(false)
	})
	it('allows empty editor padding but rejects media and legacy content', () => {
		expect(
			isProgrammingLesson(
				lesson([program, { type: 'paragraph', data: { text: '<br>&nbsp; ' } }])
			)
		).toBe(true)
		expect(
			hasMixedLessonContent(
				lesson([program, { type: 'upload', data: { file: 'video.mp4' } }])
			)
		).toBe(true)
		expect(
			hasMixedLessonContent({ ...lesson([program]), body: 'Legacy text' })
		).toBe(true)
	})
	it('handles malformed content safely', () => {
		for (const content of ['null', '{', '{"blocks":{}}', '{"blocks":[null]}'])
			expect(lessonBlocks(content)).toEqual([])
	})
})

it('does not treat raw text as an empty programming lesson', () => {
	for (const content of ['Hello', '"Hello"', '{"blocks":"Hello"}']) {
		expect(isProgrammingLesson({ content, lesson_type: 'Programming' })).toBe(
			false
		)
		expect(hasMixedLessonContent({ content, lesson_type: 'Programming' })).toBe(
			true
		)
	}
})
