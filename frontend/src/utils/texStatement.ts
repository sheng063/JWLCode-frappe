import katex from 'katex'
import DOMPurify from 'dompurify'

const escape = (text: string) => text.replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]!)

// A display-only subset of LaTeX: document text, groups, lists and KaTeX math.
// Never expand user macros, include files, or execute TeX commands.
export function renderTexStatement(source: string, inline = true): string {
	// Some imported statements contain HTML-encoded spaces inside TeX text.
	source = source.replace(/&(?:#x0*20|#0*32|nbsp);/gi, ' ')
	const body = source.match(/\\begin\{document\}([\s\S]*?)\\end\{document\}/)?.[1] ?? source
	let index = 0
	function group(): string {
		const start = ++index
		let depth = 1
		while (index < body.length && depth) {
			if (body[index] === '\\') { index += 2; continue }
			if (body[index] === '{') depth++
			if (body[index] === '}') depth--
			index++
		}
		return body.slice(start, depth ? index : index - 1)
	}
	let html = ''
	const lists: { tag: string; itemOpen: boolean }[] = []
	while (index < body.length) {
		if (body[index] === '%') { while (index < body.length && body[index] !== '\n') index++; continue }
		const delimiter = body.startsWith('$$', index) ? '$$' : body[index] === '$' ? '$' : body.startsWith('\\(', index) ? '\\(' : body.startsWith('\\[', index) ? '\\[' : ''
		if (delimiter) {
			const close = delimiter === '\\(' ? '\\)' : delimiter === '\\[' ? '\\]' : delimiter
			const end = body.indexOf(close, index + delimiter.length)
			if (end >= 0) {
				// Legacy conversion glued a single variable to comparison and multiplication commands.
				const math = body.slice(index + delimiter.length, end)
					.replace(/\\(times)([a-zA-Z])\b/g, '\\$1 $2')
					.replace(/\\(le|ge)([a-pr-zA-PR-Z])\b/g, '\\$1 $2')
				html += katex.renderToString(math, { output: 'html', displayMode: !inline && (delimiter === '$$' || delimiter === '\\['), throwOnError: false, trust: false, strict: 'ignore', maxExpand: 100, maxSize: 10 })
				index = end + close.length; continue
			}
		}
		if (body[index] === '\\') {
			index++
			const command = body.slice(index).match(/^[a-zA-Z]+\*?/)
			if (!command) { html += body[index] === '\\' ? (inline ? ' ' : '<br>') : escape(body[index] || ''); index++; continue }
			index += command[0].length
			const name = command[0].replace(/\*$/, '')
			if (name === 'begin' || name === 'end') {
				const env = body[index] === '{' ? group() : ''
				if (!inline && (env === 'itemize' || env === 'enumerate')) {
					if (name === 'begin') {
						const tag = env === 'itemize' ? 'ul' : 'ol'
						lists.push({ tag, itemOpen: false }); html += `<${tag}>`
					} else {
						const list = lists.pop()
						if (list) html += `${list.itemOpen ? '</li>' : ''}</${list.tag}>`
					}
					continue
				}
				if (name === 'begin' && env === 'verbatim') {
					const end = body.indexOf('\\end{verbatim}', index)
					const code = escape(body.slice(index, end < 0 ? body.length : end))
					html += inline ? code : `<pre>${code}</pre>`
					index = end < 0 ? body.length : end + '\\end{verbatim}'.length
				}
				html += inline ? ' ' : ''; continue
			}
			if (['input', 'include', 'includegraphics', 'label', 'documentclass', 'usepackage', 'geometry', 'newcommand', 'renewcommand', 'def'].includes(name)) {
				while (/\s/.test(body[index] || '') && index < body.length) index++
				while (body[index] === '[' || body[index] === '{') {
					if (body[index] === '{') group()
					else { const end = body.indexOf(']', index); index = end < 0 ? body.length : end + 1 }
				}
				continue
			}
			if (['problemname', 'section', 'subsection', 'subsubsection', 'textbf', 'textit', 'emph', 'texttt'].includes(name) && body[index] === '{') {
				const text = group()
				const tag = name === 'problemname' ? 'h2' : name.includes('section') ? 'h3' : name === 'texttt' ? 'code' : name === 'textbf' ? 'strong' : 'em'
				const content = name === 'texttt' ? escape(text) : renderTexStatement(text, inline)
				html += inline ? content + ' ' : `<${tag}>${content}</${tag}>`
				continue
			}
			if (name === 'item') {
				const list = lists[lists.length - 1]
				if (!inline && list) {
					html += (list.itemOpen ? '</li>' : '') + '<li>'; list.itemOpen = true
				} else html += ' • '
			}
			else if (['par', 'newline', 'linebreak'].includes(name)) html += inline ? ' ' : '<br><br>'
			// Formatting command arguments are read as ordinary text below.
			continue
		}
		if (body[index] === '{' || body[index] === '}') { index++; continue }
		if (!inline && body[index] === '\n') {
			const whitespace = body.slice(index).match(/^\n[ \t\r\n]*/)![0]
			html += (whitespace.match(/\n/g)?.length || 0) > 1 ? '<br><br>' : ' '
			index += whitespace.length; continue
		}
		html += escape(body[index++])
	}
	return DOMPurify.sanitize((inline ? html.replace(/\s+/g, ' ') : html).trim())
}
