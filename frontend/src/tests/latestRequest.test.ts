import { describe, expect, it, vi } from 'vitest'
import { createResource } from 'frappe-ui'
import { createLatestRequest } from '@/utils/latestRequest'

function deferred() {
 let resolve!: (value: any) => void
 let reject!: (error: Error) => void
 const promise = new Promise((yes, no) => { resolve = yes; reject = no })
 return { promise, resolve, reject }
}

// Use the real resource: stale errors otherwise roll data back to previousData.
it.each(['success', 'failure'])('keeps the chosen lesson when an older %s arrives late', async (outcome) => {
 const first = deferred(), second = deferred()
 const transport = vi.fn().mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
 const latest = createLatestRequest(transport)
 const resource = createResource({ url: 'get_lesson', resourceFetcher: latest.fetch })
 resource.setData({ title: 'Lesson 1' })
 const oldRequest = resource.fetch({ lesson: 2 })
 const currentRequest = resource.fetch({ lesson: 3 })
 expect(transport.mock.calls[0][0].signal.aborted).toBe(true)
 second.resolve({ title: 'Lesson 3' })
 await currentRequest
 if (outcome === 'success') first.resolve({ title: 'Lesson 2' })
 else first.reject(new Error('old network failure'))
 await oldRequest
 expect(resource.data).toEqual({ title: 'Lesson 3' })
 expect(resource.error).toBeNull()
})

it('ignores a response after leaving the page', async () => {
 const pending = deferred()
 const latest = createLatestRequest(() => pending.promise)
 const resource = createResource({ url: 'get_lesson', resourceFetcher: latest.fetch })
 const request = resource.fetch()
 latest.invalidate()
 pending.resolve({ title: 'old page' })
 await request
 expect(resource.data).toBeNull()
})

it('reports a current failure and allows a successful retry', async () => {
 const error = new Error('offline')
 const latest = createLatestRequest(vi.fn().mockRejectedValueOnce(error).mockResolvedValueOnce({ title: 'Lesson 2' }))
 const resource = createResource({ url: 'get_lesson', resourceFetcher: latest.fetch, onError: () => {} })
 await expect(resource.fetch()).rejects.toThrow('offline')
 expect(resource.error).toBe(error)
 await resource.fetch()
 expect(resource.data).toEqual({ title: 'Lesson 2' })
 expect(resource.error).toBeNull()
})
