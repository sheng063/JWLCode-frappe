import { flushPromises } from '@vue/test-utils'
import { expect, it, vi } from 'vitest'
import { disposeLessonEditor, disposeLessonPlayers } from '@/utils/lessonLifecycle'

it('destroys an editor that was left before its API became ready', async () => {
 let ready!: () => void
 const destroy = vi.fn()
 const editor: any = { isReady: new Promise<void>(resolve => { ready = resolve }) }
 disposeLessonEditor(editor)
 editor.destroy = destroy
 ready()
 await flushPromises()
 expect(destroy).toHaveBeenCalledOnce()
})
it('does not let broken editor/player cleanup stop navigation', () => {
 const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
 expect(() => disposeLessonEditor({ destroy() { throw Error('already detached') } })).not.toThrow()
 const destroy = vi.fn()
 disposeLessonPlayers([{ destroy() { throw Error('detached') } }, { destroy }])
 expect(destroy).toHaveBeenCalledOnce()
 warn.mockRestore()
})
it('handles initialization failure during teardown', async () => {
 disposeLessonEditor({ isReady: Promise.reject(new Error('invalid block')) })
 await flushPromises()
})


it('keeps Vue fragment anchors intact during EditorJS emptiness checks', async () => {
 const { createApp, h, Fragment, ref, nextTick, onBeforeUnmount } = await import('vue')
 const { vueBlockContainer } = await import('@/utils/blockDom')
 const container = vueBlockContainer()
 const items = ref([1, 2])
 const cleanup = vi.fn()
 const app = createApp({
  setup() {
   onBeforeUnmount(cleanup)
   return () => h(Fragment, null, items.value.map(item => h('span', { key: item }, String(item))))
  },
 })
 app.mount(container)
 container.normalize()
 items.value = [2, 3]
 await nextTick()
 expect(container.textContent).toBe('23')
 expect(() => app.unmount()).not.toThrow()
 expect(cleanup).toHaveBeenCalledOnce()
 expect(container.childNodes).toHaveLength(0)
})
