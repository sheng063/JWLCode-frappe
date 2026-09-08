import { beforeEach, describe, expect, it, vi } from 'vitest'
import { readProgrammingCode, saveProgrammingCode } from '@/utils/programmingCodeCache'

beforeEach(() => { vi.restoreAllMocks(); localStorage.clear() })

describe('submitted programming code', () => {
	it('restores code and language only for the same user and exercise', () => {
		const saved = { language: 'C++' as const, code: 'int main() {}' }
		saveProgrammingCode('alice', 'EX-1', saved)
		expect(readProgrammingCode('alice', 'EX-2')).toBeNull()
		expect(readProgrammingCode('bob', 'EX-1')).toBeNull()
		expect(readProgrammingCode('alice', 'EX-1', 'Python')).toBeNull()
		expect(readProgrammingCode('alice', 'EX-1')).toEqual(saved)
	})
	it('keeps the latest submission, including empty source', () => {
		saveProgrammingCode('alice', 'EX-1', { language: 'C++', code: 'old' })
		saveProgrammingCode('alice', 'EX-1', { language: 'Python', code: '' })
		expect(readProgrammingCode('alice', 'EX-1')).toEqual({ language: 'Python', code: '' })
		expect(readProgrammingCode('alice', 'EX-1', 'C++')).toEqual({ language: 'C++', code: 'old' })
		expect(readProgrammingCode('alice', 'EX-1', 'Python')?.code).toBe('')
	})
	it('does not collide when identities contain separators', () => {
		saveProgrammingCode('a:b', 'c', { language: 'Python', code: 'first' })
		expect(readProgrammingCode('a', 'b:c')).toBeNull()
	})
	it('does not cache anonymous users', () => {
		for (const user of [undefined, '', 'Guest']) {
			saveProgrammingCode(user, 'EX-1', { language: 'Python', code: 'secret' })
			expect(readProgrammingCode(user, 'EX-1')).toBeNull()
		}
		expect(localStorage.length).toBe(0)
	})
	it('ignores corrupt and unsupported records', () => {
		saveProgrammingCode('alice', 'EX-1', { language: 'Python', code: 'ok' })
		const key = localStorage.key(0)!
		for (const value of ['{', 'null', '{"code":42,"language":"Python"}', '{"code":"x","language":"Rust"}']) {
			localStorage.setItem(key, value)
			expect(readProgrammingCode('alice', 'EX-1')).toBeNull()
		}
	})
	it('continues when browser storage is blocked or full', () => {
		vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('blocked') })
		vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('full') })
		expect(readProgrammingCode('alice', 'EX-1')).toBeNull()
		expect(() => saveProgrammingCode('alice', 'EX-1', { language: 'Python', code: 'x' })).not.toThrow()
	})
})
