import { describe, expect, it } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { readFileSync } from 'node:fs'
import { routes } from '@/routes'

const sidebarSource = readFileSync('src/utils/index.js', 'utf8')
const pageSource = readFileSync('src/pages/Students.vue', 'utf8')

describe('students management page', () => {
	it('is reachable at /students', () => {
		const router = createRouter({ history: createMemoryHistory(), routes })
		const resolved = router.resolve('/students')
		expect(resolved.name).toBe('Students')
		expect(resolved.matched).toHaveLength(1)
	})

	it('is linked from the moderator sidebar', () => {
		expect(sidebarSource).toContain("label: 'Students'")
		expect(sidebarSource).toContain("to: 'Students'")
		expect(sidebarSource).toContain(
			'condition: () => userResource?.data?.is_moderator'
		)
	})

	it('reuses the member list with the student role fixed', () => {
		expect(pageSource).toContain('default-role="LMS Student"')
		expect(pageSource).toContain(':show-role-filter="false"')
		expect(pageSource).toContain(':edit-on-row-click="true"')
	})
})
