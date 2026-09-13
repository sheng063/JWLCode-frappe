import { mount } from '@vue/test-utils'
import { defineComponent, nextTick, ref } from 'vue'
import { describe, expect, it, vi } from 'vitest'
import ace from 'ace-builds'
import { editorDefaults } from '@/utils/editorPreferences'
vi.mock('frappe-ui', () => ({ Button: { template: '<button />' } }))
vi.mock('@/components/Form/labeling', () => ({
	InputDescription: {},
	InputError: {},
	InputLabel: {},
	useInputLabeling: () => ({ inputId: 'test-code-editor' }),
}))
import CodeEditor from '@/components/Controls/CodeEditor.vue'
describe('Ace editor integration', () => {
	it('retains the complete template after reset through a two-way model', async () => {
		const template = '#include <bits/stdc++.h>\nusing namespace std;\nint main() {\n    return 0;\n}\n'
		const Host = defineComponent({
			components: { CodeEditor },
			setup() {
				return { code: ref('int main(){return 42;}'), template, preferences: editorDefaults }
			},
			template: `<CodeEditor v-model="code" type="C++" :preferences="preferences" :autofocus="false" /><button @click="code = template">Reset</button>`,
		})
		const wrapper = mount(Host, { attachTo: document.body })
		const editor = ace.edit(wrapper.find('#test-code-editor').element as HTMLElement)
		await wrapper.find('button').trigger('click')
		await nextTick()
		expect(editor.getValue()).toBe(template)
		expect(wrapper.vm.code).toBe(template)
		expect(wrapper.findComponent(CodeEditor).emitted('update:modelValue')).toBeUndefined()
		await wrapper.find('button').trigger('click')
		expect(editor.getValue()).toBe(template)
		wrapper.unmount()
	})

	it('keeps identical pasted code after Ace emits removal and insertion', async () => {
		const source = 'int main(){return 0;}'
		const Host = defineComponent({
			components: { CodeEditor },
			setup: () => ({ code: ref(source), preferences: editorDefaults }),
			template: `<CodeEditor v-model="code" type="C++" :preferences="preferences" :autofocus="false" />`,
		})
		const wrapper = mount(Host, { attachTo: document.body })
		const editor = ace.edit(wrapper.find('#test-code-editor').element as HTMLElement)
		editor.setValue(source, -1)
		await nextTick()
		expect(wrapper.vm.code).toBe(source)
		expect(editor.getValue()).toBe(source)
		wrapper.unmount()
	})

	it.each([['dark', 'twilight'], ['monaco', 'monaco']])('applies %s preferences live and keeps formatting undoable', async (theme, aceTheme) => {
		const wrapper = mount(CodeEditor, {
			attachTo: document.body,
			props: {
				modelValue: 'x=1',
				type: 'Python',
				preferences: { ...editorDefaults },
				autofocus: false,
			},
		})
		const editor = ace.edit(
			wrapper.find('#test-code-editor').element as HTMLElement,
		)
		await wrapper.setProps({
			preferences: {
				...editorDefaults,
				theme,
				fontFamily: 'Monaco, monospace',
				fontSize: 20,
				tabSize: 2,
				wrap: false,
				relativeLineNumbers: true,
			},
		})
		expect(editor.getOption('fontSize')).toBe(20)
		expect(editor.getOption('fontFamily')).toBe('Monaco, monospace')
		if (theme === 'monaco') {
			expect(editor.container.classList.contains('ace-monaco')).toBe(true)
			expect(ace.require('ace/theme/monaco').cssText).toContain('#a31515')
		}
		expect(editor.getTheme()).toBe(`ace/theme/${aceTheme}`)
		await wrapper.setProps({ modelValue: 'x=2' })
		expect(editor.getTheme()).toBe(`ace/theme/${aceTheme}`)
		await wrapper.setProps({ modelValue: 'x=1' })
		expect(editor.session.getTabSize()).toBe(2)
		expect(editor.session.getUseWrapMode()).toBe(false)
		expect(editor.getOption('relativeLineNumbers')).toBe(true)
		;(wrapper.vm as any).replaceCode('x = 1\n')
		await nextTick()
		expect(editor.getValue()).toBe('x = 1\n')
		expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['x = 1\n'])
		editor.undo()
		expect(editor.getValue()).toBe('x=1')
		wrapper.unmount()
	})
})
