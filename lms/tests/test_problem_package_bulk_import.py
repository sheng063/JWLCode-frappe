"""Bundle boundary regressions; no database required."""

import hashlib
import io
import json
import zipfile
from unittest import TestCase
from unittest.mock import Mock, patch

from lms.lms.problem_package import bulk_import
from lms.lms.problem_package.parser import PackageError


def bundle(files):
	out = io.BytesIO()
	with zipfile.ZipFile(out, "w") as archive:
		for path, data in files.items():
			archive.writestr(path, data)
	return out.getvalue()


class TestReadBundle(TestCase):
	def test_export_manifest_restores_only_reviewable_settings(self):
		data = b"opaque package"
		manifest = [
			{
				"file": "p001.zip",
				"sha256": hashlib.sha256(data).hexdigest(),
				"exercise": "DO-NOT-OVERWRITE",
				"package_version": "OLD",
				"judge_config": {
					"language": "Python",
					"time_limit_seconds": 3,
					"memory_limit_kb": 131072,
					"command": "ignore",
				},
			}
		]
		result = bulk_import.read_bundle(
			bundle({"p001.zip": data, "manifest.json": json.dumps(manifest), "README.txt": "info"})
		)
		self.assertEqual(
			result,
			[("p001.zip", data, {"language": "Python", "time_limit_seconds": 3, "memory_limit_kb": 131072})],
		)

	def test_plain_bundle_does_not_require_manifest(self):
		self.assertEqual(
			bulk_import.read_bundle(bundle({"p001.kpp": b"package"})), [("p001.kpp", b"package", {})]
		)

	def test_rejects_unsafe_or_unexpected_layouts(self):
		for files in (
			{"../p001.zip": b"x"},
			{"dir/p001.zip": b"x"},
			{"problem.yaml": b"name: Single"},
			{"p001.zip": b"x", "script.sh": b"command"},
		):
			with self.subTest(files=files), self.assertRaises(PackageError):
				bulk_import.read_bundle(bundle(files))

	def test_rejects_checksum_mismatch_and_duplicate_manifest_entries(self):
		for manifest in (
			[{"file": "p001.zip", "sha256": "wrong"}],
			[{"file": "p001.zip"}] * 2,
			[{"file": "missing.zip"}],
			{"file": "p001.zip"},
		):
			with self.subTest(manifest=manifest), self.assertRaises(PackageError):
				bulk_import.read_bundle(bundle({"p001.zip": b"x", "manifest.json": json.dumps(manifest)}))

	def test_accepts_large_bundles_with_and_without_manifest(self):
		for count in (51, 2001):
			for with_manifest in (False, True):
				with self.subTest(count=count, manifest=with_manifest):
					files = {f"p{i:04}.zip": b"x" for i in range(count)}
					if with_manifest:
						files["manifest.json"] = json.dumps([{"file": path} for path in files])
					self.assertEqual(len(bulk_import.read_bundle(bundle(files))), count)

	def test_rejects_empty_bundle(self):
		with self.assertRaises(PackageError):
			bulk_import.read_bundle(bundle({}))

	@patch.object(bulk_import, "_", lambda text: text)
	@patch.object(bulk_import, "_enabled")
	@patch.object(bulk_import, "_manage")
	@patch.object(bulk_import, "frappe")
	def test_another_users_or_public_upload_is_rejected(self, frappe, manage, enabled):
		frappe.session.user = "teacher"
		frappe.throw.side_effect = PermissionError
		for owner, private in [("another", True), ("teacher", False)]:
			file = Mock(owner=owner, is_private=private)
			frappe.get_doc.return_value = file
			with self.assertRaises(PermissionError):
				bulk_import.create_bulk_import("FILE")
			file.get_content.assert_not_called()

	def test_ignores_macos_metadata_in_bundle(self):
		self.assertEqual(bulk_import.read_bundle(bundle({
			"p001.zip": b"package", "__MACOSX/._p001.zip": b"metadata",
			".DS_Store": b"metadata", "._p001.zip": b"metadata",
		})), [("p001.zip", b"package", {})])
