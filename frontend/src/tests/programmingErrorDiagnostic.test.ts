import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import Diagnostic from '@/components/ProgrammingErrorDiagnostic.vue'
import { submissionStatusLabel } from '@/utils/programmingSubmissionStatus'
it('shows Python traceback and the executed source line', () => {
 const wrapper = mount(Diagnostic, { props: { message: 'File "main.py", line 2\nZeroDivisionError: division by zero', code: 'n = 0\nprint(1 / n)' } })
 expect(wrapper.text()).toContain('ZeroDivisionError: division by zero')
 expect(wrapper.text()).toContain('第 2 行：print(1 / n)')
})
it('shows C++ compiler position and escapes submitted markup', () => {
 const wrapper = mount(Diagnostic, { props: { message: 'main.cpp:2:3: error: expected ;', code: 'int main() {\n<script>alert(1)</script>\n}' } })
 expect(wrapper.text()).toContain('第 2 行：<script>alert(1)</script>')
 expect(wrapper.find('script').exists()).toBe(false)
})
it('explains missing diagnostics instead of inventing a source location', () => {
 const wrapper = mount(Diagnostic, { props: { code: 'print(1)' } })
 expect(wrapper.text()).toContain('无法定位具体代码行')
})
it('translates both service and stored statuses', () => {
 expect(submissionStatusLabel('RUNTIME_ERROR')).toBe('执行出错')
 expect(submissionStatusLabel('Accepted')).toBe('通过')
 expect(submissionStatusLabel('Wrong Answer')).toBe('错误解答')
})
