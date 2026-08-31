#!/usr/bin/env python3
"""Validate the Simplified Chinese catalog without third-party dependencies."""

from __future__ import annotations

import ast
import re
from collections import Counter
from pathlib import Path


CATALOG = Path(__file__).resolve().parents[1] / "lms" / "locale" / "zh.po"
PLACEHOLDER = re.compile(r"\{[^{}]+\}|%\([^)]+\)[a-zA-Z]|%[a-zA-Z]")
MAX_EMPTY_TRANSLATIONS = 313
REQUIRED = {
	"Frappe Learning",
	"Learning",
	"About this course",
	"Add New Member",
	"Add students to the batch to make an announcement",
	"Assignment Progress",
	"Batch created successfully",
	"Batch updated successfully",
	"Build and manage courses, chapters, and lessons",
	"Course Progress",
	"Course Reviews",
	"Course content",
	"Course details",
	"Course editor",
	"Course overview",
	"Curriculum",
	"Delete user",
	"Edit Member",
	"Enroll a Student",
	"Enroll students to track their progress here.",
	"Evaluation Requests",
	"Exercise deleted successfully",
	"Lesson Progress",
	"Make Announcement",
	"Member added successfully",
	"No chapters yet",
	"No courses added to this batch",
	"No students enrolled yet",
	"Programming Exercise Progress",
	"Quiz Progress",
	"Select instructors",
	"Student View",
	"Student enrolled successfully",
	"Submissions",
	"Total Questions",
	"Upload Assignment",
	"Video Statistics",
}


def parse_po(path: Path) -> dict[str, str]:
	entries: dict[str, str] = {}
	msgid: list[str] | None = None
	msgstr: list[str] | None = None
	active: list[str] | None = None

	def finish() -> None:
		if msgid is not None and msgstr is not None:
			entries["".join(msgid)] = "".join(msgstr)

	for raw in [*path.read_text(encoding="utf-8").splitlines(), ""]:
		if raw.startswith("msgid "):
			finish()
			msgid = [ast.literal_eval(raw[6:])]
			msgstr = None
			active = msgid
		elif raw.startswith("msgstr "):
			msgstr = [ast.literal_eval(raw[7:])]
			active = msgstr
		elif raw.startswith('"') and active is not None:
			active.append(ast.literal_eval(raw))
		elif not raw:
			finish()
			msgid = msgstr = active = None
	return entries


def main() -> None:
	entries = parse_po(CATALOG)
	empty = {key for key, value in entries.items() if key and not value}
	errors: list[str] = []
	if len(empty) > MAX_EMPTY_TRANSLATIONS:
		errors.append(f"empty translations increased: {len(empty)} > {MAX_EMPTY_TRANSLATIONS}")
	for key in sorted(REQUIRED & empty):
		errors.append(f"required translation is empty: {key}")
	for source, target in entries.items():
		if target and Counter(PLACEHOLDER.findall(source)) != Counter(PLACEHOLDER.findall(target)):
			errors.append(f"placeholder mismatch: {source}")
		if "批次" in target:
			errors.append(f"use 班级 instead of 批次: {source}")
	if errors:
		raise SystemExit("\n".join(errors))
	print(f"zh catalog OK: {len(entries)} entries, {len(empty)} untranslated")


if __name__ == "__main__":
	main()
