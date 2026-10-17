"""Server-authoritative, per-student Game access and teacher management."""

import frappe
from frappe.utils import cint

ACCESS_DOCTYPE = "LMS Game Student Access"
MODES = ("Automatic", "Allow", "Deny")
MESSAGES = {
	"login_required": "请登录后访问 Game。",
	"disabled_user": "该账号已停用。",
	"hidden": "教师尚未开放 Game 模块。",
	"denied": "教师暂未允许你进入 Game，请联系教师。",
	"no_course": "教师尚未设置解锁课程，请联系教师。",
	"not_enrolled": "请先报名指定课程，再完成学习。",
	"empty_course": "解锁课程尚无可完成的课时，请联系教师。",
	"invalid_lesson": "指定解锁课时已不属于该课程，请联系教师重新设置。",
	"incomplete_lesson": "完成指定课时后，即可进入 Game。",
	"incomplete": "完成指定课程的全部课时后，即可进入 Game。",
}


def is_access_admin(user=None):
	user = user or frappe.session.user
	return user == "Administrator" or bool({"System Manager", "Moderator"} & set(frappe.get_roles(user)))


def require_access_admin():
	if not is_access_admin():
		frappe.throw("只有管理员或 Moderator 可以修改全站课程解锁规则。", frappe.PermissionError)


def managed_scope():
	from lms.lms.game import require_manager
	require_manager()
	if is_access_admin():
		return None, None
	courses = set(frappe.get_all("Course Instructor", filters={"instructor": frappe.session.user, "parenttype": "LMS Course"}, pluck="parent"))
	batches = set(frappe.get_all("Course Instructor", filters={"instructor": frappe.session.user, "parenttype": "LMS Batch"}, pluck="parent"))
	return courses, batches


def assignable_courses(courses, batches):
	if courses is None:
		return None
	result = set(courses)
	if batches:
		result.update(frappe.get_all("Batch Course", filters={"parent": ["in", list(batches)], "parenttype": "LMS Batch"}, pluck="course"))
	return result


def scoped_students(courses, batches):
	if courses is None:
		return None
	students = set()
	if courses:
		students.update(frappe.get_all("LMS Enrollment", filters={"course": ["in", list(courses)]}, pluck="member"))
	if batches:
		students.update(frappe.get_all("LMS Batch Enrollment", filters={"batch": ["in", list(batches)]}, pluck="member"))
	return students


def require_student_scope(student, course=""):
	from lms.lms.game import can_manage_games
	courses, batches = managed_scope()
	if can_manage_games(student):
		frappe.throw("教师账号无需设置学生解锁规则。")
	if student in ("Guest", "Administrator") or not frappe.db.exists("Has Role", {"parent": student, "parenttype": "User", "role": "LMS Student"}):
		frappe.throw("请选择 LMS 学生账号。", frappe.ValidationError)
	if courses is not None and student not in scoped_students(courses, batches):
		frappe.throw("你只能管理自己课程或班级中的学生。", frappe.PermissionError)
	courses = assignable_courses(courses, batches)
	if course and (not frappe.db.exists("LMS Course", course) or (courses is not None and course not in courses)):
		frappe.throw("你无权指定此课程。", frappe.PermissionError)


def course_lessons(course):
	return frappe.db.sql("""select lr.lesson as name, lesson.title, ch.title as chapter_title
		from `tabChapter Reference` cr
		join `tabCourse Chapter` ch on ch.name = cr.chapter
		join `tabLesson Reference` lr on lr.parent = ch.name and lr.parenttype = 'Course Chapter'
		join `tabCourse Lesson` lesson on lesson.name = lr.lesson
		where cr.parenttype = 'LMS Course' and cr.parent = %s
		order by cr.idx, lr.idx""", course, as_dict=True)


def validate_unlock_target(course, lesson):
	if lesson and (not course or lesson not in {row.name for row in course_lessons(course)}):
		frappe.throw("请选择解锁课程中的课时。")


@frappe.whitelist()
def get_course_lessons(course: str):
	courses, batches = managed_scope()
	allowed = assignable_courses(courses, batches)
	if not course or (allowed is not None and course not in allowed):
		frappe.throw("你无权查看此课程的解锁课时。", frappe.PermissionError)
	if not frappe.db.exists("LMS Course", course):
		frappe.throw("指定课程不存在。")
	seen = set()
	result = []
	for row in course_lessons(course):
		if row.name not in seen:
			seen.add(row.name)
			result.append(row)
	return result


