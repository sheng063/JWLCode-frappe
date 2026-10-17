import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import Game from '@/pages/Game.vue'
import GameDetail from '@/pages/GameDetail.vue'
import GameAccessManager from '@/components/GameAccessManager.vue'
const { api, push } = vi.hoisted(() => ({ api: vi.fn(), push: vi.fn() }))
vi.mock('@headlessui/vue', () => ({
	Dialog: { props: ['open'], template: '<div v-if="open"><slot /></div>' },
	DialogPanel: { template: '<div><slot /></div>' },
	DialogTitle: { template: '<h2><slot /></h2>' },
	DialogDescription: { template: '<p><slot /></p>' },
}))
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))
vi.mock('frappe-ui', () => ({
	call: api,
	Button: { template: '<button><slot /></button>' },
	Dialog: {
		props: ['modelValue'],
		template:
			'<div v-if="modelValue"><slot name="body-content" /><slot name="actions" /></div>',
	},
}))
vi.mock('@/stores/settings', () => ({
	useSettings: () => ({ loadSidebarSettings: vi.fn() }),
}))
let access: any
const settings = () => ({ enabled: true, can_manage: false, access })
const wrappers: any[] = []
afterEach(() => {
	wrappers.forEach((w) => w.unmount())
	wrappers.length = 0
})
function render(component: any, options = {}) {
	const w = mount(component, options)
	wrappers.push(w)
	return w
}
beforeEach(() => {
	api.mockReset()
	push.mockReset()
	access = {
		can_enter: false,
		reason_code: 'incomplete',
		required_course: 'course-a',
		course_title: '基础课程',
		completed_lessons: 1,
		total_lessons: 2,
		message: '完成指定课程的全部课时后，即可进入 Game。',
	}
	api.mockImplementation(async (method, args) => {
		if (method.endsWith('get_game_settings')) return settings()
		if (method.endsWith('get_games')) return [{ name: 'game-a', title: 'Demo' }]
		if (method.endsWith('get_game'))
			return { title: 'Demo', html: '<html>game</html>' }
		if (method.endsWith('get_course_lessons'))
			return [{ name: 'lesson-a', title: '课时 A', chapter_title: '章节一' }]
		if (method.endsWith('get_access_options'))
			return {
				courses: [{ name: 'course-a', title: '基础课程' }],
				batches: [],
				can_configure: true,
			}
		if (method.endsWith('get_students'))
			return {
				total: 1,
				rows: [
					{
						student: 'a@example.com',
						full_name: '学生 A',
						...access,
						access_mode: 'Automatic',
						course_override: '',
						reason: '',
					},
				],
			}
		if (method.endsWith('bulk_student_access'))
			return { updated: args.students.length }
	})
})
describe('course-gated Game', () => {
	it('shows progress and course navigation without fetching games', async () => {
		const w = render(Game)
		await flushPromises()
		expect(w.text()).toContain('1 / 2 课时')
		expect(api).not.toHaveBeenCalledWith('lms.lms.game.get_games')
		await w
			.findAll('button')
			.find((b) => b.text() === '继续学习')!
			.trigger('click')
		expect(push).toHaveBeenCalledWith({
			name: 'CourseDetail',
			params: { courseName: 'course-a' },
		})
		access = { ...access, can_enter: true, reason_code: 'completed' }
		window.dispatchEvent(new Event('lms-game-access-changed'))
		await flushPromises()
		expect(w.find('article').exists()).toBe(true)
	})
	it('blocks direct game routes and removes a running iframe on revocation', async () => {
		const w = render(GameDetail, { props: { gameId: 'game-a' } })
		await flushPromises()
		expect(w.find('iframe').exists()).toBe(false)
		expect(api).not.toHaveBeenCalledWith('lms.lms.game.get_game', {
			name: 'game-a',
		})
		access = { ...access, can_enter: true }
		window.dispatchEvent(new Event('lms-game-access-changed'))
		await flushPromises()
		expect(w.find('iframe').exists()).toBe(true)
		access = {
			...access,
			can_enter: false,
			reason_code: 'denied',
			message: '教师暂未允许你进入 Game，请联系教师。',
		}
		window.dispatchEvent(new Event('lms-game-access-changed'))
		await flushPromises()
		expect(w.find('iframe').exists()).toBe(false)
		expect(w.text()).toContain('教师暂未允许')
	})
	it('saves global rules, individual overrides and bulk reset', async () => {
		const w = render(GameAccessManager, {
			props: {
				settings: {
					require_course_completion: false,
					default_required_course: '',
				},
			},
		})
		await flushPromises()
		const rule = w.findAll('form')[0]
		await rule.find('input').setValue(true)
		await rule.find('select').setValue('course-a')
		await rule.trigger('submit')
		await flushPromises()
		expect(api).toHaveBeenCalledWith('lms.lms.game_access.set_course_rule', {
			required: 1,
			course: 'course-a',
			lesson: '',
		})
		await w
			.findAll('button')
			.find((b) => b.text() === '设置')!
			.trigger('click')
		const edit = w.findAll('form').at(-1)!
		await edit.get('input[value=Allow]').setValue(true)
		await edit.find('textarea').setValue('奖励')
		await edit.trigger('submit')
		await flushPromises()
		expect(api).toHaveBeenCalledWith(
			'lms.lms.game_access.save_student_access',
			{
				student: 'a@example.com',
				required_course: '',
				required_lesson: '',
				access_mode: 'Allow',
				reason: '奖励',
			},
		)
		await w.get('input[aria-label="选择本页学生"]').setValue(true)
		await w
			.findAll('button')
			.find((b) => b.text() === '恢复默认自动规则')!
			.trigger('click')
		await flushPromises()
		expect(api).toHaveBeenCalledWith(
			'lms.lms.game_access.bulk_student_access',
			{
				students: ['a@example.com'],
				action: 'reset',
				required_course: '',
				required_lesson: '',
			},
		)
	})
})

