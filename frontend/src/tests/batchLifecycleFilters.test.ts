import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'

const source = readFileSync('src/pages/Batches/Batches.vue', 'utf8')

describe('batch lifecycle filters', () => {
	it('opens staff on the active batches tab', () => {
		expect(source).toContain("is_student.value ? 'all' : 'active'")
		expect(source).toContain("label: __('Active'), value: 'active'")
	})

	it('keeps published batches visible until their end date', () => {
		expect(source).toContain("filters.value['end_date'] = ['>='")
		expect(source).not.toContain("filters.value['start_date'] = ['>='")
	})

	it('archives batches by end date rather than start date', () => {
		expect(source).toContain("filters.value['end_date'] = ['<='")
		expect(source).not.toContain("filters.value['start_date'] = ['<='")
	})
})
