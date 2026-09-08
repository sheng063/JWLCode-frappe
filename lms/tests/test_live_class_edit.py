"""Live class edits must be authorized, update the event, and retain meeting identity."""

from unittest.mock import Mock, patch

import frappe
from frappe.utils import nowdate

from lms.lms.doctype.lms_live_class.lms_live_class import LMSLiveClass, update_live_class
from lms.tests.test_course_visibility_and_batches import BatchVisibilityFixtures, as_user


class TestLiveClassEdit(BatchVisibilityFixtures):
	def setUp(self):
		super().setUp()
		self.event = frappe.get_doc(
			{
				"doctype": "Event",
				"subject": "Original",
				"starts_on": f"{nowdate()} 09:00:00",
				"event_type": "Private",
			}
		).insert()
		with patch.object(LMSLiveClass, "create_calendar_event"):
			self.live_class = frappe.get_doc(
				{
					"doctype": "LMS Live Class",
					"title": "Original",
					"description": "Original notes",
					"batch_name": self.batch.name,
					"date": nowdate(),
					"time": "09:00:00",
					"duration": 60,
					"timezone": "Asia/Shanghai",
					"host": "Administrator",
					"event": self.event.name,
					"auto_recording": "No Recording",
				}
			).insert()

	def update(self, **values):
		return update_live_class(self.live_class.name, values, str(self.live_class.modified))

	def test_edit_updates_title_description_and_calendar(self):
		name = self.update(title="Updated", description="New notes", time="10:00", duration=90)
		self.assertEqual(name, self.live_class.name)
		self.live_class.reload()
		self.assertEqual(self.live_class.title, "Updated")
		self.event.reload()
		self.assertEqual(self.event.subject, "Live Class on Updated")
		self.assertIn("New notes", self.event.description)
		self.assertEqual(str(self.event.ends_on)[11:16], "11:30")

	def test_description_only_edit_updates_calendar(self):
		self.update(description="Only the notes changed")
		self.event.reload()
		self.assertIn("Only the notes changed", self.event.description)

	def test_student_cannot_edit(self):
		self._create_batch_enrollment(self.student.name, self.batch.name)
		with as_user(self.student.name), self.assertRaises(frappe.PermissionError):
			self.update(title="Unauthorized")
		self.live_class.reload()
		self.assertEqual(self.live_class.title, "Original")

	def test_stale_form_is_rejected_before_provider_call(self):
		with patch("lms.lms.doctype.lms_live_class.lms_live_class.requests.patch") as provider:
			with self.assertRaises(frappe.TimestampMismatchError):
				update_live_class(self.live_class.name, {"title": "Stale"}, "2000-01-01 00:00:00")
			provider.assert_not_called()

	def test_only_editable_fields_are_accepted(self):
		self.update(
			title="Allowed", batch_name="other-batch", host=self.student.name, meeting_id="fake", event=None
		)
		self.live_class.reload()
		self.assertEqual(self.live_class.batch_name, self.batch.name)
		self.assertEqual(self.live_class.host, "Administrator")
		self.assertEqual(self.live_class.event, self.event.name)
		self.assertFalse(self.live_class.meeting_id)

	def test_invalid_duration_or_timezone_is_rejected(self):
		for values in [{"duration": 0}, {"duration": -2}, {"timezone": "invalid-zone"}]:
			with self.subTest(values=values), self.assertRaises(frappe.ValidationError):
				self.update(**values)

	def test_zoom_update_retains_meeting_and_sends_new_details(self):
		# The account's OAuth behavior is unrelated to editing; never call the network.
		frappe.db.set_value(
			"LMS Live Class", self.live_class.name, {"meeting_id": "12345", "zoom_account": "test-account"}
		)
		self.live_class.reload()
		with (
			patch("lms.lms.doctype.lms_live_class.lms_live_class.authenticate", return_value="test-token"),
			patch(
				"lms.lms.doctype.lms_live_class.lms_live_class.requests.patch",
				return_value=Mock(status_code=204),
			) as provider,
			patch.object(LMSLiveClass, "_validate_links"),
		):
			self.update(title="Zoom updated", time="13:30", duration=45)
			self.assertEqual(provider.call_args.args[0], "https://api.zoom.us/v2/meetings/12345")
			self.assertEqual(provider.call_args.kwargs["json"]["topic"], "Zoom updated")
			self.assertEqual(provider.call_args.kwargs["json"]["duration"], 45)
		self.live_class.reload()
		self.assertEqual(str(self.live_class.meeting_id), "12345")

	def test_provider_failure_leaves_local_class_unchanged(self):
		frappe.db.set_value(
			"LMS Live Class", self.live_class.name, {"meeting_id": "12345", "zoom_account": "test-account"}
		)
		self.live_class.reload()
		with (
			patch("lms.lms.doctype.lms_live_class.lms_live_class.authenticate", return_value="test-token"),
			patch(
				"lms.lms.doctype.lms_live_class.lms_live_class.requests.patch",
				return_value=Mock(status_code=500),
			),
			self.assertRaises(frappe.ValidationError),
		):
			self.update(title="Must not save")
		self.live_class.reload()
		self.assertEqual(self.live_class.title, "Original")
