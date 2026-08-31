app_name = "jwlcode"
app_title = "JWLCode"
app_publisher = "JWLCode Team"
app_description = "C++ teaching platform business backend"
app_email = "dev@example.invalid"
app_license = "MIT"
app_logo_url = "/assets/jwlcode/images/edu-code.svg"
app_home = "/app/edu-code"

add_to_apps_screen = [
	{
		"name": app_name,
		"logo": app_logo_url,
		"title": "Edu Code",
		"route": app_home,
		"has_permission": "frappe.permissions.check_app_permission",
	}
]

before_install = "jwlcode.setup.install.ensure_roles"
after_install = "jwlcode.setup.install.after_install"
after_migrate = "jwlcode.setup.install.ensure_indexes"

permission_query_conditions = {
	"JWL Student": "jwlcode.permission_rules.student_query",
	"JWL Enrollment": "jwlcode.permission_rules.enrollment_query",
	"JWL Academic Class": "jwlcode.permission_rules.class_query",
	"JWL Progress": "jwlcode.permission_rules.progress_query",
	"JWL Submission": "jwlcode.permission_rules.submission_query",
	"JWL Score": "jwlcode.permission_rules.score_query",
	"JWL Score Adjustment": "jwlcode.permission_rules.score_adjustment_query",
}

has_permission = {
	"JWL Student": "jwlcode.permission_rules.student_permission",
	"JWL Enrollment": "jwlcode.permission_rules.enrollment_permission",
	"JWL Academic Class": "jwlcode.permission_rules.class_permission",
	"JWL Progress": "jwlcode.permission_rules.progress_permission",
	"JWL Submission": "jwlcode.permission_rules.submission_permission",
	"JWL Score": "jwlcode.permission_rules.score_permission",
	"JWL Score Adjustment": "jwlcode.permission_rules.score_adjustment_permission",
}

scheduler_events = {
	"cron": {
		"*/5 * * * *": ["jwlcode.integrations.judge.retry_queued_submissions"],
	}
}

# Frappe already exposes DocType CRUD through /api/resource. These methods only
# implement domain operations that cannot be expressed as generic CRUD.
