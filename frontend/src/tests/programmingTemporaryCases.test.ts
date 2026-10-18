import { mount } from '@vue/test-utils'
import { defineComponent, ref } from 'vue'
import { expect, it } from 'vitest'
import Cases from '@/components/ProgrammingTestCases.vue'
function host() {
 return mount(defineComponent({
  components: { Cases },
  setup: () => ({ temporary: ref([]), disabled: ref(false), official: [{ input: '1 2', expected_output: '3' }] }),
  template: '<Cases v-model="temporary" :official-cases="official" :disabled="disabled" />',
 }))
}
it('keeps official cases read only and only deletes temporary cases', async () => {
 const wrapper = host()
 expect(wrapper.find('textarea').exists()).toBe(false)
 expect(wrapper.find('[aria-label="删除当前临时用例"]').exists()).toBe(false)
 await wrapper.get('[aria-label="添加临时测试用例"]').trigger('click')
 await wrapper.get('[aria-label="临时用例输入"]').setValue('  4 5\n')
 await wrapper.get('[aria-label="临时用例标准输出"]').setValue('9\n')
 expect(wrapper.vm.temporary).toEqual([{ input: '  4 5\n', expected_output: '9\n' }])
 await wrapper.get('[aria-label="删除当前临时用例"]').trigger('click')
 expect(wrapper.vm.temporary).toEqual([])
 expect(wrapper.vm.official).toEqual([{ input: '1 2', expected_output: '3' }])
 expect(wrapper.text()).toContain('用例 1')
 wrapper.unmount()
})
it('selects an externally added case and prevents mutation while running', async () => {
 const wrapper = host()
 wrapper.vm.temporary = [{ input: 'failed', expected_output: 'answer' }] as any
 await wrapper.vm.$nextTick()
 expect((wrapper.get('[aria-label="临时用例输入"]').element as HTMLTextAreaElement).value).toBe('failed')
 wrapper.vm.disabled = true
 await wrapper.vm.$nextTick()
 expect(wrapper.get('[aria-label="临时用例输入"]').attributes('disabled')).toBeDefined()
 await wrapper.get('[aria-label="删除当前临时用例"]').trigger('click')
 await wrapper.get('[aria-label="添加临时测试用例"]').trigger('click')
 expect(wrapper.vm.temporary).toHaveLength(1)
 wrapper.unmount()
 const refreshed = host()
 expect(refreshed.vm.temporary).toHaveLength(0)
 refreshed.unmount()
})
