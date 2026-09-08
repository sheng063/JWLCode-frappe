"""Language-aware formatting for the programming exercise editor."""

import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

import frappe
from frappe import _


@frappe.whitelist()
def format_code(code: str, language: str, tab_size: int = 4):
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in to format code."), frappe.PermissionError)
	if not isinstance(code, str) or len(code.encode("utf-8")) > 200_000:
		frappe.throw(_("Code must be text and no larger than 200 KB."))
	if language not in ("Python", "C++"):
		frappe.throw(_("Unsupported programming language."))
	try:
		tab_size = int(tab_size)
	except (TypeError, ValueError):
		frappe.throw(_("Invalid indentation size."))
	if tab_size not in (2, 4, 8):
		frappe.throw(_("Invalid indentation size."))
	if not code.strip():
		return code

	if language == "Python":
		# Black uses standard four-space Python indentation, independent of Tab width.
		command = [sys.executable, "-m", "black", "--quiet", "--config", str(Path(__file__).with_name("formatter.toml")), "-"]
	else:
		binary = Path(sysconfig.get_path("scripts")) / "clang-format"
		executable = str(binary) if binary.is_file() else shutil.which("clang-format")
		if not executable:
			frappe.throw(_("C++ formatter is unavailable. Please install the LMS dependencies."))
		command = [executable, "--assume-filename=main.cpp", f"--style={{BasedOnStyle: LLVM, IndentWidth: {tab_size}, UseTab: Never}}"]
	try:
		result = subprocess.run(command, input=code, text=True, encoding="utf-8", capture_output=True, timeout=10, check=False)
	except (OSError, subprocess.TimeoutExpired):
		frappe.throw(_("Code formatting is unavailable or timed out. Please try again."))
	if result.returncode:
		frappe.throw(_("Unable to format code. Check the syntax and that LMS formatter dependencies are installed."))
	return result.stdout
