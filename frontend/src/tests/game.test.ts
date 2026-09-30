import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { gameDocument, MAX_GAME_BYTES, readGameFile } from '@/utils/game'
import Game from '@/pages/Game.vue'
import GameDetail from '@/pages/GameDetail.vue'
import GameEditor from '@/components/GameEditor.vue'
import { reactive } from 'vue'
const { api, sidebar, navigate } = vi.hoisted(() => ({
	api: vi.fn(),
	sidebar: vi.fn(),
	navigate: vi.fn(),
}))
vi.mock('vue-router', () => ({ useRouter: () => ({ push: navigate }) }))
const visibility = reactive({ data: { game: 1 } })
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
	useSettings: () => ({
		loadSidebarSettings: sidebar,
		sidebarSettings: visibility,
	}),
}))
const html =
	'<html><body><button onclick="this.textContent=42">Play</button></body></html>'
let enabled = false
let manager = true
beforeEach(() => {
	enabled = false
	manager = true
	api.mockReset()
	navigate.mockReset()
	visibility.data.game = 1
	api.mockImplementation(async (method, args) => {
		if (method.endsWith('get_game_settings'))
			return { can_manage: manager, enabled }
		if (method.endsWith('set_game_enabled')) {
			enabled = !!args.enabled
			return { can_manage: manager, enabled }
		}
		if (method.endsWith('get_games'))
			return [{ name: 'test', title: 'Demo', filename: 'demo.html' }]
		if (method.endsWith('get_game'))
			return { name: 'test', title: 'Demo', html }
	})
})
describe('Game', () => {
	it('lets teachers toggle visibility and navigate to the game page', async () => {
		const w = mount(Game)
		await flushPromises()
		await w.get('input[type=checkbox]').setValue(true)
		await flushPromises()
		expect(api).toHaveBeenCalledWith('lms.lms.game.set_game_enabled', {
			enabled: 1,
		})
		await w.get('button h2').trigger('click')
		await flushPromises()
		expect(navigate).toHaveBeenCalledWith({
			name: 'GameDetail',
			params: { gameId: 'test' },
		})
		expect(w.find('iframe').exists()).toBe(false)
		w.unmount()
	})
	it('hides games and upload controls from students when disabled', async () => {
		manager = false
		const w = mount(Game)
		await flushPromises()
		expect(w.text()).toContain('教师尚未开放')
		expect(w.find('input').exists()).toBe(false)
		expect(api).not.toHaveBeenCalledWith('lms.lms.game.get_games')
		w.unmount()
	})
	it('keeps the saved toggle value when saving fails', async () => {
		const w = mount(Game)
		await flushPromises()
		api.mockRejectedValueOnce(new Error('failed'))
		await w.get('input[type=checkbox]').setValue(true)
		await flushPromises()
		expect(
			(w.get('input[type=checkbox]').element as HTMLInputElement).checked
		).toBe(false)
		expect(w.get('[role=alert]').text()).toContain('保存失败')
		w.unmount()
	})
	it('uploads the selected file and refreshes game cards', async () => {
		const w = mount(Game)
		await flushPromises()
		const input = w.get('input[type=file]')
		Object.defineProperty(input.element, 'files', {
			value: [new File([html], 'demo.html')],
		})
		await input.trigger('change')
		await w.get('form').trigger('submit')
		await vi.waitFor(() =>
			expect(api).toHaveBeenCalledWith(
				'lms.lms.game.upload_game',
				expect.objectContaining({ filename: 'demo.html' })
			)
		)
		await flushPromises()
		expect(w.text()).toContain('上传成功')
		expect(w.text()).toContain('Demo')
		w.unmount()
	})
})
describe('HTML game files', () => {
	it('preserves UTF-8 HTML and scripts through upload encoding', async () => {
		const source = '<html><script>const 名字="游戏"</script></html>'
		expect(
			Buffer.from(
				await readGameFile(new File([source], 'game.HTML')),
				'base64'
			).toString('utf8')
		).toBe(source)
	})
	it('rejects unsupported, empty and oversized files', async () => {
		await expect(readGameFile(new File(['x'], 'game.exe'))).rejects.toThrow(
			'HTML'
		)
		await expect(readGameFile(new File([], 'game.html'))).rejects.toThrow(
			'不能为空'
		)
		await expect(
			readGameFile(new File([new Uint8Array(MAX_GAME_BYTES + 1)], 'game.html'))
		).rejects.toThrow('5 MB')
	})
	it('places the content policy before game code and preserves standards mode', () => {
		const doc = gameDocument('<!DOCTYPE html>' + html)
		expect(doc.startsWith('<!doctype html><meta')).toBe(true)
		expect(doc.match(/<!doctype/gi)).toHaveLength(1)
		expect(doc).toContain("connect-src 'none'")
	})
})

