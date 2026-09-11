export function extractStatementSource(html: string): string | null {
	const doc = new DOMParser().parseFromString(html || '', 'text/html')
	const isTex = [...doc.querySelectorAll('a')].some(link =>
		link.getAttribute('href')?.startsWith('/api/method/lms.lms.problem_package.api.download_statement?') && link.textContent?.includes('TeX'))
	return isTex ? doc.querySelector('pre')?.textContent ?? null : null
}

export function replaceStatementSource(html: string, source: string): string {
	const doc = new DOMParser().parseFromString(html, 'text/html')
	const pre = doc.querySelector('pre')
	if (pre) pre.textContent = source
	return doc.body.innerHTML
}