class AccessEvaluator:
	"""Batch reads avoid a database query for each student in the management table."""

	def __init__(self, users):
		users = list(set(users))
		self.settings = frappe.get_single("LMS Settings")
		self.users = {row.name: row for row in frappe.get_all("User", filters={"name": ["in", users]}, fields=["name", "enabled"])} if users else {}
		self.rules = {row.student: row for row in frappe.get_all(ACCESS_DOCTYPE, filters={"student": ["in", users]}, fields=["student", "required_course", "required_lesson", "access_mode", "reason", "modified", "modified_by"])} if users else {}
		course_names = {self.rules.get(user, {}).get("required_course") or self.settings.game_default_required_course for user in users} - {None, ""}
		self.courses = {row.name: row.title for row in frappe.get_all("LMS Course", filters={"name": ["in", list(course_names)]}, fields=["name", "title"])} if course_names else {}
		self.lessons = {}
		self.lesson_titles = {}
		if course_names:
			rows = frappe.db.sql("""select distinct cr.parent as course, lr.lesson, lesson.title
				from `tabChapter Reference` cr
				join `tabCourse Chapter` ch on ch.name = cr.chapter
				join `tabLesson Reference` lr on lr.parent = ch.name and lr.parenttype = 'Course Chapter'
				join `tabCourse Lesson` lesson on lesson.name = lr.lesson
				where cr.parenttype = 'LMS Course' and cr.parent in %(courses)s""", {"courses": tuple(course_names)}, as_dict=True)
			for row in rows:
				self.lessons.setdefault(row.course, set()).add(row.lesson)
				self.lesson_titles[row.lesson] = row.title
		self.enrolled = set()
		self.completed = {}
		if users and course_names:
			filters = {"member": ["in", users], "course": ["in", list(course_names)]}
			self.enrolled = {(row.member, row.course) for row in frappe.get_all("LMS Enrollment", filters=filters, fields=["member", "course"])}
			for row in frappe.get_all("LMS Course Progress", filters={**filters, "status": "Complete"}, fields=["member", "course", "lesson"]):
				self.completed.setdefault((row.member, row.course), set()).add(row.lesson)

	def evaluate(self, user, *, manager=False):
		rule = self.rules.get(user, {})
		course = rule.get("required_course") or self.settings.game_default_required_course or ""
		lesson = (rule.get("required_lesson") if rule.get("required_course") else self.settings.game_default_required_lesson) or ""
		lessons = self.lessons.get(course, set())
		targets = {lesson} if lesson else lessons
		result = dict(can_enter=False, reason_code="", message="", required_course=course,
			course_title=self.courses.get(course, ""), required_lesson=lesson,
			lesson_title=self.lesson_titles.get(lesson, ""), lesson_override=rule.get("required_lesson") or "",
			completed_lessons=len(targets & lessons & self.completed.get((user, course), set())),
			total_lessons=len(targets), access_mode=rule.get("access_mode") or "Automatic",
			course_override=rule.get("required_course") or "", reason=rule.get("reason") or "",
			modified=rule.get("modified"), modified_by=rule.get("modified_by"))
		if user == "Guest":
			code = "login_required"
		elif not self.users.get(user, {}).get("enabled"):
			code = "disabled_user"
		elif manager:
			code = "teacher"
		elif not cint(self.settings.game_enabled):
			code = "hidden"
		elif result["access_mode"] == "Deny":
			code = "denied"
		elif result["access_mode"] == "Allow":
			code = "manual_allow"
		elif not cint(self.settings.game_require_course_completion):
			code = "open"
		elif not course or course not in self.courses:
			code = "no_course"
		elif (user, course) not in self.enrolled:
			code = "not_enrolled"
		elif lesson and lesson not in lessons:
			code = "invalid_lesson"
		elif not lessons:
			code = "empty_course"
		elif result["completed_lessons"] != result["total_lessons"]:
			code = "incomplete_lesson" if lesson else "incomplete"
		else:
			code = "completed"
		result.update(reason_code=code, message=MESSAGES.get(code, "已解锁"), can_enter=code in ("teacher", "manual_allow", "open", "completed"))
		return result


def get_game_access(user=None):
	from lms.lms.game import can_manage_games
	user = user or frappe.session.user
	return AccessEvaluator([user]).evaluate(user, manager=can_manage_games(user))


@frappe.whitelist(methods=["POST"])
def set_course_rule(required: int, course: str = "", lesson: str = ""):
	require_access_admin()
	if str(required) not in ("0", "1"):
		frappe.throw("无效的课程解锁开关。")
	if course and not frappe.db.exists("LMS Course", course):
		frappe.throw("指定课程不存在。")
	if cint(required) and not course:
		frappe.throw("开启课程解锁前，请选择默认课程。")
	validate_unlock_target(course, lesson)
	settings = frappe.get_single("LMS Settings")
	settings.game_default_required_lesson = lesson or None
	settings.game_require_course_completion = cint(required)
	settings.game_default_required_course = course or None
	settings.save(ignore_permissions=True)
	from lms.lms.game import get_game_settings
	return get_game_settings()


