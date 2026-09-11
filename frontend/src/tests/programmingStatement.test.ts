import { nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ProgrammingStatement from '@/components/ProgrammingStatement.vue'

const link = '<p><a href="/api/method/lms.lms.problem_package.api.download_statement?version_id=test">Download TeX statement</a></p>'
describe('programming statement', () => {
	it('renders imported TeX with display math and multiline examples without the download link', () => {
		const wrapper = mount(ProgrammingStatement, { props: { icpc: true, html: link + String.raw`<pre>\begin{document}题目描述
$$x^2$$
\begin{verbatim}1 2
3 4\end{verbatim}\end{document}</pre>` } })
		expect(wrapper.text()).toContain('题目描述')
		expect(wrapper.text()).not.toContain('Download')
		expect(wrapper.find('.katex-display').exists()).toBe(true)
		expect(wrapper.find('pre').text()).toBe('1 2\n3 4')
		expect(wrapper.find('a').exists()).toBe(false)
	})
	it('keeps PDF statements accessible without Download wording', async () => {
		const wrapper = mount(ProgrammingStatement, { props: { icpc: true, html: link.replace('TeX', 'PDF') } })
		await nextTick()
		expect(wrapper.find('a').text()).toBe('查看题面 PDF')
	})
	it('preserves ordinary HTML statements and code examples', async () => {
		const wrapper = mount(ProgrammingStatement, { props: { html: '<p>题目</p><pre>$code$</pre>' } })
		await nextTick()
		expect(wrapper.find('p').text()).toBe('题目')
		expect(wrapper.find('pre').text()).toBe('$code$')
	})
})