describe('student access management UI', () => {
	async function openEditor() {
		const w = render(GameAccessManager, {
			props: {
				settings: { enabled: true, default_required_course: 'course-a' },
			},
		})
		await flushPromises()
		await w
			.findAll('button')
			.find((b) => b.text() === '设置')!
			.trigger('click')
		return w
	}
	it('keeps the saved status separate from draft radio and course changes, and cancels without saving', async () => {
		const w = await openEditor()
		expect(w.get('.student-summary').text()).toContain('当前未解锁')
		await w.get('input[value=Allow]').setValue(true)
		expect(w.get('.student-summary').text()).toContain('当前未解锁')
		await w.get('select[aria-label="学生解锁课程"]').setValue('course-a')
		await w.get('textarea').setValue('draft')
		await w
			.findAll('button')
			.find((b) => b.text() === '取消')!
			.trigger('click')
		expect(w.find('.student-drawer').exists()).toBe(false)
		expect(api).not.toHaveBeenCalledWith(
			'lms.lms.game_access.save_student_access',
			expect.anything(),
		)
		await w
			.findAll('button')
			.find((b) => b.text() === '设置')!
			.trigger('click')
		expect((w.get('textarea').element as HTMLTextAreaElement).value).toBe('')
		expect(
			(w.get('input[value=Automatic]').element as HTMLInputElement).checked,
		).toBe(true)
	})
	it('preserves a failed student draft and shows the error inside the drawer', async () => {
		const w = await openEditor()
		await w.get('input[value=Deny]').setValue(true)
		await w.get('textarea').setValue('课堂安排')
		api.mockRejectedValueOnce({ messages: ['保存失败，请重试'] })
		await w.get('#student-access-form').trigger('submit')
		await flushPromises()
		expect(w.get('.student-drawer [role=alert]').text()).toContain('保存失败')
		expect((w.get('textarea').element as HTMLTextAreaElement).value).toBe(
			'课堂安排',
		)
		expect(
			(w.get('input[value=Deny]').element as HTMLInputElement).checked,
		).toBe(true)
	})
	it('shows bulk actions only for selected students and submits the chosen course', async () => {
		const w = render(GameAccessManager, {
			props: { settings: { enabled: true } },
		})
		await flushPromises()
		expect(w.find('.bulk-bar').exists()).toBe(false)
		await w.get('input[aria-label="选择本页学生"]').setValue(true)
		expect(w.find('.bulk-bar').exists()).toBe(true)
		await w.get('select[aria-label="批量指定课程"]').setValue('course-a')
		await w
			.findAll('button')
			.find((b) => b.text() === '批量指定课程')!
			.trigger('click')
		await flushPromises()
		expect(api).toHaveBeenCalledWith(
			'lms.lms.game_access.bulk_student_access',
			{
				students: ['a@example.com'],
				action: 'assign_course',
				required_course: 'course-a',
				required_lesson: '',
			},
		)
		expect(w.find('.bulk-bar').exists()).toBe(false)
	})
	it('shows read-only global rules for teachers without configuration permission', async () => {
		const implementation = api.getMockImplementation()!
		api.mockImplementation(async (method, args) =>
			method.endsWith('get_access_options')
				? { courses: [], batches: [], can_configure: false }
				: implementation(method, args),
		)
		const w = render(GameAccessManager, {
			props: { settings: { enabled: false, require_course_completion: true } },
		})
		await flushPromises()
		expect(w.find('.rules-form').exists()).toBe(false)
		expect(w.text()).toContain('学生入口已关闭')
		expect(w.find('.rule-readonly').exists()).toBe(true)
		expect(w.findAll('button').some((b) => b.text() === '设置')).toBe(true)
	})
})

