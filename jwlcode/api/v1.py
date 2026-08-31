from __future__ import annotations

import hashlib
import json
import uuid

import frappe
from frappe.utils import add_to_date, cint, flt, get_datetime, now_datetime

from jwlcode.domain.submission import can_transition, is_terminal, normalize_languages, validate_source
from jwlcode.integrations.judge import verify_callback
from jwlcode.permissions import (
	can_access_course,
	can_access_student,
	is_admin,
	require_class_teacher,
	require_course_access,
	require_login,
	require_teacher,
	roles,
	student_for_user,
	teacher_for_user,
)


def _bounded_page(start: int | str = 0, page_length: int | str = 20) -> tuple[int, int]:
	return max(cint(start), 0), min(max(cint(page_length), 1), 100)


def _problem_context(problem_id: str) -> dict:
	rows = frappe.db.sql(
		"""
		select p.*, l.chapter, c.course
		from `tabJWL Problem` p
		inner join `tabJWL Lesson` l on l.name = p.lesson
		inner join `tabJWL Chapter` c on c.name = l.chapter
		where p.name = %s
		limit 1
		""",
		problem_id,
		as_dict=True,
	)
	if not rows:
		frappe.throw("Problem not found", frappe.DoesNotExistError)
	return rows[0]


def _lesson_context(lesson_id: str) -> dict:
	rows = frappe.db.sql(
		"""
		select l.*, c.course
		from `tabJWL Lesson` l
		inner join `tabJWL Chapter` c on c.name = l.chapter
		where l.name = %s
		limit 1
		""",
		lesson_id,
		as_dict=True,
	)
	if not rows:
		frappe.throw("Lesson not found", frappe.DoesNotExistError)
	return rows[0]


@frappe.whitelist(methods=["GET"])
def me() -> dict:
	user = require_login()
	student = student_for_user(user)
	teacher = teacher_for_user(user)
	data_scope: dict = {}
	if student:
		data_scope["student_id"] = student
		data_scope["class_ids"] = frappe.get_all(
			"JWL Enrollment", filters={"student": student, "status": "Active"}, pluck="academic_class"
		)
	if teacher:
		data_scope["teacher_id"] = teacher
		data_scope["class_ids"] = frappe.get_all(
			"JWL Teaching Assignment", filters={"teacher": teacher, "status": "Active"}, pluck="academic_class"
		)
	return {"user": user, "full_name": frappe.utils.get_fullname(user), "roles": sorted(roles(user)), "data_scope": data_scope}


@frappe.whitelist(methods=["GET"])
def courses(start: int = 0, page_length: int = 20) -> dict:
	user = require_login()
	start, page_length = _bounded_page(start, page_length)
	filters: dict = {}
	if not (is_admin(user) or teacher_for_user(user)):
		filters["status"] = "Published"
	visible = []
	for item in frappe.get_all(
		"JWL Course",
		filters=filters,
		fields=["name", "title", "version", "status", "description", "owner_teacher", "modified"],
		order_by="modified desc",
		limit_page_length=0,
	):
		if can_access_course(item.name, user):
			visible.append(item)
	return {"data": visible[start : start + page_length], "has_more": len(visible) > start + page_length}


@frappe.whitelist(methods=["GET"])
def lesson(lesson_id: str) -> dict:
	require_login()
	item = _lesson_context(lesson_id)
	require_course_access(item.course)
	if item.status != "Published" and not (is_admin() or teacher_for_user()):
		frappe.throw("Lesson not found", frappe.DoesNotExistError)
	student = student_for_user()
	progress = None
	if student:
		progress = frappe.db.get_value(
			"JWL Progress", {"student": student, "lesson": lesson_id}, ["status", "percent", "modified"], as_dict=True
		)
	return {
		"id": item.name,
		"chapter_id": item.chapter,
		"course_id": item.course,
		"title": item.title,
		"content": item.content,
		"sort_order": item.sort_order,
		"status": item.status,
		"progress": progress,
	}


@frappe.whitelist(methods=["GET"])
def problem(problem_id: str) -> dict:
	require_login()
	item = _problem_context(problem_id)
	require_course_access(item.course)
	if item.status != "Published" and not (is_admin() or teacher_for_user()):
		frappe.throw("Problem not found", frappe.DoesNotExistError)
	policy = frappe.db.get_value(
		"JWL Judge Policy",
		item.judge_policy,
		["allowed_languages", "time_limit_ms", "memory_limit_kb", "mode"],
		as_dict=True,
	)
	return {
		"id": item.name,
		"lesson_id": item.lesson,
		"title": item.title,
		"statement": item.statement,
		"type": item.problem_type,
		"version": item.version,
		"code_template": item.code_template,
		"max_score": item.max_score,
		"limits": policy,
	}


