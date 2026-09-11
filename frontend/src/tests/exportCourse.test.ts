import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
const { errorToast } = vi.hoisted(() => ({ errorToast: vi.fn() }))
vi.mock('frappe-ui', () => ({ toast: { error: errorToast } }))
import { exportCourseAsZip } from '@/utils/exportCourse'

describe('course ZIP download', () => {
  beforeEach(() => {
    vi.stubGlobal('__', (s: string) => s)
    vi.stubGlobal('fetch', vi.fn())
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: vi.fn(() => 'blob:audit') })
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() })
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    vi.spyOn(console, 'error').mockImplementation(() => {})
    errorToast.mockReset()
  })
  afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals() })
  it('downloads ZIP with encoded course name and server filename', async () => {
    const blob = new Blob(['zip'])
    vi.mocked(fetch).mockResolvedValue({ ok: true, blob: async () => blob, headers: new Headers({ 'Content-Disposition': 'attachment; filename="lesson.zip"' }) } as Response)
    let filename = ''
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function () { filename = this.download })
    await exportCourseAsZip('中文 & course')
    expect(fetch).toHaveBeenCalledWith('/api/method/lms.lms.api.export_course_as_zip?course_name=' + encodeURIComponent('中文 & course'), { method: 'GET', credentials: 'include' })
    expect(filename).toBe('lesson.zip')
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:audit')
    expect(document.querySelector('a[download]')).toBeNull()
  })
  it('uses fallback filename when disposition is absent', async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true, blob: async () => new Blob(['zip']), headers: new Headers() } as Response)
    let filename = ''
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function () { filename = this.download })
    await exportCourseAsZip('course')
    expect(filename).toBe('course.zip')
  })
  it('shows a failure toast for denied export without downloading', async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: false, status: 403 } as Response)
    await exportCourseAsZip('course')
    expect(errorToast).toHaveBeenCalledWith('Export failed')
    expect(URL.createObjectURL).not.toHaveBeenCalled()
  })
  it('shows a failure toast after a network error', async () => {
    vi.mocked(fetch).mockRejectedValue(new Error('offline'))
    await exportCourseAsZip('course')
    expect(errorToast).toHaveBeenCalledWith('Export failed')
  })
})
