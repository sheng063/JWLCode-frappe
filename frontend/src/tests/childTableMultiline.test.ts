import { afterEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, mount } from '@vue/test-utils'
import { defineComponent, ref } from 'vue'
import ChildTable from '@/components/Controls/ChildTable.vue'

vi.stubGlobal('__', (text: string) => text)
vi.mock('frappe-ui', () => ({ Button: { template: '<button><slot /></button>' } }))
enableAutoUnmount(afterEach)
const Host = defineComponent({
	components: { ChildTable },
	setup() {
		const samples = ref([{ input: '1\n2\n', expected_output: '3\n\n4\n' }])
		const hidden = ref([{ input: '5\n6', expected_output: '11' }])
		return { samples, hidden }
	},
	template: `<div>
		<ChildTable v-model="samples" :columns="['Input', 'Expected Output']" multiline />
		<ChildTable v-model="hidden" :columns="['Input', 'Expected Output']" multiline />
	</div>`,
})
const global = { mocks: { __: (s: string) => s } }
describe('multiline test cases', () => {
	it('preserves blank lines, indentation and long output in both tables', async () => {
		const wrapper = mount(Host, { global })
		const cells = wrapper.findAll('textarea')
		expect(cells.map((cell) => cell.element.value)).toEqual(['1\n2\n', '3\n\n4\n', '5\n6', '11'])
		const input = '  first\n\nsecond\n'
		const expected_output = 'a\nb\n'.repeat(100)
		for (const offset of [0, 2]) {
			await cells[offset].setValue(input)
			await cells[offset + 1].setValue(expected_output)
		}
		expect(wrapper.vm.samples[0]).toEqual({ input, expected_output })
		expect(wrapper.vm.hidden[0]).toEqual({ input, expected_output })
	})
	it('focuses the new textarea in the correct table', async () => {
		const wrapper = mount(Host, { attachTo: document.body, global })
		const tables = wrapper.findAllComponents(ChildTable)
		await tables[1].findAll('button').find((button) => button.text() === 'Add Row')!.trigger('click')
		expect(wrapper.vm.hidden).toHaveLength(2)
		expect(wrapper.vm.samples).toHaveLength(1)
		expect(document.activeElement).toBe(tables[1].findAll('textarea')[2].element)
	})
	it('keeps other tables single line by default', () => {
		const wrapper = mount(ChildTable, { props: { columns: ['Input'], modelValue: [{ input: 'value' }] }, global })
		expect(wrapper.find('input').element.value).toBe('value')
		expect(wrapper.find('textarea').exists()).toBe(false)
	})
})