describe('Game detail page', () => {
	it('loads a game directly, isolates scripts, restarts and returns to the list', async () => {
		const w = mount(GameDetail, { props: { gameId: 'test' } })
		await flushPromises()
		expect(api).toHaveBeenCalledWith('lms.lms.game.get_game', { name: 'test' })
		expect(w.get('iframe').attributes('sandbox')).toBe(
			'allow-scripts allow-pointer-lock'
		)
		expect(w.get('iframe').attributes('srcdoc')).toContain(html)
		const frame = w.get('iframe').element
		await w
			.findAll('button')
			.find((b) => b.text() === '重新开始')!
			.trigger('click')
		expect(w.get('iframe').element).not.toBe(frame)
		await w
			.findAll('button')
			.find((b) => b.text() === '返回游戏列表')!
			.trigger('click')
		expect(navigate).toHaveBeenCalledWith({ name: 'Game' })
		w.unmount()
	})
	it('rejects a disabled student deep link without fetching HTML', async () => {
		manager = false
		const w = mount(GameDetail, { props: { gameId: 'test' } })
		await flushPromises()
		expect(w.text()).toContain('教师尚未开放')
		expect(api).not.toHaveBeenCalledWith('lms.lms.game.get_game', {
			name: 'test',
		})
		w.unmount()
	})
	it('removes the player on realtime revocation', async () => {
		manager = false
		enabled = true
		const w = mount(GameDetail, { props: { gameId: 'test' } })
		await flushPromises()
		expect(w.find('iframe').exists()).toBe(true)
		visibility.data.game = 0
		await flushPromises()
		expect(w.find('iframe').exists()).toBe(false)
		expect(w.text()).toContain('教师尚未开放')
		w.unmount()
	})
	it('shows a recoverable error for a missing game', async () => {
		api.mockImplementation(async (method) => {
			if (method.endsWith('get_game_settings'))
				return { can_manage: true, enabled: false }
			throw new Error('not found')
		})
		const w = mount(GameDetail, { props: { gameId: 'missing' } })
		await flushPromises()
		expect(w.get('[role=alert]').text()).toContain('无法打开游戏')
		expect(w.find('iframe').exists()).toBe(false)
		w.unmount()
	})
	it('discards a delayed game response after access is revoked', async () => {
		manager = false
		enabled = true
		let resolveGame: (value: unknown) => void = () => {}
		api.mockImplementation(async (method) => {
			if (method.endsWith('get_game_settings'))
				return { can_manage: false, enabled: true }
			return new Promise((resolve) => {
				resolveGame = resolve
			})
		})
		const w = mount(GameDetail, { props: { gameId: 'test' } })
		await flushPromises()
		visibility.data.game = 0
		await flushPromises()
		resolveGame({ name: 'test', title: 'Demo', html })
		await flushPromises()
		expect(w.find('iframe').exists()).toBe(false)
		w.unmount()
	})
})

