type ProgrammingLanguage = 'C++' | 'Python'
const preferenceKey = 'lms:programming-language'

export function readProgrammingLanguage(): ProgrammingLanguage {
	try {
		const saved = localStorage.getItem(preferenceKey)
		if (saved === 'C++' || saved === 'Python') return saved
	} catch { /* Browser storage may be unavailable. */ }
	return 'C++'
}

export function saveProgrammingLanguage(language: ProgrammingLanguage) {
	if (language !== 'C++' && language !== 'Python') return
	try {
		localStorage.setItem(preferenceKey, language)
	} catch { /* A storage failure must not interrupt language switching. */ }
}
