/** Plain quiz text, including legacy imports with escaped HTML wrappers. */
export function quizText(value: unknown): string {
	let text = String(value ?? '')
	for (let pass = 0; pass < 3; pass++) {
		if (
			!/<\/?(?:p|div|span|br|strong|em|b|i|ul|ol|li|pre|code|h[1-6]|table|tr|td|img|a|script|style)(?:\s|>|\/)/i.test(
				text,
			)
		) {
			const decoder = document.createElement('textarea')
			decoder.innerHTML = text.replace(/</g, '&lt;').replace(/>/g, '&gt;')
			const decoded = decoder.value
			if (decoded === text) break
			text = decoded
			continue
		}
		const doc = new DOMParser().parseFromString(
			text
				.replace(
					/<(?!\/?(?:p|div|span|br|strong|em|b|i|ul|ol|li|pre|code|h[1-6]|table|tr|td|img|a|script|style)(?:\s|>|\/))/gi,
					'&lt;',
				)
				.replace(/<\s*br\s*\/?\s*>/gi, '\n')
				.replace(/<\/(p|div|li|h[1-6]|pre|tr)>/gi, '\n'),
			'text/html',
		)
		doc.querySelectorAll('script,style').forEach((node) => node.remove())
		const next = doc.body.textContent || ''
		if (next === text) break
		text = next
		// Only unwrap known HTML; keep literal code such as vector<int>.
		if (
			!/<\/?(?:p|div|span|br|strong|em|b|i|ul|ol|li|pre|code|h[1-6])(?:\s|>)/i.test(
				text,
			)
		)
			break
	}
	return text.replace(/\u00a0/g, ' ').trim()
}
