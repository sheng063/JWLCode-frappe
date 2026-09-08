export const editorDefaults = {
	theme: 'light',
	fontSize: 14,
	fontFamily: 'monospace',
	fontLigatures: false,
	tabSize: 4,
	wrap: true,
	relativeLineNumbers: false,
	autocomplete: true,
	keyboard: 'standard',
	runShortcut: true,
	submitShortcut: true,
}
export type EditorPreferences = typeof editorDefaults
export const editorPreferencesKey = 'lms:programming-editor:v1'
export function readEditorPreferences(): EditorPreferences {
	const result = { ...editorDefaults }
	try {
		const saved = JSON.parse(localStorage.getItem(editorPreferencesKey) || '{}')
		for (const key of [
			'fontLigatures',
			'wrap',
			'relativeLineNumbers',
			'autocomplete',
			'runShortcut',
			'submitShortcut',
		] as const) {
			if (typeof saved[key] === 'boolean') result[key] = saved[key]
		}
		if ([12, 13, 14, 16, 18, 20, 24].includes(saved.fontSize))
			result.fontSize = saved.fontSize
		if ([2, 4, 8].includes(saved.tabSize)) result.tabSize = saved.tabSize
		if (
			['monospace', 'Menlo, monospace', 'Consolas, monospace'].includes(
				saved.fontFamily,
			)
		)
			result.fontFamily = saved.fontFamily
		if (['light', 'dark'].includes(saved.theme)) result.theme = saved.theme
		if (['standard', 'vim', 'emacs'].includes(saved.keyboard))
			result.keyboard = saved.keyboard
	} catch {
		/* Storage can be disabled or contain an older invalid value. */
	}
	return result
}