def _validate_assignment(assignment_id: str | None, problem: dict) -> None:
	if not assignment_id:
		return
	assignment = frappe.get_doc("JWL Assignment", assignment_id)
	if assignment.course != problem.course or assignment.status != "Published":
		frappe.throw("Assignment is not available", frappe.PermissionError)
	now = now_datetime()
	if get_datetime(assignment.opens_at) > now or get_datetime(assignment.due_at) < now:
		frappe.throw("Assignment is outside its submission window", frappe.ValidationError)
	student = student_for_user()
	if not student or not frappe.db.exists(
		"JWL Enrollment", {"student": student, "academic_class": assignment.academic_class, "status": "Active"}
	):
		frappe.throw("Assignment access denied", frappe.PermissionError)


def _create_submission(
	problem_id: str,
	language: str,
	source_code: str,
	client_request_id: str,
	*,
	submission_type: str,
	assignment_id: str | None = None,
	custom_input: str | None = None,
) -> dict:
	user = require_login()
	student = student_for_user(user)
	if not student:
		frappe.throw("An active student profile is required", frappe.PermissionError)
	try:
		validate_source(source_code)
	except ValueError as exc:
		frappe.throw(str(exc), frappe.ValidationError)
	if not client_request_id or len(client_request_id) > 140:
		frappe.throw("A valid client_request_id is required", frappe.ValidationError)
	existing = frappe.db.get_value(
		"JWL Submission", {"student": student, "client_request_id": client_request_id}, ["name", "status"], as_dict=True
	)
	if existing:
		return {"submission_id": existing.name, "status": existing.status, "idempotent_replay": True}
	problem = _problem_context(problem_id)
	require_course_access(problem.course)
	if problem.status != "Published":
		frappe.throw("Problem is not published", frappe.ValidationError)
	if submission_type == "Submission":
		_validate_assignment(assignment_id, problem)
	policy = frappe.get_doc("JWL Judge Policy", problem.judge_policy)
	language = language.strip().lower()
	if language not in normalize_languages(policy.allowed_languages):
		frappe.throw("Language is not allowed for this problem", frappe.ValidationError)
	if custom_input and len(custom_input.encode("utf-8")) > 64 * 1024:
		frappe.throw("custom_input exceeds 65536 bytes", frappe.ValidationError)
	if frappe.db.exists(
		"JWL Submission", {"student": student, "creation": [">", add_to_date(now_datetime(), seconds=-2)]}
	):
		frappe.throw("Please wait before submitting again", frappe.ValidationError)
	snapshot = {
		"policy_id": policy.name,
		"allowed_languages": sorted(normalize_languages(policy.allowed_languages)),
		"time_limit_ms": policy.time_limit_ms,
		"memory_limit_kb": policy.memory_limit_kb,
		"engine": policy.engine,
		"mode": policy.mode,
		"compiler_options": policy.compiler_options,
	}
	doc = frappe.get_doc(
		{
			"doctype": "JWL Submission",
			"student": student,
			"problem": problem_id,
			"assignment": assignment_id,
			"submission_type": submission_type,
			"language": language,
			"source_code": source_code,
			"custom_input": custom_input if submission_type == "Run" else None,
			"client_request_id": client_request_id,
			"trace_id": str(uuid.uuid4()),
			"status": "QUEUED",
			"status_version": 0,
			"problem_version": problem.version,
			"policy_snapshot": json.dumps(snapshot, ensure_ascii=False, sort_keys=True),
			"test_case_ref": problem.test_case_ref,
			"test_case_checksum": problem.test_case_checksum,
		}
	)
	frappe.db.savepoint("jwlcode_submission_insert")
	try:
		doc.insert(ignore_permissions=True)
	except frappe.DuplicateEntryError:
		frappe.db.rollback(save_point="jwlcode_submission_insert")
		existing = frappe.db.get_value(
			"JWL Submission",
			{"student": student, "client_request_id": client_request_id},
			["name", "status"],
			as_dict=True,
		)
		if existing:
			return {"submission_id": existing.name, "status": existing.status, "idempotent_replay": True}
		raise
	frappe.enqueue(
		"jwlcode.integrations.judge.dispatch_submission",
		queue="short",
		enqueue_after_commit=True,
		submission=doc.name,
		job_id=f"jwlcode-dispatch-{doc.name}",
		deduplicate=True,
	)
	return {"submission_id": doc.name, "status": doc.status, "trace_id": doc.trace_id}


