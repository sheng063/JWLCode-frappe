// Only the current sandbox Window may open one channel per game load.
export function createGameBridge({ getFrame, getLaunch, call }: any) {
  let port: MessagePort | null = null
  let epoch = 0
  let busy = false
  function reset() {
    epoch++
    port?.close()
    port = null
    busy = false
  }
  async function receive(event: MessageEvent) {
    const launch = getLaunch()
    if (!launch || port || event.source !== getFrame()?.contentWindow ||
        event.data?.type !== 'jwl-game-ready' ||
        !/^[a-f0-9]{32}$/.test(event.data?.nonce || '')) return
    const channel = new MessageChannel()
    const current = epoch
    port = channel.port1
    port.onmessage = async ({ data }) => {
      if (current !== epoch || data?.type !== 'ticket' ||
          typeof data.id !== 'string' || data.id.length > 64 || busy) return
      if (!launch.room_keys.includes(data.roomKey)) return
      busy = true
      try {
        const result = await call('lms.lms.game_runtime.issue_join_ticket', {
          launch_id: launch.launch_id, room_key: data.roomKey,
        })
        if (current === epoch) port?.postMessage({ type: 'ticket', id: data.id, result })
      } catch {
        if (current === epoch) port?.postMessage({ type: 'ticket', id: data.id, error: '无法取得联机授权，请重新进入游戏。' })
      } finally { if (current === epoch) busy = false }
    }
    port.start()
    getFrame().contentWindow.postMessage({ type: 'jwl-game-connect', nonce: event.data.nonce }, '*', [channel.port2])
  }
  window.addEventListener('message', receive)
  return { reset, dispose() { reset(); window.removeEventListener('message', receive) } }
}
