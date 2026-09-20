const pending = new Set(['Queued', 'Compiling', 'Running'])

// 每个页面独立管理轮询；切换页面或卸载时递增代次，
// 使尚未触发的定时器和仍在传输中的旧响应同时失效。
export function createJudgeStatusPoller({ fetchStatus, onStatus, onError,
  isHidden = () => document.hidden, schedule = setTimeout, cancel = clearTimeout }) {
  let generation = 0
  let timer
  const stop = () => {
    generation++
    if (timer !== undefined) cancel(timer)
    timer = undefined
  }
  return {
    stop,
    start(name) {
      stop()
      const current = generation
      const isCurrent = () => generation === current
      const poll = (failures = 0) => {
        if (!isCurrent()) return
        const delay = Math.max(isHidden() ? 5000 : 1500, Math.min(1500 * 2 ** failures, 15000))
        timer = schedule(async () => {
          try {
            const result = await fetchStatus(name)
            if (!isCurrent()) return
            await onStatus(result, name, isCurrent)
            if (pending.has(result.status)) poll()
          } catch (error) {
            if (!isCurrent()) return
            onError?.(error)
            poll(Math.min(failures + 1, 4))
          }
        }, delay)
      }
      poll()
    },
  }
}
