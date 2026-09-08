export type SavedProgrammingCode = {
	language: 'Python' | 'C++'
	code: string
}

// Use the stable document ID (the route's exerciseID), not the display title.
const cacheKey = (user: string, exercise: string, language: SavedProgrammingCode['language']) =>
	`lms:submitted-code:v2:${JSON.stringify([user, exercise, language])}`
const languageKey = (user: string, exercise: string) =>
	`lms:submitted-language:v2:${JSON.stringify([user, exercise])}`

export function readProgrammingCode(
	user: string | undefined,
	exercise: string,
	language?: SavedProgrammingCode['language'],
): SavedProgrammingCode | null {
	if (!user || user === 'Guest' || !exercise) return null
	try {
		// On entry remember the last submitted language; language switches read
		// only the explicitly selected language's independent submission.
		const selected = language ?? localStorage.getItem(languageKey(user, exercise))
		if (selected !== 'Python' && selected !== 'C++') return null
		const saved = JSON.parse(localStorage.getItem(cacheKey(user, exercise, selected)) || 'null')
		if (saved && typeof saved.code === 'string' && saved.language === selected) return saved
	} catch { /* Unavailable or malformed storage falls back to the template. */ }
	return null
}

export function saveProgrammingCode(user: string | undefined, exercise: string, saved: SavedProgrammingCode) {
	if (!user || user === 'Guest' || !exercise) return
	try {
		localStorage.setItem(cacheKey(user, exercise, saved.language), JSON.stringify(saved))
		localStorage.setItem(languageKey(user, exercise), saved.language)
	} catch { /* A storage failure must not prevent submitting code. */ }
}
