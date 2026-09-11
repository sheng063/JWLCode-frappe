"""Statement delivery uses source bytes and preserves access checks."""
import io
import json
import zipfile
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from lms.lms.problem_package import api


@pytest.mark.parametrize("extension,mime", [("tex", "text/plain; charset=utf-8"), ("pdf", "application/pdf")])
def test_preview_and_download_preserve_format(extension, mime):
	path = f"problem_statement/problem.zh.{extension}"
	data = b"\\section{Example}" if extension == "tex" else b"%PDF-1.4\n"
	out = io.BytesIO()
	with zipfile.ZipFile(out, "w") as archive:
		archive.writestr("__MACOSX/._problem", b"metadata")
		archive.writestr("example/" + path, data)
	record = SimpleNamespace(report=json.dumps({"statements": [path]}))
	version = SimpleNamespace(name="V1", exercise="E1", import_record="I1", statement_path=path)
	exercise = SimpleNamespace(active_package_version="V1", check_permission=Mock())
	frappe = Mock()
	frappe.session.user = "student"
	frappe.local.response = SimpleNamespace()
	frappe.get_doc.side_effect = lambda kind, name: {api.VERSION: version, api.EXERCISE: exercise, api.IMPORT: record}[kind]
	with patch.object(api, "frappe", frappe), patch.object(api, "_owned", return_value=record) as owned, patch.object(api, "_content", return_value=out.getvalue()):
		api.preview_statement("I1", path)
		owned.assert_called_once_with("I1")
		assert frappe.local.response.filecontent == data
		assert frappe.local.response.content_type == mime
		assert frappe.local.response.filename == "statement." + extension
		api.download_statement("V1")
		exercise.check_permission.assert_called_once_with("read")
		assert frappe.local.response.filecontent == data
		assert frappe.local.response.content_type == mime
		assert frappe.local.response.filename == "statement." + extension
		assert frappe.local.response.display_content_as == "attachment"


def test_source_endpoint_only_returns_owned_approved_tex():
	path = "problem_statement/problem.zh.tex"
	out = io.BytesIO()
	with zipfile.ZipFile(out, "w") as archive:
		archive.writestr("example/" + path, "\\section{题目} $a+b$")
		archive.writestr("example/data/secret/01.in", "SECRET")
	record = SimpleNamespace(report=json.dumps({"statements": [path]}))
	frappe = Mock()
	frappe.throw.side_effect = ValueError
	with patch.object(api, "frappe", frappe), patch.object(api, "_owned", return_value=record) as owned, patch.object(api, "_content", return_value=out.getvalue()) as content:
		assert api.get_statement_source("I1", path)["source"] == "\\section{题目} $a+b$"
		owned.assert_called_once_with("I1")
		content.reset_mock()
		with pytest.raises(ValueError):
			api.get_statement_source("I1", "data/secret/01.in")
		content.assert_not_called()
		owned.side_effect = PermissionError
		with pytest.raises(PermissionError):
			api.get_statement_source("I1", path)
