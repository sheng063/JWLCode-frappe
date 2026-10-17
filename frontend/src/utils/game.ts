export const MAX_ZIP_GAME_BYTES = 20 * 1024 * 1024
export const MAX_GAME_BYTES = 5 * 1024 * 1024

export function readGameFile(file: File): Promise<string> {
	if (!/\.(html?|zip)$/i.test(file.name)) {
		return Promise.reject(new Error('请选择 HTML 或 ZIP 格式的游戏文件。'))
	}
	const limit = /\.zip$/i.test(file.name) ? MAX_ZIP_GAME_BYTES : MAX_GAME_BYTES
	if (!file.size || file.size > limit) {
		return Promise.reject(
			new Error(`文件不能为空，且不能超过 ${limit / 1024 / 1024} MB。`)
		)
	}
	return new Promise((resolve, reject) => {
		const reader = new FileReader()
		reader.onerror = () => reject(new Error('无法读取文件，请重新选择。'))
		reader.onload = () => resolve(String(reader.result).split(',')[1])
		reader.readAsDataURL(file)
	})
}

export function gameDocument(html: string, connectSources: string[] = []): string {
	// Placed before uploaded markup so it cannot relax the policy. The iframe
	// deliberately omits allow-same-origin, keeping scripts away from LMS data.
	const connections = connectSources.filter((source) => {
		try {
			const url = new URL(source)
			return ['https:', 'wss:', 'http:', 'ws:'].includes(url.protocol) &&
				!url.username && !url.password && url.pathname === '/' && !url.search && !url.hash &&
				!/[\s;"'<>]/.test(source)
		} catch { return false }
	}).join(' ') || "'none'"
	const policy =
		`default-src 'none'; script-src 'unsafe-inline' 'unsafe-eval' https: blob:; style-src 'unsafe-inline' https:; img-src data: blob: https:; media-src data: blob: https:; font-src data: https:; connect-src ${connections}; base-uri 'none'; form-action 'none'`
	return `<!doctype html><meta http-equiv="Content-Security-Policy" content="${policy}">${html.replace(/^\s*<!doctype[^>]*>/i, '')}`
}

export async function readGameCover(
	file: File
): Promise<{ content: string; preview: string }> {
	if (
		!/\.(png|jpe?g|webp)$/i.test(file.name) ||
		!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)
	) {
		throw new Error('封面仅支持 JPG、PNG 或 WebP 图片。')
	}
	if (!file.size || file.size > 2 * 1024 * 1024)
		throw new Error('封面不能为空，且不能超过 2 MB。')
	return new Promise((resolve, reject) => {
		const reader = new FileReader()
		reader.onerror = () => reject(new Error('无法读取封面，请重新选择。'))
		reader.onload = () => {
			const preview = String(reader.result)
			resolve({ preview, content: preview.split(',')[1] })
		}
		reader.readAsDataURL(file)
	})
}

export function saveGameDownload(filename: string, content: string) {
	const bytes = Uint8Array.from(atob(content), (char) => char.charCodeAt(0))
	const url = URL.createObjectURL(
		new Blob([bytes], {
			type: /\.zip$/i.test(filename)
				? 'application/zip'
				: 'text/html;charset=utf-8',
		})
	)
	const link = document.createElement('a')
	link.href = url
	link.download = filename
	document.body.appendChild(link)
	link.click()
	link.remove()
	window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
