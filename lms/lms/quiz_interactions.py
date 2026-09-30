"""Authoring, public payloads and server grading for interactive quiz questions."""
import json
import random
import uuid

import frappe
from frappe import _

INTERACTIVE_TYPES = ("Ordering", "Matching")


def items_for(question):
	return json.loads(question.get("interactive_items") or "[]")


def validate_items(question):
	if question.type not in INTERACTIVE_TYPES:
		return
	try:
		items = items_for(question)
	except (ValueError, TypeError):
		frappe.throw(_("Invalid interactive question items."))
	if not isinstance(items, list) or not 2 <= len(items) <= 20:
		frappe.throw(_("Add between 2 and 20 items."))
	seen = set()
	for item in items:
		if not isinstance(item, dict):
			frappe.throw(_("Invalid interactive question items."))
		for field in ("text", "right") if question.type == "Matching" else ("text",):
			value = item.get(field)
			if not isinstance(value, str) or not value.strip():
				frappe.throw(_("Every item needs text."))
			item[field] = value.strip()
			key = (field, item[field])
			if key in seen:
				frappe.throw(_("Each column must contain unique items."))
			seen.add(key)
		for key in ("id", "right_id"):
			value = item.get(key)
			if not isinstance(value, str) or len(value) != 32 or value in seen or any(c not in '0123456789abcdef' for c in value):
				value = uuid.uuid4().hex
			item[key] = value
			seen.add(value)
	question.interactive_items = json.dumps(items, ensure_ascii=False)
	question.multiple = 0


def public_question(question):
	items = items_for(question) if question.type in INTERACTIVE_TYPES else []
	question.pop("interactive_items", None)
	if not items:
		return question
	left = [{"id": item["id"], "text": item["text"]} for item in items]
	random.SystemRandom().shuffle(left)
	if question.type == "Ordering" and [x['id'] for x in left] == [x['id'] for x in items]:
		left = left[1:] + left[:1]
	question["items"] = left
	if question.type == "Matching":
		right = [{"id": item["right_id"], "text": item["right"]} for item in items]
		random.SystemRandom().shuffle(right)
		question["right_items"] = right
	return question


def grade_answer(question_name, answers):
	question = frappe.get_doc("LMS Question", question_name)
	items = items_for(question)
	if not isinstance(answers, list) or not all(isinstance(a, str) for a in answers):
		return False, ""
	if question.type == "Ordering":
		labels = {item["id"]: item["text"] for item in items}
		return bool(items) and answers == list(labels), " → ".join(labels.get(a, "?") for a in answers)
	if question.type == "Matching":
		expected = {item["id"] + ":" + item["right_id"] for item in items}
		left = {item["id"]: item["text"] for item in items}
		right = {item["right_id"]: item["right"] for item in items}
		readable = []
		for answer in answers:
			l, _, r = answer.partition(":")
			readable.append(f'{left.get(l, "?")} ↔ {right.get(r, "?")}')
		return bool(items) and len(answers) == len(expected) and set(answers) == expected, "; ".join(readable)
	return False, ""


@frappe.whitelist()
def check_match(quiz: str, question: str, left: str, right: str):
	from lms.lms.permissions import can_access_quiz

	if not can_access_quiz(quiz) or not frappe.db.exists("LMS Quiz Question", {"parent": quiz, "question": question}):
		frappe.throw(_("You are not authorized to view this quiz."), frappe.PermissionError)
	doc = frappe.get_doc("LMS Question", question)
	if doc.type != "Matching":
		frappe.throw(_("Invalid question type."))
	return any(item["id"] == left and item["right_id"] == right for item in items_for(doc))
