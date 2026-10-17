import base64
from unittest.mock import patch

import frappe
from lms.lms.test_helpers import BaseTestUtils
from lms.lms import game, game_access as access


class TestGameAccess(BaseTestUtils):
	def setUp(self):
		super().setUp()
		frappe.set_user('Administrator')
		self.suffix = frappe.generate_hash(length=10)
		self.a = self.user('a', 'LMS Student')
		self.b = self.user('b', 'LMS Student')
		self.teacher = self.user('teacher', 'Course Creator')
		self.other_teacher = self.user('other', 'Course Creator')
		self.course = self._create_course('Unlock ' + self.suffix, self.teacher)
		self.chapter = self._create_chapter('Chapter', self.course.name)
		self._create_chapter_reference(self.course.name, self.chapter.name)
		self.lessons = [self.add_lesson('Lesson 1'), self.add_lesson('Lesson 2')]
		for user in [self.a, self.b]:
			self._create_enrollment(user, self.course.name)
		game.set_game_enabled(1)
		access.set_course_rule(1, self.course.name)
		self.game = game.upload_game('test.html', base64.b64encode(b'<html>test</html>').decode())['name']

	def tearDown(self):
		frappe.set_user('Administrator')
		frappe.db.rollback()
		frappe.clear_cache(doctype='LMS Settings')

	def user(self, name, role):
		return self._create_user(f'game-access-{name}-{self.suffix}@example.com', name, 'QA', [role]).name

	def add_lesson(self, title):
		lesson = self._create_lesson(title, self.chapter.name, self.course.name)
		index = frappe.db.count('Lesson Reference', {'parent': self.chapter.name}) + 1
		reference = self._create_lesson_reference(self.chapter.name, lesson.name)
		reference.db_set('idx', index)
		return lesson.name

	def complete(self, user, lesson):
		frappe.set_user('Administrator')
		doc = self._create_progress(user, self.course.name, lesson)
		doc.status = 'Complete'
		doc.save()
		return doc

	def test_students_unlock_independently_and_html_api_enforces(self):
		for lesson in self.lessons:
			self.complete(self.a, lesson)
		self.assertTrue(access.get_game_access(self.a)['can_enter'])
		self.assertFalse(access.get_game_access(self.b)['can_enter'])
		frappe.set_user(self.a)
		self.assertIn('html', game.get_game(self.game))
		frappe.set_user(self.b)
		self.assertTrue(game.game_visible())
		self.assertEqual(access.get_game_access()['reason_code'], 'incomplete')
		for action in [game.get_games, lambda: game.get_game(self.game)]:
			with self.assertRaises(frappe.PermissionError): action()

	def test_override_precedence_and_default_off(self):
		access.save_student_access(self.a, access_mode='Allow')
		self.assertTrue(access.get_game_access(self.a)['can_enter'])
		game.set_game_enabled(0)
		self.assertFalse(access.get_game_access(self.a)['can_enter'])
		game.set_game_enabled(1)
		access.save_student_access(self.a, access_mode='Deny')
		access.set_course_rule(0)
		self.assertFalse(access.get_game_access(self.a)['can_enter'])
		self.assertTrue(access.get_game_access(self.b)['can_enter'])
		access.save_student_access(self.a)
		self.assertTrue(access.get_game_access(self.a)['can_enter'])
		frappe.db.set_value('User', self.a, 'enabled', 0)
		self.assertEqual(access.get_game_access(self.a)['reason_code'], 'disabled_user')

	def test_counts_distinct_current_lessons_and_revokes(self):
		for lesson in self.lessons:
			self.complete(self.a, lesson)
		# Duplicate references and obsolete completion rows must not inflate completion.
		self._create_lesson_reference(self.chapter.name, self.lessons[0])
		self.assertEqual(access.get_game_access(self.a)['total_lessons'], 2)
		added = self.add_lesson('New lesson')
		self.assertFalse(access.get_game_access(self.a)['can_enter'])
		enrollment = frappe.db.get_value('LMS Enrollment', {'member': self.a, 'course': self.course.name}, 'name')
		frappe.db.set_value('LMS Enrollment', enrollment, 'progress', 150)
		self.assertFalse(access.get_game_access(self.a)['can_enter'])
		progress = self.complete(self.a, added)
		self.assertTrue(access.get_game_access(self.a)['can_enter'])
		progress.status = 'Incomplete'; progress.save()
		self.assertFalse(access.get_game_access(self.a)['can_enter'])
		frappe.delete_doc('LMS Enrollment', enrollment)
		self.assertEqual(access.get_game_access(self.a)['reason_code'], 'not_enrolled')

	def test_empty_and_unconfigured_courses_fail_closed(self):
		empty = self._create_course('Empty ' + self.suffix, self.teacher)
		access.save_student_access(self.a, required_course=empty.name)
		self._create_enrollment(self.a, empty.name)
		self.assertEqual(access.get_game_access(self.a)['reason_code'], 'empty_course')
		access.save_student_access(self.a)
		frappe.db.set_single_value('LMS Settings', 'game_default_required_course', '')
		self.assertEqual(access.get_game_access(self.a)['reason_code'], 'no_course')

	def test_teacher_scope_and_forged_student_mutations(self):
		frappe.set_user(self.teacher)
		rows = access.get_students(search=self.suffix)
		self.assertEqual({r['student'] for r in rows['rows']}, {self.a, self.b})
		access.save_student_access(self.a, self.course.name, 'Allow')
		with self.assertRaises(frappe.PermissionError): access.set_course_rule(0)
		frappe.set_user(self.other_teacher)
		self.assertEqual(access.get_students(search=self.suffix)['total'], 0)
		with self.assertRaises(frappe.PermissionError): access.save_student_access(self.a, access_mode='Allow')
		frappe.set_user(self.b)
		for action in [lambda: access.save_student_access(self.b, access_mode='Allow'), access.get_students, access.get_access_options]:
			with self.assertRaises(frappe.PermissionError): action()
		self.assertFalse(frappe.has_permission(access.ACCESS_DOCTYPE, 'read'))
		self.assertFalse(frappe.has_permission(access.ACCESS_DOCTYPE, 'write'))

	def test_batch_and_course_scope_are_distinct(self):
		# A batch instructor may manage their batch, not all students of its course.
		batch = self._create_batch(self.course.name, instructor=self.other_teacher, title='Game batch ' + self.suffix, evaluator='')
		frappe.get_doc(dict(doctype='LMS Batch Enrollment', member=self.a, batch=batch.name)).insert(ignore_permissions=True)
		frappe.set_user(self.other_teacher)
		self.assertEqual({r['student'] for r in access.get_students(search=self.suffix)['rows']}, {self.a})
		access.save_student_access(self.a, self.course.name, 'Allow')
		with self.assertRaises(frappe.PermissionError): access.save_student_access(self.b, access_mode='Allow')

	def test_bulk_filters_pagination_and_audit_notifications(self):
		with patch.object(frappe, 'publish_realtime') as publish:
			access.bulk_student_access([self.a, self.b], 'assign_course', self.course.name)
			for user in [self.a, self.b]:
				self.assertTrue(any(c.kwargs.get('user') == user and c.kwargs.get('after_commit') for c in publish.call_args_list))
		# Current Frappe suppresses Version records by default while in_test.
		# Exercise production audit behavior explicitly for this assertion.
		with patch.object(frappe, 'in_test', False):
			access.save_student_access(self.a, self.course.name, 'Allow', 'Reward')
		result = access.get_students(search=self.suffix, status='unlocked', page_length=1)
		self.assertEqual(result['total'], 1)
		self.assertEqual(result['rows'][0]['student'], self.a)
		doc = frappe.get_doc(access.ACCESS_DOCTYPE, frappe.db.get_value(access.ACCESS_DOCTYPE, {'student': self.a}))
		self.assertEqual(doc.reason, 'Reward')
		self.assertTrue(frappe.db.exists('Version', {'ref_doctype': access.ACCESS_DOCTYPE, 'docname': doc.name}))
		access.bulk_student_access([self.a, self.b], 'reset')
		self.assertFalse(access.get_game_access(self.a)['can_enter'])
		self.assertEqual(access.get_game_access(self.a)['course_override'], '')

	def test_bulk_rejects_all_before_writing_and_validates_values(self):
		frappe.set_user(self.teacher)
		with self.assertRaises(frappe.ValidationError):
			access.bulk_student_access([self.a, 'Guest'], 'assign_course', self.course.name)
		self.assertFalse(frappe.db.exists(access.ACCESS_DOCTYPE, {'student': self.a}))
		for mode, reason in [('Invalid', ''), ('Allow', 'x' * 501)]:
			with self.assertRaises(frappe.ValidationError): access.save_student_access(self.a, access_mode=mode, reason=reason)

	def test_default_lesson_unlocks_without_finishing_entire_course(self):
		access.set_course_rule(1, self.course.name, self.lessons[1])
		self.complete(self.a, self.lessons[0])
		locked = access.get_game_access(self.a)
		self.assertEqual(locked['reason_code'], 'incomplete_lesson')
		self.assertEqual((locked['completed_lessons'], locked['total_lessons']), (0, 1))
		self.assertEqual(locked['lesson_title'], 'Lesson 2')
		frappe.set_user(self.a)
		with self.assertRaises(frappe.PermissionError): game.get_game(self.game)
		progress = self.complete(self.a, self.lessons[1])
		self.assertTrue(access.get_game_access(self.a)['can_enter'])
		self.assertFalse(access.get_game_access(self.b)['can_enter'])
		frappe.set_user(self.a)
		self.assertIn('html', game.get_game(self.game))
		frappe.set_user('Administrator')
		progress.status = 'Incomplete'; progress.save()
		self.assertFalse(access.get_game_access(self.a)['can_enter'])
		self.complete(self.b, self.lessons[1])
		self.assertTrue(access.get_game_access(self.b)['can_enter'])
		access.set_course_rule(1, self.course.name)
		self.assertFalse(access.get_game_access(self.b)['can_enter'])

	def test_individual_lesson_and_entire_course_override_default_target(self):
		access.set_course_rule(1, self.course.name, self.lessons[1])
		self.complete(self.a, self.lessons[0])
		frappe.set_user(self.teacher)
		access.save_student_access(self.a, self.course.name, required_lesson=self.lessons[0])
		self.assertTrue(access.get_game_access(self.a)['can_enter'])
		self.assertFalse(access.get_game_access(self.b)['can_enter'])
		access.save_student_access(self.a, self.course.name)
		self.assertEqual(access.get_game_access(self.a)['required_lesson'], '')
		self.assertEqual(access.get_game_access(self.a)['total_lessons'], 2)
		self.assertFalse(access.get_game_access(self.a)['can_enter'])
		access.save_student_access(self.a)
		self.assertEqual(access.get_game_access(self.a)['required_lesson'], self.lessons[1])

	def test_bulk_lesson_assignment_reset_and_existing_denial(self):
		frappe.set_user(self.teacher)
		access.save_student_access(self.a, access_mode='Deny')
		access.bulk_student_access([self.a, self.b], 'assign_course', self.course.name, self.lessons[0])
		for student in (self.a, self.b): self.complete(student, self.lessons[0])
		self.assertFalse(access.get_game_access(self.a)['can_enter'])
		self.assertTrue(access.get_game_access(self.b)['can_enter'])
		access.bulk_student_access([self.a, self.b], 'reset')
		for student in (self.a, self.b):
			self.assertEqual(access.get_game_access(student)['required_lesson'], '')
			self.assertFalse(access.get_game_access(student)['can_enter'])

	def test_lesson_options_are_ordered_scoped_and_reject_foreign_targets(self):
		other = self._create_course('Other target ' + self.suffix, self.other_teacher)
		chapter = self._create_chapter('Other chapter', other.name)
		self._create_chapter_reference(other.name, chapter.name)
		foreign = self._create_lesson('Foreign lesson', chapter.name, other.name)
		self._create_lesson_reference(chapter.name, foreign.name)
		frappe.set_user(self.teacher)
		self.assertEqual([row.name for row in access.get_course_lessons(self.course.name)], self.lessons)
		with self.assertRaises(frappe.PermissionError): access.get_course_lessons(other.name)
		with self.assertRaises(frappe.ValidationError):
			access.save_student_access(self.a, self.course.name, required_lesson=foreign.name)
		with self.assertRaises(frappe.ValidationError):
			access.bulk_student_access([self.a, self.b], 'assign_course', self.course.name, foreign.name)
		self.assertFalse(frappe.db.exists(access.ACCESS_DOCTYPE, {'student': self.a}))
		with self.assertRaises(frappe.ValidationError):
			access.save_student_access(self.a, required_lesson=self.lessons[0])
		frappe.set_user('Administrator')
		with self.assertRaises(frappe.ValidationError): access.set_course_rule(1, self.course.name, foreign.name)
		frappe.set_user(self.a)
		with self.assertRaises(frappe.PermissionError): access.get_course_lessons(self.course.name)

	def test_removed_lesson_and_enrollment_fail_closed(self):
		access.set_course_rule(1, self.course.name, self.lessons[0])
		self.complete(self.a, self.lessons[0])
		self.assertTrue(access.get_game_access(self.a)['can_enter'])
		frappe.db.delete('Lesson Reference', {'parent': self.chapter.name, 'lesson': self.lessons[0]})
		self.assertEqual(access.get_game_access(self.a)['reason_code'], 'invalid_lesson')
		self._create_lesson_reference(self.chapter.name, self.lessons[0])
		enrollment = frappe.db.get_value('LMS Enrollment', {'member': self.a, 'course': self.course.name}, 'name')
		frappe.delete_doc('LMS Enrollment', enrollment)
		self.assertEqual(access.get_game_access(self.a)['reason_code'], 'not_enrolled')
