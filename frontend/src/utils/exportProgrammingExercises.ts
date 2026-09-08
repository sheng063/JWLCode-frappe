/** Download a complete selection, propagating server validation errors to the page. */
export async function exportProgrammingExercises(names: string[]): Promise<void> {
	if (!names.length || names.length > 50) {
		throw new Error(__('Select between 1 and 50 exercises to export.'))
	}
	const response = await fetch(
		'/api/method/lms.lms.problem_package.export.export_exercises',
		{
			method: 'POST',
			credentials: 'same-origin',
			headers: {
				'Content-Type': 'application/json',
				'X-Frappe-CSRF-Token': (window as any).csrf_token || '',
			},
			body: JSON.stringify({ exercises: names }),
		}
	)
	if (!response.ok) {
		let message = __('Export failed. Please try again.')
		try {
			const data = await response.json()
			const messages = JSON.parse(data._server_messages || '[]')
			const first = messages[0]
			if (first) {
				message = (typeof first === 'string' ? JSON.parse(first) : first).message || message
			}
		} catch {
			// Proxies may return HTML; retain the readable fallback.
		}
		throw new Error(message)
	}
	if (!response.headers.get('Content-Type')?.includes('application/zip')) {
		throw new Error(__('The server did not return a ZIP file. Please sign in and try again.'))
	}
	const url = URL.createObjectURL(await response.blob())
	const link = document.createElement('a')
	try {
		link.href = url
		link.download = 'programming-exercises.zip'
		document.body.appendChild(link)
		link.click()
	} finally {
		link.remove()
		// Give the browser time to start reading the object URL.
		setTimeout(() => URL.revokeObjectURL(url), 1000)
	}
}
