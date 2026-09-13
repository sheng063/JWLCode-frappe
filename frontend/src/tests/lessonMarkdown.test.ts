import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { LessonMarkdownBlock } from '@/utils/lessonMarkdown'
import LessonContent from '@/components/LessonContent.vue'
vi.mock('@/components/QuizBlock.vue', () => ({ default: { props: ['quiz'], template: '<div class="quiz-stub">{{ quiz }}</div>' } }))
vi.mock('@/components/PdfBlock.vue', () => ({ default: { template: '<div />' } }))
const text = '# 标题\n\n**重点**\n\n- A\n- B\n\n| 名称 | 值 |\n| --- | --- |\n| A | 1 |\n\n```cpp\nint a;\n\nint b;\n```'
function check(root: Element) {
 expect(root.querySelector('h1')?.textContent).toBe('标题')
 expect(root.querySelector('strong')?.textContent).toBe('重点')
 expect(root.querySelectorAll('li')).toHaveLength(2)
 expect(root.querySelector('td')?.textContent).toBe('A')
 expect(root.querySelector('pre code')?.textContent).toBe('int a;\n\nint b;\n')
}
describe('lesson Markdown', () => {
 it('renders text blocks without modifying data', () => {
  const block = new LessonMarkdownBlock({ data: { text } })
  check(block.render())
  expect(block.save()).toEqual({ text })
 })
 it('preserves rich HTML and removes unsafe markup', () => {
  const root = new LessonMarkdownBlock({ data: { text: '<p><b>保留</b><img src="x" onerror="alert(1)"></p>\n\n<script>alert(1)</script>' } }).render()
  expect(root.querySelector('b')?.textContent).toBe('保留')
  expect(root.querySelector('script')).toBeNull()
  expect(root.querySelector('img')?.hasAttribute('onerror')).toBe(false)
 })
 it('renders complete legacy documents', () => {
  check(mount(LessonContent, { props: { content: text } }).element)
 })
 it('distinguishes macros from code examples and retains reference links', () => {
  const content = '```\n{{ Quiz("example") }}\n\n```\n\n{{ Quiz("real") }}\n\n[资料][ref]\n\n[ref]: https://example.com'
  const wrapper = mount(LessonContent, { props: { content } })
  expect(wrapper.findAll('.quiz-stub')).toHaveLength(1)
  expect(wrapper.get('.quiz-stub').text()).toBe('real')
  expect(wrapper.get('pre code').text()).toContain('{{ Quiz("example") }}')
  expect(wrapper.get('a').attributes('href')).toBe('https://example.com')
 })
})

 describe('inline code in rich-text lesson paragraphs', () => {
  it.each(['使用 `printf` 输出', '<p>使用 `printf` 输出</p>', '<div>使用 ``printf`` 输出</div>'])('renders %s', (text) => {
   const root = new LessonMarkdownBlock({ data: { text } }).render()
   expect(root.querySelector('code')?.textContent).toBe('printf')
   expect(root.textContent).not.toContain('`')
  })
  it('keeps existing code literal and treats encoded tags inside backticks as text', () => {
   const text = '<p>`&lt;img src=x onerror=alert(1)&gt;`</p><pre><code>`literal`</code></pre>'
   const root = new LessonMarkdownBlock({ data: { text } }).render()
   expect(root.querySelector('p code')?.textContent).toBe('<img src=x onerror=alert(1)>')
   expect(root.querySelector('img')).toBeNull()
   expect(root.querySelector('pre code')?.textContent).toBe('`literal`')
  })
 })
