import MarkdownIt from 'markdown-it'
import { sanitizeAt } from '@/directives/safeHtmlLevels'

const markdown = new MarkdownIt({ html: true, linkify: true })
const inlineMarkdown = new MarkdownIt({ html: false, linkify: true })

// Rich-text paragraphs can contain literal backticks inside <p>/<div> tags.
// Markdown treats those as opaque HTML blocks, so parse their text separately.
// Work on sanitized, inert HTML and never reinterpret existing code or attributes.
markdown.renderer.rules.html_block = (tokens, index) => {
	const doc = new DOMParser().parseFromString(
		sanitizeAt('rich', tokens[index].content), 'text/html'
	)
	const visit = (node) => {
		for (const child of [...node.childNodes]) {
			if (child.nodeType === 3 && child.textContent.includes('`')) {
				const parsed = new DOMParser().parseFromString(
					inlineMarkdown.renderInline(child.textContent), 'text/html'
				)
				child.replaceWith(...parsed.body.childNodes)
			} else if (child.nodeType === 1 && !child.matches('pre, code, script, style, textarea')) {
				visit(child)
			}
		}
	}
	visit(doc.body)
	return doc.body.innerHTML
}

export const renderLessonMarkdown = (text = '') => markdown.render(text)

// Parse the entire document so blank lines in fences/lists and reference links
// retain their Markdown meaning. Only standalone, top-level macros are embeds.
export function lessonContentBlocks(content = '') {
	const env = {}
	const tokens = markdown.parse(content, env)
	const blocks = []
	let pending = []
	const flush = () => {
		if (!pending.length) return
		blocks.push({ type: 'text', html: markdown.renderer.render(pending, markdown.options, env) })
		pending = []
	}
	for (let i = 0; i < tokens.length; i++) {
		const token = tokens[i]
		const text = tokens[i + 1]?.content
		const macro = token.type === 'paragraph_open' && token.level === 0 &&
			text?.match(/^\{\{\s*(YouTubeVideo|Quiz|Video|PDF|Audio|Embed)\b[^\n]*\}\}$/)
		if (macro) {
			flush()
			blocks.push({ type: macro[1], text })
			i += 2
		} else {
			pending.push(token)
		}
	}
	flush()
	return blocks
}

// Used only by the lesson reader; authoring tools keep their original data.
export class LessonMarkdownBlock {
	static get isReadOnlySupported() { return true }
	constructor({ data }) { this.data = data }
	render() {
		const element = document.createElement('div')
		element.classList.add('cdx-block', 'ce-paragraph', 'lesson-markdown')
		element.innerHTML = sanitizeAt('rich', renderLessonMarkdown(this.data.text || ''))
		return element
	}
	save() { return this.data }
}