describe('lesson unlock rules', () => {
	it('saves a default lesson and clears it when the course changes', async () => {
		const w = render(GameAccessManager, {
			props: {
				settings: {
					enabled: true,
					require_course_completion: true,
					default_required_course: 'course-a',
				},
			},
		})
		await flushPromises()
		await w.get('select[aria-label="默认解锁条件"]').setValue('lesson-a')
		await w.get('.rules-form').trigger('submit')
		await flushPromises()
		expect(api).toHaveBeenCalledWith('lms.lms.game_access.set_course_rule', {
			required: 1,
			course: 'course-a',
			lesson: 'lesson-a',
		})
		await w.get('select[aria-label="默认解锁课程"]').setValue('')
		expect(
			(w.get('select[aria-label="默认解锁条件"]').element as HTMLSelectElement)
				.value,
		).toBe('')
	})
	it('saves an individual lesson and can inherit the entire default rule', async () => {
		const w = render(GameAccessManager, {
			props: {
				settings: {
					enabled: true,
					default_required_course: 'course-a',
					default_required_lesson: 'lesson-a',
					default_lesson_title: '课时 A',
				},
			},
		})
		await flushPromises()
		await w
			.findAll('button')
			.find((b) => b.text() === '设置')!
			.trigger('click')
		await w.get('select[aria-label="学生解锁课程"]').setValue('course-a')
		await flushPromises()
		await w.get('select[aria-label="学生解锁条件"]').setValue('lesson-a')
		await w.get('#student-access-form').trigger('submit')
		await flushPromises()
		expect(api).toHaveBeenCalledWith(
			'lms.lms.game_access.save_student_access',
			expect.objectContaining({
				required_course: 'course-a',
				required_lesson: 'lesson-a',
			}),
		)
		await w
			.findAll('button')
			.find((b) => b.text() === '设置')!
			.trigger('click')
		expect(w.get('.student-drawer').text()).toContain(
			'继承默认解锁条件：指定课时：课时 A',
		)
		await w.get('#student-access-form').trigger('submit')
		await flushPromises()
		expect(api).toHaveBeenLastCalledWith(
			'lms.lms.game_access.get_students',
			expect.anything(),
		)
		expect(api).toHaveBeenCalledWith(
			'lms.lms.game_access.save_student_access',
			expect.objectContaining({ required_course: '', required_lesson: '' }),
		)
	})
	it('assigns a lesson in bulk', async () => {
		const w = render(GameAccessManager, {
			props: { settings: { enabled: true } },
		})
		await flushPromises()
		await w.get('input[aria-label="选择本页学生"]').setValue(true)
		await w.get('select[aria-label="批量指定课程"]').setValue('course-a')
		await flushPromises()
		await w.get('select[aria-label="批量解锁条件"]').setValue('lesson-a')
		await w
			.findAll('button')
			.find((b) => b.text() === '批量指定课程')!
			.trigger('click')
		await flushPromises()
		expect(api).toHaveBeenCalledWith(
			'lms.lms.game_access.bulk_student_access',
			{
				students: ['a@example.com'],
				action: 'assign_course',
				required_course: 'course-a',
				required_lesson: 'lesson-a',
			},
		)
	})
	it('shows the target lesson and unlocks the player after its completion', async () => {
		access = {
			...access,
			reason_code: 'incomplete_lesson',
			required_lesson: 'lesson-a',
			lesson_title: '课时 A',
			completed_lessons: 0,
			total_lessons: 1,
			message: '完成指定课时后，即可进入 Game。',
		}
		const w = render(GameDetail, { props: { gameId: 'game-a' } })
		await flushPromises()
		expect(w.text()).toContain('指定课时：课时 A')
		expect(w.text()).toContain('0 / 1 课时')
		expect(w.find('iframe').exists()).toBe(false)
		access = {
			...access,
			can_enter: true,
			reason_code: 'completed',
			completed_lessons: 1,
		}
		window.dispatchEvent(new Event('lms-game-access-changed'))
		await flushPromises()
		expect(w.find('iframe').exists()).toBe(true)
	})
})
