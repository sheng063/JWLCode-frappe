import { describe, it, expect, vi, afterEach } from 'vitest'
import { createGameBridge } from '@/utils/gameRuntime'
import { gameDocument } from '@/utils/game'

const native = globalThis.MessageChannel
class MockChannel {
  port1 = { onmessage: null as any, postMessage: vi.fn(), start: vi.fn(), close: vi.fn() }
  port2 = {}
  static last: MockChannel
  constructor() { MockChannel.last = this }
}
afterEach(() => { globalThis.MessageChannel = native })
function setup() {
  globalThis.MessageChannel = MockChannel as any
  const frame = { contentWindow: { postMessage: vi.fn() } }
  const launch = { launch_id: 'launch', platform_api: 1 }
  const api = vi.fn().mockResolvedValue({ ticket: 'safe' })
  const bridge = createGameBridge({ getFrame: () => frame, getLaunch: () => launch, call: api })
  const ready = (source: any = frame.contentWindow, nonce = 'f'.repeat(32)) => window.dispatchEvent(new MessageEvent('message', { source, data: { type: 'jwl-game-ready', nonce } }))
  return { frame, api, bridge, ready }
}
describe('Game runtime bridge', () => {
  it('accepts only the current iframe and a valid handshake nonce', () => {
    const { frame, bridge, ready } = setup()
    ready(null)
    ready(frame.contentWindow, 'bad')
    expect(frame.contentWindow.postMessage).not.toHaveBeenCalled()
    ready()
    expect(frame.contentWindow.postMessage).toHaveBeenCalledTimes(1)
    ready()
    expect(frame.contentWindow.postMessage).toHaveBeenCalledTimes(1)
    bridge.dispose()
  })
  it('rejects unknown actions and requests operation-bound join tickets', async () => {
    const { api, bridge, ready } = setup()
    ready()
    const port = MockChannel.last.port1
    await port.onmessage({ data: { type: 'ticket', id: '1', action: 'foreign' } })
    expect(api).not.toHaveBeenCalled()
    await port.onmessage({ data: { type: 'ticket', id: '2', action: 'quickMatch' } })
    expect(api).toHaveBeenCalledWith('lms.lms.game_runtime.issue_join_ticket', { launch_id: 'launch', action: 'quickMatch', room_id: '' })
    expect(port.postMessage).toHaveBeenCalledWith({ type: 'ticket', id: '2', result: { ticket: 'safe' } })
    bridge.dispose()
  })
  it('does not deliver in-flight credentials after reset', async () => {
    const { api, bridge, ready } = setup()
    let resolve: any
    api.mockReturnValue(new Promise(r => { resolve = r }))
    ready()
    const port = MockChannel.last.port1
    const pending = port.onmessage({ data: { type: 'ticket', id: '1', action: 'quickMatch' } })
    bridge.reset()
    resolve({ ticket: 'stale' })
    await pending
    expect(port.postMessage).not.toHaveBeenCalled()
    expect(port.close).toHaveBeenCalled()
    bridge.dispose()
  })
  it('keeps static networking blocked and permits only valid configured origins', () => {
    expect(gameDocument('<html/>')).toContain("connect-src 'none'")
    const doc = gameDocument('<html/>', ['https://games.example.com', 'wss://games.example.com', "https://evil.example; script-src *"])
    expect(doc).toContain('connect-src https://games.example.com wss://games.example.com;')
    expect(doc).not.toContain('evil.example')
  })
})
