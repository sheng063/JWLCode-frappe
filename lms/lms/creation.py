"""Private code creations, persisted separately from assessed submissions."""

import frappe
import requests
from frappe.utils import cint

from lms.lms.judge_service import _get_settings

DOCTYPE = "LMS Creation"
FIELDS = ["name", "title", "language", "code", "stdin", "modified"]


def require_user():
	if frappe.session.user == "Guest":
		frappe.throw("请先登录。", frappe.PermissionError)


def validate_source(language, code, stdin):
	if language not in {"Python", "C++"}:
		frappe.throw("不支持的编程语言。")
	for value, limit, label in ((code, 256000, "代码"), (stdin, 64000, "输入")):
		if not isinstance(value, str) or len(value.encode("utf-8")) > limit:
			frappe.throw(f"{label}格式无效或超出大小限制（{limit} 字节）。")


def owned_creation(name):
	require_user()
	doc = frappe.get_doc(DOCTYPE, name)
	if doc.owner != frappe.session.user:
		frappe.throw("无权访问此作品。", frappe.PermissionError)
	return doc


def serialize(doc):
	return {field: doc.get(field) for field in FIELDS}


@frappe.whitelist()
def get_creation(name: str):
	return serialize(owned_creation(name))


@frappe.whitelist()
def get_creations(
	start: int = 0, search: str = "", language: str = "",
	sort: str = "modified", with_total: bool = False,
):
	require_user()
	if not isinstance(search, str) or len(search) > 140:
		frappe.throw("搜索内容过长。")
	orders = {"modified": "modified desc, name desc", "created": "creation desc, name desc", "title": "title asc, name asc"}
	if language not in {"", "Python", "C++"} or sort not in orders:
		frappe.throw("筛选或排序参数无效。")
	filters = {"owner": frappe.session.user}
	if language:
		filters["language"] = language
	if search.strip():
		filters["title"] = ["like", "%" + search.strip() + "%"]
	items = frappe.get_all(DOCTYPE, filters=filters,
		fields=["name", "title", "language", "modified"],
		order_by=orders[sort], start=max(0, cint(start)), page_length=20 if with_total else 21)
	if with_total:
		return {"items": items, "total": frappe.db.count(DOCTYPE, filters)}
	return items


@frappe.whitelist(methods=["POST"])
def save_creation(
	title: str, language: str, code: str = "", stdin: str = "",
	name: str | None = None, modified: str | None = None,
):
	require_user()
	validate_source(language, code, stdin)
	if not isinstance(title, str) or not title.strip() or len(title.strip()) > 140:
		frappe.throw("请输入 1 至 140 字的作品名称。")
	if name:
		doc = owned_creation(name)
		if not modified or str(doc.modified) != str(modified):
			frappe.throw("作品已在其他窗口更新，请重新打开后再保存。", frappe.TimestampMismatchError)
	else:
		doc = frappe.new_doc(DOCTYPE)
		doc.owner = frappe.session.user
	doc.update(dict(title=title.strip(), language=language, code=code, stdin=stdin))
	# Generic document endpoints have no access; the API checks ownership above.
	doc.save(ignore_permissions=True)
	return serialize(doc)


def check_revision(doc, modified):
	if not modified or str(doc.modified) != str(modified):
		frappe.throw("作品已更新，请刷新列表后重试。", frappe.TimestampMismatchError)


@frappe.whitelist(methods=["POST"])
def rename_creation(name: str, title: str, modified: str):
	doc = owned_creation(name)
	check_revision(doc, modified)
	if not isinstance(title, str) or not title.strip() or len(title.strip()) > 140:
		frappe.throw("请输入 1 至 140 字的作品名称。")
	doc.title = title.strip()
	doc.save(ignore_permissions=True)
	return {"name": doc.name, "title": doc.title, "modified": doc.modified}


@frappe.whitelist(methods=["POST"])
def delete_creation(name: str, modified: str):
	doc = owned_creation(name)
	check_revision(doc, modified)
	frappe.delete_doc(DOCTYPE, doc.name, ignore_permissions=True)
	return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def run_creation(language: str, code: str, stdin: str = ""):
	require_user()
	validate_source(language, code, stdin)
	if not code.strip():
		frappe.throw("请先编写代码。")
	settings = _get_settings()
	# Execute only in the existing remote judge sandbox, never in the LMS process.
	payload = dict(language=language, source_code=code,
		time_limit_seconds=4 if language == "Python" else 2, memory_limit_kb=128000,
		test_cases=[dict(input=stdin, expected_output="", hidden=False)])
	try:
		response = requests.post(
			f"{settings.service_url.rstrip('/')}/internal/v1/runs", json=payload,
			headers={"Authorization": f"Bearer {settings.get_password('api_token')}"},
			timeout=max(cint(settings.request_timeout_seconds), 135))
		response.raise_for_status()
		result = response.json()
	except (requests.RequestException, ValueError):
		frappe.throw("运行服务暂时不可用，请稍后重试。")
	cases = result.get("cases") or []
	case = cases[0] if cases else {}
	status = result.get("status")
	# Free creation has no expected answer: a completed run is successful.
	return dict(status="COMPLETED" if status in {"ACCEPTED", "WRONG_ANSWER"} and cases else status,
		stdout=case.get("stdout") or "",
		stderr=result.get("compiler_message") or case.get("stderr") or case.get("compile_output") or "")
