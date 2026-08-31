from __future__ import annotations

import hashlib
import hmac
import json
from urllib.parse import urljoin

import frappe
from frappe.integrations.utils import make_post_request
from frappe.utils import add_to_date, now_datetime


def _config() -> tuple[str, str]:
	url = frappe.conf.get("jwlcode_judge_service_url")
	token = frappe.conf.get("jwlcode_judge_service_token")
	if not url or not token:
		raise frappe.ValidationError("Judge Service is not configured")
	return str(url).rstrip("/") + "/", str(token)


def dispatch_submission(submission: str) -> None:
	"""Background entrypoint. A timeout leaves the submission queued for reconciliation."""
	doc = frappe.get_doc("JWL Submission", submission)
	if doc.judge_request_id or doc.status != "QUEUED":
		return
	url, token = _config()
	payload = {
		"submission_id": doc.name,
		"request_type": doc.submission_type.lower(),
		"problem_version": doc.problem_version,
		"test_case_ref": doc.test_case_ref,
		"test_case_checksum": doc.test_case_checksum,
		"language": doc.language,
		"source_code": doc.source_code,
		"custom_input": doc.custom_input if doc.submission_type == "Run" else None,
		"resource_limits": json.loads(doc.policy_snapshot or "{}"),
		"callback_url": urljoin(frappe.utils.get_url().rstrip("/") + "/", "api/method/jwlcode.api.v1.judge_callback"),
		"idempotency_key": doc.client_request_id,
		"trace_id": doc.trace_id,
	}
	try:
		response = make_post_request(
			urljoin(url, "internal/v1/judge-requests"),
			headers={"Authorization": f"Bearer {token}"},
			json=payload,
		)
	except Exception:
		frappe.log_error(title=f"Judge dispatch pending: {submission}")
		return
	judge_request_id = response.get("judge_request_id")
	if judge_request_id:
		frappe.db.set_value("JWL Submission", doc.name, "judge_request_id", judge_request_id, update_modified=False)


def retry_queued_submissions() -> None:
	"""Re-dispatch stranded requests; the Judge Service idempotency key prevents duplicate execution."""
	for submission in frappe.get_all(
		"JWL Submission",
		filters={
			"status": "QUEUED",
			"judge_request_id": ["is", "not set"],
			"creation": ["<", add_to_date(now_datetime(), seconds=-30)],
		},
		pluck="name",
		limit_page_length=100,
	):
		frappe.enqueue(
			"jwlcode.integrations.judge.dispatch_submission",
			queue="short",
			submission=submission,
			job_id=f"jwlcode-dispatch-{submission}",
			deduplicate=True,
		)


def verify_callback(raw_body: bytes, timestamp: str, signature: str) -> None:
	secret = frappe.conf.get("jwlcode_judge_callback_secret")
	if not secret:
		raise frappe.AuthenticationError("Judge callback secret is not configured")
	try:
		age = abs(frappe.utils.now_datetime().timestamp() - float(timestamp))
	except (TypeError, ValueError):
		raise frappe.AuthenticationError("Invalid callback timestamp") from None
	if age > 300:
		raise frappe.AuthenticationError("Expired callback timestamp")
	expected = hmac.new(str(secret).encode(), timestamp.encode() + b"." + raw_body, hashlib.sha256).hexdigest()
	provided = signature.removeprefix("sha256=")
	if not hmac.compare_digest(expected, provided):
		raise frappe.AuthenticationError("Invalid callback signature")
