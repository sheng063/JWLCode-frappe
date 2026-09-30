import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
const { notices } = vi.hoisted(() => ({ notices: { error: vi.fn(), info: vi.fn(), success: vi.fn() } }))
vi.mock('frappe-ui', () => ({ toast: notices }))
vi.mock('@/utils/dialogs', () => ({ createDialog: vi.fn() }))
import { createDialog } from '@/utils/dialogs'
import { confirmCourseExport, exportCourseAsZip } from '@/utils/exportCourse'

const reply = (message: unknown) => ({ ok: true, json: async () => ({ message }) }) as Response

describe('course ZIP download', () => {
  beforeEach(() => {
    vi.mocked(createDialog).mockClear()
    vi.useFakeTimers()
    vi.stubGlobal('__', (s: string) => s)
    vi.stubGlobal('fetch', vi.fn())
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    vi.spyOn(console, 'error').mockImplementation(() => {})
    Object.values(notices).forEach(mock => mock.mockReset())
  })
  afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); vi.unstubAllGlobals() })
  it('waits for background preparation and downloads directly without a Blob', async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(reply({ export_id: 'token' }))
      .mockResolvedValueOnce(reply({ status: 'running' }))
      .mockResolvedValueOnce(reply({ status: 'ready' }))
    let href = ''
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function () { href = this.href })
    const exporting = exportCourseAsZip('中文 & course')
    await vi.advanceTimersByTimeAsync(3000)
    await exporting
    expect(fetch).toHaveBeenNthCalledWith(1, '/api/method/lms.lms.course_export_jobs.start_export', expect.objectContaining({
      method: 'POST', credentials: 'include', body: JSON.stringify({ course_name: '中文 & course', include_videos: '1' }),
    }))
    expect(href).toContain('download_export?export_id=token')
    expect(document.querySelector('a[download]')).toBeNull()
    expect(notices.success).toHaveBeenCalled()
  })
  it('prevents repeated clicks while preparing', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(reply({ export_id: 'token' })).mockResolvedValueOnce(reply({ status: 'ready' }))
    await Promise.all([exportCourseAsZip('course'), exportCourseAsZip('course')])
    expect(fetch).toHaveBeenCalledTimes(2)
  })
  it('shows worker failure and permits retry', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(reply({ export_id: 'token' })).mockResolvedValueOnce(reply({ status: 'failed', error: 'Missing asset' }))
    await exportCourseAsZip('course')
    expect(notices.error).toHaveBeenCalledWith('Missing asset')
    expect(HTMLAnchorElement.prototype.click).not.toHaveBeenCalled()
    vi.mocked(fetch).mockResolvedValueOnce(reply({ export_id: 'retry' })).mockResolvedValueOnce(reply({ status: 'ready' }))
    await exportCourseAsZip('course')
    expect(HTMLAnchorElement.prototype.click).toHaveBeenCalledOnce()
  })
  it('shows a failure toast for denied export without downloading', async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: false, status: 403 } as Response)
    await exportCourseAsZip('course')
    expect(notices.error).toHaveBeenCalledWith('Export failed')
    expect(HTMLAnchorElement.prototype.click).not.toHaveBeenCalled()
  })
})


describe('course export confirmation', () => {
  beforeEach(() => {
    vi.stubGlobal('__', (s: string) => s)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(reply({ export_id: 'choice' })).mockResolvedValueOnce(reply({ status: 'ready' })))
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    vi.mocked(createDialog).mockClear()
  })
  afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals() })
  it.each([true, false])('submits the selected video option: %s', async (includeVideos) => {
    confirmCourseExport('course')
    expect(fetch).not.toHaveBeenCalled()
    const dialog = vi.mocked(createDialog).mock.calls[0][0]
    const close = vi.fn()
    await dialog.actions[includeVideos ? 0 : 1].onClick({ close })
    expect(close).toHaveBeenCalledOnce()
    expect(fetch).toHaveBeenNthCalledWith(1, expect.any(String), expect.objectContaining({
      body: JSON.stringify({ course_name: 'course', include_videos: includeVideos ? '1' : '0' }),
    }))
  })
  it('cancels without starting an export', () => {
    confirmCourseExport('course')
    const close = vi.fn()
    vi.mocked(createDialog).mock.calls[0][0].actions[2].onClick({ close })
    expect(close).toHaveBeenCalledOnce()
    expect(fetch).not.toHaveBeenCalled()
  })
})