@frappe.whitelist(methods=["POST"])
def create_code_run(problem_id: str, language: str, source_code: str, client_request_id: str, custom_input: str = "") -> dict:
	return _create_submission(
		problem_id,
		language,
		source_code,
		client_request_id,
		submission_type="Run",
		custom_input=custom_input,
	)


@frappe.whitelist(methods=["POST"])
def create_submission(
	problem_id: str,
	language: str,
	source_code: str,
	client_request_id: str,
	assignment_id: str | None = None,
) -> dict:
	return _create_submission(
		problem_id,
		language,
		source_code,
		client_request_id,
		submission_type="Submission",
		assignment_id=assignment_id,
	)


@frappe.whitelist(methods=["GET"])
def submission(submission_id: str) -> dict:
	require_login()
	doc = frappe.get_doc("JWL Submission", submission_id)
	if not can_access_student(doc.student):
		frappe.throw("Submission access denied", frappe.PermissionError)
	result = {
		"submission_id": doc.name,
		"problem_id": doc.problem,
		"type": doc.submission_type,
		"status": doc.status,
		"status_version": doc.status_version,
		"score": doc.score,
		"time_ms": doc.time_ms,
		"memory_kb": doc.memory_kb,
		"compiler_message": doc.compiler_message,
		"finished_at": doc.finished_at,
	}
	if student_for_user() == doc.student:
		result["source_code"] = doc.source_code
	if doc.submission_type == "Run":
		result["output"] = doc.custom_output
	return result


@frappe.whitelist(methods=["GET"])
def student_progress(student_id: str) -> dict:
	require_login()
	if not can_access_student(student_id):
		frappe.throw("Student progress access denied", frappe.PermissionError)
	return {
		"student_id": student_id,
		"data": frappe.get_all(
			"JWL Progress",
			filters={"student": student_id},
			fields=["lesson", "status", "percent", "modified"],
			order_by="modified desc",
		),
	}


@frappe.whitelist(methods=["POST"])
def create_assignment(
	title: str,
	academic_class: str,
	course_id: str,
	opens_at: str,
	due_at: str,
	max_score: float = 100,
	grading_rule: str = "Highest score",
) -> dict:
	require_class_teacher(academic_class)
	if get_datetime(opens_at) >= get_datetime(due_at):
		frappe.throw("due_at must be later than opens_at", frappe.ValidationError)
	if not frappe.db.exists(
		"JWL Teaching Assignment", {"academic_class": academic_class, "course": course_id, "status": "Active"}
	) and not is_admin():
		frappe.throw("Course is not assigned to this class", frappe.ValidationError)
	doc = frappe.get_doc(
		{
			"doctype": "JWL Assignment",
			"title": title,
			"academic_class": academic_class,
			"course": course_id,
			"opens_at": opens_at,
			"due_at": due_at,
			"status": "Draft",
			"max_score": flt(max_score),
			"grading_rule": grading_rule,
		}
	).insert(ignore_permissions=True)
	return {"assignment_id": doc.name, "status": doc.status}


@frappe.whitelist(methods=["GET"])
def class_analytics(academic_class: str) -> dict:
	require_class_teacher(academic_class)
	student_count = frappe.db.count("JWL Enrollment", {"academic_class": academic_class, "status": "Active"})
	rows = frappe.db.sql(
		"""
		select s.status, count(*) as count, avg(coalesce(sc.final_score, s.score, 0)) as average_score
		from `tabJWL Submission` s
		inner join `tabJWL Enrollment` e on e.student = s.student and e.status = 'Active'
		left join `tabJWL Score` sc on sc.submission = s.name
		where e.academic_class = %s and s.submission_type = 'Submission'
		group by s.status
		""",
		academic_class,
		as_dict=True,
	)
	return {"class_id": academic_class, "student_count": student_count, "submissions_by_status": rows}