@frappe.whitelist()
def get_access_options():
	courses, batches = managed_scope()
	courses = assignable_courses(courses, batches)
	return dict(can_configure=is_access_admin(),
		courses=frappe.get_all("LMS Course", filters={} if courses is None else {"name": ["in", list(courses)]}, fields=["name", "title"], order_by="title"),
		batches=frappe.get_all("LMS Batch", filters={} if batches is None else {"name": ["in", list(batches)]}, fields=["name", "title"], order_by="title"))


@frappe.whitelist()
def get_students(search: str = "", batch: str = "", course: str = "", status: str = "", start: int = 0, page_length: int = 20):
	courses, batches = managed_scope()
	allowed = scoped_students(courses, batches)
	if batch:
		if batches is not None and batch not in batches:
			frappe.throw("无权查看该班级。", frappe.PermissionError)
		members = set(frappe.get_all("LMS Batch Enrollment", filters={"batch": batch}, pluck="member"))
		allowed = members if allowed is None else allowed & members
	course_scope = assignable_courses(courses, batches)
	if course and course_scope is not None and course not in course_scope:
		frappe.throw("无权查看该课程。", frappe.PermissionError)
	filters = {"name": ["not in", ["Guest", "Administrator"]]}
	role_users = set(frappe.get_all("Has Role", filters={"role": "LMS Student", "parenttype": "User"}, pluck="parent"))
	staff = set(frappe.get_all("Has Role", filters={"role": ["in", ["System Manager", "Moderator", "Course Creator"]], "parenttype": "User"}, pluck="parent"))
	role_users -= staff
	filters["name"] = ["in", list(role_users if allowed is None else role_users & allowed)]
	users = frappe.get_all("User", filters=filters, or_filters={"name": ["like", f"%{search[:140]}%"], "full_name": ["like", f"%{search[:140]}%"]} if search else None, fields=["name", "full_name", "enabled"], order_by="full_name, name")
	evaluator = AccessEvaluator([u.name for u in users])
	rows = []
	for user in users:
		access = evaluator.evaluate(user.name)
		if course and access["required_course"] != course:
			continue
		if status == "unlocked" and not access["can_enter"] or status == "locked" and access["can_enter"]:
			continue
		rows.append(dict(student=user.name, full_name=user.full_name, **access))
	start, page_length = max(0, cint(start)), min(100, max(1, cint(page_length)))
	return dict(rows=rows[start:start + page_length], total=len(rows))


@frappe.whitelist(methods=["POST"])
def save_student_access(student: str, required_course: str = "", access_mode: str = "Automatic", reason: str = "", required_lesson: str = ""):
	require_student_scope(student, required_course)
	# Serialize edits, including the initial insert, on the student's User row.
	frappe.db.get_value("User", student, "name", for_update=True)
	name = frappe.db.get_value(ACCESS_DOCTYPE, {"student": student}, "name")
	doc = frappe.get_doc(ACCESS_DOCTYPE, name) if name else frappe.new_doc(ACCESS_DOCTYPE)
	doc.update(dict(student=student, required_course=required_course or None, required_lesson=required_lesson or None, access_mode=access_mode, reason=reason.strip()))
	doc.save(ignore_permissions=True)
	return get_game_access(student)


@frappe.whitelist(methods=["POST"])
def bulk_student_access(students: list[str], action: str, required_course: str = "", required_lesson: str = ""):
	if not students or len(students) > 100 or action not in ("assign_course", "reset"):
		frappe.throw("每次请选择 1–100 名学生及有效操作。")
	if action == "assign_course" and not required_course:
		frappe.throw("请选择课程。")
	for student in set(students):
		require_student_scope(student, required_course)
	validate_unlock_target(required_course, required_lesson)
	# One HTTP transaction: a failure rolls back the whole batch.
	for student in sorted(set(students)):
		if action == "reset":
			save_student_access(student, access_mode="Automatic", reason="批量恢复自动规则")
		else:
			rule = frappe.db.get_value(ACCESS_DOCTYPE, {"student": student}, ["access_mode", "reason"], as_dict=True) or {}
			save_student_access(student, required_course, rule.get("access_mode") or "Automatic", rule.get("reason") or "", required_lesson=required_lesson)
	return {"updated": len(set(students))}


def notify_access_change(doc, method=None):
	user = doc.get("student") or doc.get("member")
	if doc.doctype == "User":
		user = doc.name
	if user:
		frappe.publish_realtime("lms_game_access_changed", user=user, after_commit=True)
	else:
		frappe.publish_realtime("lms_game_access_changed", room="website", after_commit=True)
