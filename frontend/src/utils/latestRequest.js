// A resource normally accepts every response, even after a newer fetch started.
// Invalidate both successful and failed old requests so neither can replace the
// current lesson. Abort also releases the browser's connection on slow networks.
export function createLatestRequest(fetcher) {
 let generation = 0
 let controller
 const invalidate = () => {
  generation++
  controller?.abort()
 }
 return {
  invalidate,
  async fetch(options) {
   invalidate()
   const current = generation
   controller = new AbortController()
   try {
    const data = await fetcher({ ...options, signal: controller.signal })
    if (current !== generation) throw new DOMException('Superseded request', 'AbortError')
    return data
   } catch (error) {
    if (current !== generation) throw new DOMException('Superseded request', 'AbortError')
    throw error
   }
  },
 }
}
