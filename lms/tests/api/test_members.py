import frappe

from frappe.utils.password import check_password

from lms.lms.api import MEMBERS_PAGE_LENGTH, create_member, get_member, get_members, update_member
from lms.lms.test_helpers import BaseTestUtils


class TestCreateMember(BaseTestUtils):
	def setUp(self):
		super().setUp()
		self.moderator = self._create_user("member-moderator@example.com", "Member", "Moderator", ["Moderator"])
		frappe.set_user(self.moderator.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_creates_a_website_student_with_a_name_fallback_and_selected_roles(self):
		created = create_member("  Quick.Student@Example.com  ", roles=["Course Creator"])
		self.cleanup_items.append(("User", created["name"]))

		user = frappe.get_doc("User", created["name"])
		self.assertEqual(user.name, "quick.student@example.com")
		self.assertEqual(user.first_name, "quick.student")
		self.assertEqual(user.user_type, "Website User")
		self.assertIn("LMS Student", created["roles"])
		self.assertIn("Course Creator", created["roles"])

	def test_updates_profile_password_and_roles_together(self):
		student = self._create_user("editable-student@example.com", "Old", "Name", ["LMS Student"])
		password = "S3cure-Learning-Password!"

		updated = update_member(
			student.name,
			first_name="New",
			last_name="Student",
			phone="021-5555-1234",
			mobile_no="13800138000",
			new_password=password,
			roles=["LMS Student", "Course Creator"],
		)

		user = frappe.get_doc("User", student.name)
		self.assertEqual(user.first_name, "New")
		self.assertEqual(user.last_name, "Student")
		self.assertEqual(user.phone, "021-5555-1234")
		self.assertEqual(user.mobile_no, "13800138000")
		self.assertEqual(check_password(student.name, password), student.name)
		self.assertIn("Course Creator", updated.roles)
		self.assertNotIn("new_password", updated)

	def test_rejects_non_lms_roles_without_creating_a_user(self):
		email = "forbidden-role@example.com"
		with self.assertRaises(frappe.PermissionError):
			create_member(email, first_name="Forbidden", roles=["System Manager"])
		self.assertFalse(frappe.db.exists("User", email))

	def test_non_moderator_cannot_create_a_member(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			create_member("blocked@example.com", first_name="Blocked")


class TestGetMembers(BaseTestUtils):
	"""Settings > Users pages at MEMBERS_PAGE_LENGTH and searches the whole table.

	The frontend steps `start` by that same number, so a mismatch here silently
	skips or repeats a row on every Load More. Search has to reach past the
	first page, since the panel does not fetch the rest before searching.
	"""

	def setUp(self):
		super().setUp()
		self.moderator = self._create_user("moderator@example.com", "Mod", "Erator", ["Moderator"])
		self.members = [
			self._create_user(f"member{index}@example.com", "Member", str(index), ["LMS Student"])
			for index in range(2 * MEMBERS_PAGE_LENGTH + 3)
		]
		frappe.set_user(self.moderator.name)

	def _users_in_one_query(self, limit):
		"""What get_members would return if it never paged, read straight from
		the table with the same filters and ordering.

		Deriving this by paging through get_members would make the paging test
		circular: it would agree with itself however wrongly it paged.
		"""
		return [
			user.name
			for user in frappe.get_all(
				"User",
				filters=[
					["enabled", "=", 1],
					["name", "not in", ["Administrator", "Guest"]],
				],
				fields=["name"],
				limit_page_length=limit,
				start=0,
			)
		]

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_first_page_stops_at_the_page_length(self):
		self.assertEqual(len(get_members()), MEMBERS_PAGE_LENGTH)

	def test_second_page_continues_the_first_without_gap_or_repeat(self):
		"""Disjointness alone is not enough: it stays true when page two comes
		back empty or skips rows, which are the regressions this claims to pin."""
		first = [member.name for member in get_members()]
		second = [member.name for member in get_members(start=MEMBERS_PAGE_LENGTH)]
		both = first + second

		self.assertEqual(len(first), MEMBERS_PAGE_LENGTH)
		self.assertEqual(len(second), MEMBERS_PAGE_LENGTH, "page two came back short")
		self.assertEqual(len(set(both)), len(both), "a row was served on both pages")
		self.assertEqual(
			both,
			self._users_in_one_query(2 * MEMBERS_PAGE_LENGTH),
			"the two pages do not reconstruct the unpaged list",
		)

	def test_search_reaches_a_member_past_the_first_page(self):
		target = self.members[-1]

		found = get_members(search=target.first_name + " " + target.last_name)

		self.assertIn(target.name, [member.name for member in found])

	def test_search_matches_the_email_too(self):
		target = self.members[-1]

		found = get_members(search=target.name)

		self.assertIn(target.name, [member.name for member in found])

	def test_search_rejects_a_non_string(self):
		# @whitelist's pydantic argument check rejects the list with FrappeTypeError
		# before the body's own isinstance guard can throw ValidationError. Either
		# refusal satisfies the contract; the two classes are unrelated.
		with self.assertRaises((frappe.ValidationError, frappe.FrappeTypeError)):
			get_members(search=["ada"])


class TestGetMember(BaseTestUtils):
	"""The member edit form seeds itself from one exact row.

	It used to ask get_members for it, which pages and hides disabled users, so
	the two cases below came back empty and left Save disabled with nothing on
	screen explaining why.
	"""

	def setUp(self):
		super().setUp()
		self.moderator = self._create_user("moderator@example.com", "Mod", "Erator", ["Moderator"])
		self.members = [
			self._create_user(f"member{index}@example.com", "Member", str(index), ["LMS Student"])
			for index in range(MEMBERS_PAGE_LENGTH + 3)
		]
		frappe.set_user(self.moderator.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_returns_the_roles_of_the_member_asked_for(self):
		target = self.members[0]

		row = get_member(target.name)

		self.assertEqual(row.name, target.name)
		self.assertIn("LMS Student", row.roles)

	def test_reaches_a_member_past_the_first_page(self):
		# setUp creates three members more than a page holds, but which three fall
		# off it is get_members' ordering (newest first) rather than part of the
		# contract, so take the target from what the first page actually left out.
		first_page = [member.name for member in get_members()]
		off_page = [member for member in self.members if member.name not in first_page]

		self.assertTrue(off_page, "the fixture no longer exceeds one page")
		self.assertEqual(get_member(off_page[0].name).name, off_page[0].name)

	def test_reaches_a_disabled_member(self):
		target = self.members[0]
		frappe.db.set_value("User", target.name, "enabled", 0)

		self.assertNotIn(target.name, [member.name for member in get_members(search=target.name)])
		self.assertEqual(get_member(target.name).name, target.name)

	def test_rejects_a_member_that_does_not_exist(self):
		with self.assertRaises(frappe.DoesNotExistError):
			get_member("nobody@example.com")

	def test_rejects_the_built_in_accounts(self):
		for name in ["Administrator", "Guest"]:
			with self.assertRaises(frappe.ValidationError):
				get_member(name)

	def test_rejects_a_blank_member(self):
		with self.assertRaises(frappe.ValidationError):
			get_member("   ")

	def test_rejects_a_non_string(self):
		# Same two-class refusal as get_members' search guard.
		with self.assertRaises((frappe.ValidationError, frappe.FrappeTypeError)):
			get_member(["ada"])
