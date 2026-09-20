import { describe, it, expect, vi } from 'vitest'
import { createJudgeStatusPoller } from '../utils/judgeStatusPoller'

function fixture() {
  let timer
  const fetchStatus = vi.fn().mockResolvedValue({ status: 'Running' })
  const onStatus = vi.fn()
  const schedule = vi.fn((fn, delay) => { timer = fn; return delay })
  const cancel = vi.fn()
  const isHidden = vi.fn(() => false)
  const poller = createJudgeStatusPoller({ fetchStatus, onStatus, schedule, cancel, isHidden })
  return { poller, fetchStatus, onStatus, schedule, cancel, isHidden, tick: () => timer() }
}

describe('judge status polling', () => {
  it('stops at a terminal result and keeps polling pending results', async () => {
    const f = fixture()
    f.poller.start('one')
    await f.tick()
    expect(f.schedule).toHaveBeenCalledTimes(2)
    f.fetchStatus.mockResolvedValue({ status: 'Passed' })
    await f.tick()
    expect(f.onStatus).toHaveBeenCalledTimes(2)
    expect(f.schedule).toHaveBeenCalledTimes(2)
  })
  it('backs off on network errors with a cap and resets after success', async () => {
    const f = fixture()
    f.fetchStatus.mockRejectedValue(new Error('offline'))
    f.poller.start('one')
    for (let i = 0; i < 8; i++) await f.tick()
    expect(f.schedule.mock.lastCall[1]).toBe(15000)
    f.fetchStatus.mockResolvedValue({ status: 'Running' })
    await f.tick()
    expect(f.schedule.mock.lastCall[1]).toBe(1500)
    f.isHidden.mockReturnValue(true)
    await f.tick()
    expect(f.schedule.mock.lastCall[1]).toBe(5000)
  })
  it('ignores an in-flight response after switching submission', async () => {
    const f = fixture()
    let resolve
    f.fetchStatus.mockReturnValueOnce(new Promise(r => { resolve = r }))
    f.poller.start('old')
    const flight = f.tick()
    f.poller.start('new')
    resolve({ status: 'Passed' })
    await flight
    expect(f.onStatus).not.toHaveBeenCalled()
    expect(f.schedule).toHaveBeenCalledTimes(2)
  })
  it('does not restart after unmount during a failed request', async () => {
    const f = fixture()
    let reject
    f.fetchStatus.mockReturnValueOnce(new Promise((_, r) => { reject = r }))
    f.poller.start('one')
    const flight = f.tick()
    f.poller.stop()
    reject(new Error('offline'))
    await flight
    expect(f.onStatus).not.toHaveBeenCalled()
    expect(f.schedule).toHaveBeenCalledTimes(1)
  })
  it('retries when loading terminal details fails', async () => {
    const f = fixture()
    f.fetchStatus.mockResolvedValue({ status: 'Passed' })
    f.onStatus.mockRejectedValueOnce(new Error('detail offline'))
    f.poller.start('one')
    await f.tick()
    expect(f.schedule.mock.lastCall[1]).toBe(3000)
    await f.tick()
    expect(f.onStatus).toHaveBeenCalledTimes(2)
    expect(f.schedule).toHaveBeenCalledTimes(2)
  })
})
