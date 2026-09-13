import { expect, it } from 'vitest'
import { socketUrl } from '@/utils/socketUrl'
it.each([
 ['http://120.48.133.64', 'http://120.48.133.64/site'],
 ['https://school.example', 'https://school.example/site'],
 ['http://school.localhost:8000', 'http://school.localhost:9000/site'],
 ['https://school.localhost:8000', 'https://school.localhost:9000/site'],
])('connects realtime using the scheme of %s', (page, expected) => {
 expect(socketUrl(new URL(page), 9000, 'site')).toBe(expected)
})
