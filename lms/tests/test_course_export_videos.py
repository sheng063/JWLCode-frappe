import io
import json
import os
import tempfile
import unittest
import zipfile
from unittest.mock import patch

import frappe
from lms.lms import course_import_export as transfer


class TestCourseExportVideos(unittest.TestCase):
	def test_video_detection_does_not_exclude_audio_or_images(self):
		for name in ("clip.MP4", "clip.webm", "clip.mov", "clip.mkv", "clip%2Emp4", "clip.ogv"):
			self.assertTrue(transfer.is_video_asset("/private/files/" + name))
		for name in ("sound.mp3", "sound.ogg", "sound.wav", "cover.png", "notes.pdf"):
			self.assertFalse(transfer.is_video_asset("/files/" + name))

	def test_archive_contains_only_selected_assets(self):
		with tempfile.TemporaryDirectory() as directory:
			names = ["clip.MP4", "audio.mp3", "cover.png", "notes.pdf", "opaque"]
			for name in names:
				with open(os.path.join(directory, name), "wb") as stream:
					stream.write(name.encode())
			def document(doctype, name):
				return frappe._dict(file_name=name, file_type="MOV" if name == "opaque" else "", is_private=1,
					get_full_path=lambda: os.path.join(directory, name))
			assets = ["/private/files/" + name for name in names]
			with patch.object(frappe.db, "get_value", side_effect=lambda dt, filters, field: filters["file_url"].split("/")[-1]), patch.object(frappe, "get_doc", side_effect=document), patch.object(transfer, "is_safe_path", return_value=True):
				for include in (True, False):
					buffer = io.BytesIO()
					with zipfile.ZipFile(buffer, "w") as archive:
						transfer.write_assets(archive, assets, include_videos=include)
					with zipfile.ZipFile(buffer) as archive:
						manifest = json.loads(archive.read("assets.json"))
						expected = names if include else ["audio.mp3", "cover.png", "notes.pdf"]
						self.assertEqual([item["file_name"] for item in manifest], expected)
						self.assertEqual(len(archive.namelist()), len(expected) + 1)
						for item in manifest:
							self.assertEqual(archive.read(item["file"]), item["file_name"].encode())

	def test_excluded_missing_video_does_not_fail_export(self):
		with patch.object(frappe.db, "get_value") as lookup:
			with zipfile.ZipFile(io.BytesIO(), "w") as archive:
				transfer.write_assets(archive, ["/files/missing.mp4"], include_videos=False)
			lookup.assert_not_called()

	def test_export_option_reaches_archive_and_preserves_video_link(self):
		from lms.lms import course_export_jobs as jobs

		course = frappe.new_doc("LMS Course")
		course.name = "video-option-test"
		course.title = "Video option"
		course.description = '<video src="/files/clip.mp4"></video>'
		with tempfile.TemporaryDirectory() as directory:
			with patch.object(frappe, "get_doc", return_value=course), patch.object(transfer, "get_chapters_for_export", return_value=[]), patch.object(transfer, "get_lessons_for_export", return_value=[]), patch.object(transfer, "get_course_instructors", return_value=[]), patch.object(transfer, "get_course_evaluator", return_value=[]), patch.object(transfer, "get_course_assessments", return_value=([], [], [])), patch.object(jobs, "export_directory", return_value=directory):
				path = transfer.export_course_zip(course.name, download=False, include_videos="0")
				with zipfile.ZipFile(path) as archive:
					self.assertEqual(json.loads(archive.read("assets.json")), [])
					self.assertIn('/files/clip.mp4', json.loads(archive.read("course.json"))["description"])
