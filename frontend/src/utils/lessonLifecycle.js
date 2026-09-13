// EditorJS does not expose destroy until isReady resolves. A new lesson uses
// its own holder element, so a late teardown cannot empty the new lesson.
export function disposeLessonEditor(editor) {
 if (!editor) return
 const destroy = () => {
  try { editor.destroy?.() }
  catch (error) { console.warn('Unable to dispose lesson editor', error) }
 }
 if (editor.destroy) destroy()
 else editor.isReady?.then(destroy).catch(() => {})
}

export function disposeLessonPlayers(players) {
 for (const player of players) {
  try { player.destroy?.() }
  catch (error) { console.warn('Unable to dispose lesson player', error) }
 }
}
