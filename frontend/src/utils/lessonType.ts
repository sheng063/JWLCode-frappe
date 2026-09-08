export function lessonBlocks(content?: string) {
	try {
		const blocks = JSON.parse(content || '{}')?.blocks
		return Array.isArray(blocks)
			? blocks.filter((block) => block && typeof block === 'object')
			: []
	} catch {
		return []
	}
}

export function meaningfulBlocks(content?: string) {
	return lessonBlocks(content).filter((block: any) => {
		if (['paragraph', 'markdown'].includes(block.type)) {
			return (
				String(block.data?.text || '').replace(/<br\s*\/?>|&nbsp;|\s/gi, '')
					.length > 0
			)
		}
		return true
	})
}

export function isProgrammingLesson(lesson: any) {
	const blocks = meaningfulBlocks(lesson?.content)
	if (lesson?.lesson_type === 'Text' || hasRawText(lesson?.content))
		return false
	if (blocks.some((block: any) => block.type !== 'program')) return false
	if (lesson?.body || lesson?.youtube || lesson?.quiz_id || lesson?.question)
		return false
	return (
		lesson?.lesson_type === 'Programming' ||
		(blocks.length > 0 &&
			blocks.every((block: any) => block.type === 'program'))
	)
}

export function hasMixedLessonContent(lesson: any) {
	const blocks = meaningfulBlocks(lesson?.content)
	const hasProgram = blocks.some((block: any) => block.type === 'program')
	const hasOther =
		hasRawText(lesson?.content) ||
		blocks.some((block: any) => block.type !== 'program') ||
		Boolean(
			lesson?.body || lesson?.youtube || lesson?.quiz_id || lesson?.question
		)
	return (
		(hasProgram && (hasOther || lesson?.lesson_type === 'Text')) ||
		(lesson?.lesson_type === 'Programming' && hasOther)
	)
}

function hasRawText(content?: string) {
	if (!content) return false
	try {
		const parsed = JSON.parse(content)
		return (
			!parsed ||
			typeof parsed !== 'object' ||
			Array.isArray(parsed) ||
			!Array.isArray(parsed.blocks ?? [])
		)
	} catch {
		return true
	}
}
