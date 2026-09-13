import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import {
	editorDefaults,
	readEditorPreferences,
	editorPreferencesKey,
} from '@/utils/editorPreferences'
vi.mock('frappe-ui', () => ({
	Dialog: { template: '<div><slot /></div>', props: ['open', 'title', 'size'] },
}))
import Settings from '@/components/ProgrammingEditorSettings.vue'
describe('programming editor preferences', () => {
	beforeEach(() => localStorage.clear())
	it('recovers from corrupt and invalid saved settings', () => {
		localStorage.setItem(editorPreferencesKey, '{')
		expect(readEditorPreferences()).toEqual(editorDefaults)
		localStorage.setItem(
			editorPreferencesKey,
			JSON.stringify({
				theme: 'invalid',
				fontSize: 900,
				tabSize: 0,
				wrap: false,
				keyboard: 'invalid',
			}),
		)
		expect(readEditorPreferences()).toEqual({ ...editorDefaults, wrap: false })
	})
	it.each([['dark', 'Menlo, monospace'], ['monaco', 'Monaco, monospace'], ['monaco', 'JetBrains Mono, monospace']])('restores %s and %s after reload', (theme, fontFamily) => {
		localStorage.setItem(editorPreferencesKey, JSON.stringify({ theme, fontSize: 24, fontFamily }))
		expect(readEditorPreferences()).toMatchObject({ theme, fontSize: 24, fontFamily })
	})
	it('changes real model values and exposes only the two requested menus', async () => {
		const model = { ...editorDefaults }
		const wrapper = mount(Settings, {
			props: { modelValue: model, open: true },
		})
		expect(wrapper.findAll('nav button').map((b) => b.text())).toEqual([
			'代码编辑器',
			'键盘快捷键',
		])
		await wrapper.find('[aria-label="字体大小"]').setValue('20')
		expect(model.fontSize).toBe(20)
		await wrapper.find('[aria-label="主题"]').setValue('dark')
		expect(model.theme).toBe('dark')
		await wrapper.find('[aria-label="主题"]').setValue('monaco')
		expect(model.theme).toBe('monaco')
		await wrapper.find('[aria-label="字体"]').setValue('Monaco, monospace')
		expect(model.fontFamily).toBe('Monaco, monospace')
		await wrapper.find('[aria-label="字体"]').setValue('JetBrains Mono, monospace')
		expect(model.fontFamily).toBe('JetBrains Mono, monospace')
		await wrapper.findAll('input')[1].setValue(false)
		expect(model.wrap).toBe(false)
		await wrapper.findAll('nav button')[1].trigger('click')
		await nextTick()
		await wrapper.findAll('input')[0].setValue(false)
		expect(model.runShortcut).toBe(false)
		expect(wrapper.text()).toContain('代码格式化')
		wrapper.unmount()
	})
})
