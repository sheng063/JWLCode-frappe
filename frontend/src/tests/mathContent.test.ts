import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { describe, expect, it } from 'vitest'
import MathContent from '@/components/MathContent.vue'

describe('MathContent', () => {
	it('renders all four delimiters and preserves code samples', async () => {
		const wrapper = mount(MathContent, { props: { html: String.raw`<p>$x^2$ and \(a_1\)</p><p>$$\frac{1}{2}$$</p><p>\[n^2\]</p><pre>$code$</pre><code>\(code\)</code>` } })
		await nextTick()
		expect(wrapper.findAll('.katex')).toHaveLength(4)
		expect(wrapper.findAll('.katex-display')).toHaveLength(2)
		expect(wrapper.find('pre').text()).toBe('$code$')
		expect(wrapper.find('code').text()).toBe(String.raw`\(code\)`)
	})

	it('renders asynchronously loaded and replaced content without duplicates', async () => {
		const wrapper = mount(MathContent)
		await wrapper.setProps({ html: '$x$' })
		expect(wrapper.findAll('.katex')).toHaveLength(1)
		await wrapper.setProps({ html: '$y$' })
		expect(wrapper.findAll('.katex')).toHaveLength(1)
		expect(wrapper.find('annotation').text()).toBe('y')
		await wrapper.setProps({ html: null })
		expect(wrapper.text()).toBe('')
	})

	it('sanitizes HTML and disables trusted LaTeX commands', async () => {
		const wrapper = mount(MathContent, { props: { html: String.raw`<img src=x onerror="alert(1)"><script>alert(1)</script>$\href{javascript:alert(1)}{click}$` } })
		await nextTick()
		expect(wrapper.find('script').exists()).toBe(false)
		expect(wrapper.find('img').attributes('onerror')).toBeUndefined()
		expect(wrapper.find('a').exists()).toBe(false)
	})

	it('keeps invalid formulas readable and continues rendering', async () => {
		const wrapper = mount(MathContent, { props: { html: String.raw`$\invalidcommand{x}$ and $y^2$` } })
		await nextTick()
		expect(wrapper.text()).toContain(String.raw`\invalidcommand{x}`)
		expect(wrapper.findAll('annotation').map((node) => node.text())).toContain('y^2')
	})
})
