"""Prepare large course archives outside HTTP requests; serve them without buffering."""
import os
import secrets
import time

import frappe
from frappe import _

RETENTION = 24 * 60 * 60
JOB_TIMEOUT = 6 * 60 * 60


def export_directory():
	path = frappe.get_site_path("private", "course-exports")
	os.makedirs(path, exist_ok=True)
	return path


def _save(export_id, state):
	frappe.cache.set_value("course-export:" + export_id, state, expires_in_sec=RETENTION)


def _authorize(course_name):
	from lms.lms.api import can_modify_course

	if not can_modify_course(course_name):
		frappe.throw(_("You do not have permission to export this course."), frappe.PermissionError)


def _state(export_id):
	state = frappe.cache.get_value("course-export:" + export_id)
	if not state or state["owner"] != frappe.session.user:
		frappe.throw(_("Export not found or expired."), frappe.PermissionError)
	_authorize(state["course"])
	return state


@frappe.whitelist(methods=["POST"])
def start_export(course_name: str, include_videos: bool = True):
	_authorize(course_name)
	include_videos = bool(frappe.utils.cint(include_videos))
	# Reuse an in-progress export for this user, including after a page refresh.
	key = "course-export-active:" + frappe.session.user + ":" + course_name + ":videos=" + str(int(include_videos))
	with frappe.cache.lock(key + ":lock", timeout=10):
		existing = frappe.cache.get_value(key)
		state = frappe.cache.get_value("course-export:" + existing) if existing else None
		if state and state["status"] in ("queued", "running") and time.time() - state["created"] < JOB_TIMEOUT:
			return {"export_id": existing}
		export_id = secrets.token_hex(24)
		state = dict(owner=frappe.session.user, course=course_name, status="queued", created=time.time(), include_videos=include_videos)
		_save(export_id, state)
		try:
			frappe.enqueue(
				"lms.lms.course_export_jobs.prepare_export", queue="long", timeout=JOB_TIMEOUT,
				export_id=export_id, enqueue_after_commit=True,
			)
		except Exception:
			frappe.cache.delete_value("course-export:" + export_id)
			raise
		frappe.cache.set_value(key, export_id, expires_in_sec=RETENTION - 3600)
	return {"export_id": export_id}


def prepare_export(export_id):
	from lms.lms.course_import_export import export_course_zip

	state = frappe.cache.get_value("course-export:" + export_id)
	if not state:
		return
	try:
		_authorize(state["course"])
		state["status"] = "running"
		_save(export_id, state)
		state["path"] = export_course_zip(state["course"], download=False, include_videos=state.get("include_videos", True))
		state["status"] = "ready"
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Course export failed")
		state["status"] = "failed"
		state["error"] = _("Course export failed. Please retry or contact the administrator.")
	_save(export_id, state)


@frappe.whitelist()
def export_status(export_id: str):
	state = _state(export_id)
	if state["status"] in ("queued", "running") and time.time() - state["created"] >= JOB_TIMEOUT:
		return {"status": "failed", "error": _("Course export timed out. Please retry.")}
	if state["status"] == "ready" and not os.path.isfile(state["path"]):
		return {"status": "failed", "error": _("Export expired. Please export the course again.")}
	return {"status": state["status"], "error": state.get("error")}


@frappe.whitelist()
def download_export(export_id: str):
	from lms.lms.course_import_export import serve_zip

	state = _state(export_id)
	if state["status"] != "ready":
		frappe.throw(_("Export is not ready."))
	return serve_zip(state["path"], os.path.basename(state["path"]))


def cleanup_exports():
	# A queue timeout limits execution; it does not delay a deletion job.
	cutoff = time.time() - RETENTION
	for entry in os.scandir(export_directory()):
		if entry.is_file(follow_symlinks=False) and entry.name.endswith((".zip", ".partial")):
			try:
				if entry.stat().st_mtime < cutoff:
					os.remove(entry.path)
			except FileNotFoundError:
				pass
