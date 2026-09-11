import { describe, expect, it } from 'vitest'
import { renderTexStatement } from '@/utils/texStatement'

describe('TeX statement preview', () => {
	it('extracts Chinese document text and renders math inline', () => {
		const result = renderTexStatement(String.raw`\documentclass{article}
\usepackage{ctex}
\newcommand{\problemname}[1]{ignored}
\begin{document}
\problemname{半价票问题}
\subsection*{题目描述}
身高满足 $1.2 \le n \le 1.5$。
\begin{verbatim}YES\end{verbatim}
\end{document}`)
		expect(result).toContain('半价票问题')
		expect(result).toContain('题目描述')
		expect(result).toContain('katex')
		expect(result).toContain('YES')
		expect(result).not.toMatch(/documentclass|usepackage|newcommand|subsection|verbatim|ignored/)
		expect(result).not.toContain('\n')
	})
	it('escapes HTML and does not expand file commands or trusted math URLs', () => {
		const result = renderTexStatement(String.raw`<img src=x onerror=alert(1)> \input{/etc/passwd} $\href{javascript:alert(1)}{click}$`)
		expect(result).not.toContain('<img')
		expect(result).not.toContain('href="javascript:')
		expect(result).not.toContain('/etc/passwd')
	})
})

it('renders paragraphs, nested lists, escaped spaces and legacy comparison commands', () => {
 const html = renderTexStatement(String.raw`\problemname{一个月有几天}

输入年份。&#x20;

已知：
\begin{itemize}\item $31$ 天\item 二月：\begin{itemize}\item 闰年：$29$ 天\end{itemize}\end{itemize}
\subsection*{输入格式}
$1600\ley\le3000$ 和 $1\lem\le12$，$x\leq y$。
\subsection*{样例输入}
\begin{verbatim}1900 2
2018 12\end{verbatim}`, false)
 const doc = new DOMParser().parseFromString(html, 'text/html')
 expect(doc.querySelector('h2')?.textContent).toBe('一个月有几天')
 expect(doc.querySelectorAll('h3')).toHaveLength(2)
 expect(doc.querySelector('br')).not.toBeNull()
 expect(doc.querySelector('ul li ul li')?.textContent).toContain('闰年')
 expect(doc.querySelector('pre')?.textContent).toBe('1900 2\n2018 12')
 expect(doc.querySelector('.katex-error')).toBeNull()
 expect(doc.querySelector('.katex-mathml')).toBeNull()
 expect(doc.body.textContent).not.toContain('&#x20;')
 expect(doc.body.textContent).toContain('≤')
})


it('renders multiplication glued to a variable in both preview and full statements', () => {
 for (const inline of [true, false]) {
  const html = renderTexStatement(String.raw`$S=l\timesw$`, inline)
  const expected = renderTexStatement(String.raw`$S=l\times w$`, inline)
  expect(html).toBe(expected)
  expect(html).not.toContain('katex-error')
  expect(new DOMParser().parseFromString(html, 'text/html').body.textContent).toContain('×')
 }
})
