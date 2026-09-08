"""Content rules shared by all Course Lesson writes."""

import json
import re


def resolve_lesson_type(blocks, lesson_type=None, *, body=None, youtube=None, quiz_id=None, question=None, raw_content=None):
	if lesson_type and lesson_type not in ("Text", "Programming"):
		raise ValueError("Invalid lesson type.")
	meaningful = []
	for block in blocks:
		if block.get("type") in ("paragraph", "markdown"):
			text = str((block.get("data") or {}).get("text") or "")
			if not re.sub(r"<br\s*/?>|&nbsp;|\s", "", text, flags=re.I):
				continue
		meaningful.append(block)
	has_program = any(block.get("type") == "program" for block in meaningful)
	raw_text = False
	if raw_content:
		try:
			parsed = json.loads(raw_content)
			raw_text = not isinstance(parsed, dict) or not isinstance(parsed.get("blocks", []), list)
		except (ValueError, TypeError):
			raw_text = True
	has_other = raw_text or any(block.get("type") != "program" for block in meaningful) or any(
		(body, youtube, quiz_id, question)
	)
	if (has_program and (has_other or lesson_type == "Text")) or (
		lesson_type == "Programming" and has_other
	):
		raise ValueError("Programming exercises cannot be combined with other lesson content. Split them into separate lessons.")
	if any(not (block.get("data") or {}).get("exercise") for block in meaningful if block.get("type") == "program"):
		raise ValueError("Select a programming exercise or remove the empty exercise.")
	return lesson_type or ("Programming" if has_program else "Text")
