import { toast } from 'frappe-ui'
import { createDialog } from '@/utils/dialogs'

const endpoint = '/api/method/lms.lms.course_export_jobs.'
const pending = new Set<string>()

async function request(method: string, params: Record<string, string>, post = false) {
	const response = await fetch(endpoint + method + (post ? '' : '?' + new URLSearchParams(params)), {
		method: post ? 'POST' : 'GET',
		credentials: 'include',
		...(post ? {
			headers: { 'Content-Type': 'application/json', 'X-Frappe-CSRF-Token': (window as any).csrf_token || '' },
			body: JSON.stringify(params),
		} : {}),
	})
	if (!response.ok) throw new Error(__('Export failed'))
	return (await response.json()).message
}

/** Ask before starting a potentially large video download. */
export function confirmCourseExport(courseName: string): void {
	if (pending.has(courseName)) return
	createDialog({
		title: __('Export Course'),
		message: __('Include course videos in the export? Without videos, video links are kept, but video files must be transferred separately. External videos are linked only.'),
		actions: [
			...[true, false].map((includeVideos) => ({
				label: includeVideos ? __('Export with videos') : __('Export without videos'),
				variant: includeVideos ? 'solid' : 'subtle',
				onClick({ close }: { close: () => void }) {
					close()
					return exportCourseAsZip(courseName, includeVideos)
				},
			})),
			{ label: __('Cancel'), onClick: ({ close }: { close: () => void }) => close() },
		],
	})
}

/** Background preparation followed by a native, resumable browser download. */
export async function exportCourseAsZip(courseName: string, includeVideos = true): Promise<void> {
	if (pending.has(courseName)) return
	pending.add(courseName)
	try {
		const { export_id } = await request('start_export', { course_name: courseName, include_videos: includeVideos ? '1' : '0' }, true)
		toast.info(__('Preparing course export. Large courses may take several minutes.'))
		const deadline = Date.now() + 6 * 60 * 60 * 1000
		while (Date.now() < deadline) {
			const state = await request('export_status', { export_id })
			if (state.status === 'failed') throw new Error(state.error || __('Export failed'))
			if (state.status === 'ready') {
				const a = document.createElement('a')
				a.href = endpoint + 'download_export?export_id=' + encodeURIComponent(export_id)
				a.download = ''
				document.body.appendChild(a)
				a.click()
				a.remove()
				toast.success(__('Course export is ready. Download started.'))
				return
			}
			await new Promise((resolve) => setTimeout(resolve, 3000))
		}
		throw new Error(__('Course export timed out. Please retry.'))
	} catch (err) {
		console.error(err)
		toast.error(err instanceof Error ? err.message : __('Export failed'))
	} finally {
		pending.delete(courseName)
	}
}