describe('Teacher game management', () => {
	it('renders a default background and teacher actions, and cancels deletion', async () => {
		const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
		const w = mount(Game)
		await flushPromises()
		expect(w.find('.game-cover').exists()).toBe(true)
		await w
			.findAll('button')
			.find((b) => b.text() === '删除')!
			.trigger('click')
		expect(api).not.toHaveBeenCalledWith(
			'lms.lms.game.delete_game',
			expect.anything()
		)
		confirm.mockRestore()
		w.unmount()
	})
	it('deletes a confirmed game without navigating into it', async () => {
		const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true)
		const w = mount(Game)
		await flushPromises()
		await w
			.findAll('button')
			.find((b) => b.text() === '删除')!
			.trigger('click')
		await flushPromises()
		expect(api).toHaveBeenCalledWith('lms.lms.game.delete_game', {
			name: 'test',
		})
		expect(w.find('.game-card').exists()).toBe(false)
		expect(navigate).not.toHaveBeenCalled()
		confirm.mockRestore()
		w.unmount()
	})
	it('hides management actions from students', async () => {
		manager = false
		enabled = true
		const w = mount(Game)
		await flushPromises()
		for (const text of ['编辑', '下载', '删除'])
			expect(w.findAll('button').some((b) => b.text() === text)).toBe(false)
		w.unmount()
	})
	it('saves name and description while preserving the current cover', async () => {
		const w = mount(GameEditor, {
			props: {
				modelValue: true,
				game: {
					name: 'test',
					title: 'Old',
					cover_image: 'data:image/jpeg;base64,abc',
				},
			},
		})
		await w.get('input:not([type=file])').setValue('New name')
		await w.get('textarea').setValue('New description')
		await w
			.findAll('button')
			.find((b) => b.text() === '保存修改')!
			.trigger('click')
		await flushPromises()
		expect(api).toHaveBeenCalledWith('lms.lms.game.update_game', {
			name: 'test',
			title: 'New name',
			description: 'New description',
			cover: null,
		})
		expect(w.emitted('saved')).toHaveLength(1)
		w.unmount()
	})
	it('clears the cover explicitly and keeps the dialog open when save fails', async () => {
		const w = mount(GameEditor, {
			props: {
				modelValue: true,
				game: {
					name: 'test',
					title: 'Old',
					cover_image: 'data:image/jpeg;base64,abc',
				},
			},
		})
		await w
			.findAll('button')
			.find((b) => b.text() === '恢复默认封面')!
			.trigger('click')
		api.mockRejectedValueOnce(new Error('failure'))
		await w
			.findAll('button')
			.find((b) => b.text() === '保存修改')!
			.trigger('click')
		await flushPromises()
		expect(api).toHaveBeenCalledWith(
			'lms.lms.game.update_game',
			expect.objectContaining({ cover: '' })
		)
		expect(w.get('[role=alert]').text()).toContain('保存失败')
		expect(w.emitted('saved')).toBeUndefined()
		w.unmount()
	})
})

describe('ZIP games', () => {
	it('accepts ZIP uploads up to 20 MB and rejects larger files', async () => {
		const file = new File(['zip'], 'game.ZIP', { type: 'application/zip' })
		expect(Buffer.from(await readGameFile(file), 'base64').toString()).toBe(
			'zip'
		)
		await expect(
			readGameFile(new File([new Uint8Array(20 * 1024 * 1024 + 1)], 'game.zip'))
		).rejects.toThrow('20 MB')
	})
	it('uses the authenticated package URL in the isolated iframe', async () => {
		api.mockImplementation(async (method) =>
			method.endsWith('get_game_settings')
				? { can_manage: true, enabled: false }
				: {
						name: 'zip',
						title: 'ZIP Game',
						url: '/game-assets/token/game/index.html',
					}
		)
		const w = mount(GameDetail, { props: { gameId: 'zip' } })
		await flushPromises()
		expect(w.get('iframe').attributes('src')).toBe(
			'/game-assets/token/game/index.html'
		)
		expect(w.get('iframe').attributes('srcdoc')).toBeUndefined()
		expect(w.get('iframe').attributes('sandbox')).not.toContain(
			'allow-same-origin'
		)
		w.unmount()
	})
})
