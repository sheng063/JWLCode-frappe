import { describe, expect, it } from 'vitest'
import { extractStatementSource, replaceStatementSource } from '@/utils/statementEditor'
import { renderTexStatement } from '@/utils/texStatement'
describe('editable TeX source', () => {
	it('preserves TeX and escapes HTML across repeated saves', () => {
		const html = '<a href="/api/method/lms.lms.problem_package.api.download_statement?version_id=V1">Download TeX statement</a><pre>old</pre>'
		const source = String.raw`\section{题目描述} $a_1 \leq b$ <script>alert(1)</script>`
		const saved = replaceStatementSource(html, source)
		expect(extractStatementSource(saved)).toBe(source)
		expect(saved).not.toContain('<script>')
		expect(extractStatementSource(replaceStatementSource(saved, source))).toBe(source)
		expect(renderTexStatement(source, false)).toContain('katex')
	})
	it('keeps manual HTML and PDF descriptions in the rich text editor', () => {
		expect(extractStatementSource('<p>$a+b$</p>')).toBeNull()
		expect(extractStatementSource('<a href="/api/method/lms.lms.problem_package.api.download_statement?version_id=V1">Download PDF statement</a>')).toBeNull()
	})
})