@frappe.whitelist(methods=["POST"])
def adjust_score(submission_id: str, new_score: float, reason: str) -> dict:
	user = require_teacher()
	submission_doc = frappe.get_doc("JWL Submission", submission_id)
	if submission_doc.submission_type != "Submission" or not can_access_student(submission_doc.student, user):
		frappe.throw("Score adjustment access denied", frappe.PermissionError)
	if not reason or not reason.strip():
		frappe.throw("A reason is required", frappe.ValidationError)
	score_name = frappe.db.get_value("JWL Score", {"submission": submission_id}, "name")
	if not score_name:
		frappe.throw("The submission has no final score", frappe.ValidationError)
	score_doc = frappe.get_doc("JWL Score", score_name)
	value = flt(new_score)
	if value < 0 or value > flt(score_doc.max_score):
		frappe.throw("new_score must be within the allowed score range", frappe.ValidationError)
	frappe.get_doc(
		{
			"doctype": "JWL Score Adjustment",
			"score": score_doc.name,
			"old_score": score_doc.final_score,
			"new_score": value,
			"reason": reason.strip(),
			"adjusted_by": user,
			"adjusted_at": now_datetime(),
		}
	).insert(ignore_permissions=True)
	score_doc.final_score = value
	score_doc.grading_source = "Manual"
	score_doc.adjustment_reason = reason.strip()
	score_doc.save(ignore_permissions=True)
	return {"submission_id": submission_id, "score_id": score_doc.name, "final_score": value}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def judge_callback() -> dict:
	raw = frappe.request.get_data(cache=True)
	timestamp = frappe.get_request_header("X-JWL-Timestamp") or ""
	signature = frappe.get_request_header("X-JWL-Signature") or ""
	verify_callback(raw, timestamp, signature)
	try:
		payload = json.loads(raw)
	except (TypeError, json.JSONDecodeError):
		frappe.throw("Invalid JSON payload", frappe.ValidationError)
	required = {"event_id", "judge_request_id", "submission_id", "status", "status_version"}
	if not required.issubset(payload):
		frappe.throw("Callback payload is incomplete", frappe.ValidationError)
	locked = frappe.db.sql(
		"select name from `tabJWL Submission` where name=%s for update",
		payload["submission_id"],
	)
	if not locked:
		frappe.throw("Submission not found", frappe.DoesNotExistError)
	if frappe.db.exists("JWL Judge Callback Event", {"event_id": payload["event_id"]}):
		return {"accepted": True, "duplicate": True}
	doc = frappe.get_doc("JWL Submission", payload["submission_id"])
	if doc.judge_request_id and doc.judge_request_id != payload["judge_request_id"]:
		frappe.throw("judge_request_id mismatch", frappe.ValidationError)
	version = cint(payload["status_version"])
	if version <= cint(doc.status_version):
		return {"accepted": True, "stale": True}
	status = str(payload["status"]).upper()
	if not can_transition(doc.status, status):
		frappe.throw(f"Illegal status transition: {doc.status} -> {status}", frappe.ValidationError)
	if payload.get("score") is not None:
		max_score = flt(frappe.db.get_value("JWL Problem", doc.problem, "max_score"))
		if flt(payload["score"]) < 0 or flt(payload["score"]) > max_score:
			frappe.throw("Callback score is outside the problem score range", frappe.ValidationError)
	frappe.get_doc(
		{
			"doctype": "JWL Judge Callback Event",
			"event_id": payload["event_id"],
			"submission": doc.name,
			"judge_request_id": payload["judge_request_id"],
			"status": status,
			"status_version": version,
			"payload_hash": hashlib.sha256(raw).hexdigest(),
		}
	).insert(ignore_permissions=True)
	doc.status = status
	doc.status_version = version
	doc.judge_request_id = payload["judge_request_id"]
	doc.score = flt(payload.get("score"))
	doc.time_ms = cint(payload.get("time_ms"))
	doc.memory_kb = cint(payload.get("memory_kb"))
	doc.compiler_message = payload.get("compiler_message")
	if doc.submission_type == "Run":
		doc.custom_output = payload.get("output")
	if is_terminal(status):
		doc.finished_at = payload.get("finished_at") or now_datetime()
	doc.save(ignore_permissions=True)
	if doc.submission_type == "Submission" and is_terminal(status):
		max_score = flt(frappe.db.get_value("JWL Problem", doc.problem, "max_score"))
		score = frappe.db.get_value("JWL Score", {"submission": doc.name}, "name")
		values = {
			"raw_score": doc.score,
			"final_score": doc.score,
			"max_score": max_score,
			"grading_source": "Automatic",
		}
		if score:
			frappe.db.set_value("JWL Score", score, values)
		else:
			frappe.get_doc({"doctype": "JWL Score", "submission": doc.name, **values}).insert(ignore_permissions=True)
		if status == "ACCEPTED":
			lesson_id = frappe.db.get_value("JWL Problem", doc.problem, "lesson")
			progress_name = frappe.db.get_value(
				"JWL Progress", {"student": doc.student, "lesson": lesson_id}, "name"
			)
			if progress_name:
				frappe.db.set_value("JWL Progress", progress_name, {"status": "Completed", "percent": 100})
			else:
				frappe.get_doc(
					{
						"doctype": "JWL Progress",
						"student": doc.student,
						"lesson": lesson_id,
						"status": "Completed",
						"percent": 100,
					}
				).insert(ignore_permissions=True)
	return {"accepted": True, "submission_id": doc.name, "status": status}
