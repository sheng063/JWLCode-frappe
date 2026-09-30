import unittest
from unittest.mock import patch

import frappe
import requests

from lms.lms import creation


class TestCreation(unittest.TestCase):
	def setUp(self):
		frappe.set_user('Administrator')
		self.users = []
		for _ in range(2):
			email = f'creation-{frappe.generate_hash(length=10)}@example.com'
			frappe.get_doc(dict(doctype='User', email=email, first_name='Creation QA',
				send_welcome_email=0, roles=[dict(role='LMS Student')])).insert(ignore_permissions=True)
			self.users.append(email)
		frappe.set_user(self.users[0])

	def tearDown(self):
		frappe.set_user('Administrator')
		frappe.db.rollback()

	def test_roundtrip_update_conflict_and_private_access(self):
		doc = creation.save_creation('作品', 'Python', 'print(input())', '你好')
		self.assertEqual(creation.get_creation(doc['name'])['stdin'], '你好')
		updated = creation.save_creation('新名称', 'C++', 'int main() {}', '', doc['name'], doc['modified'])
		self.assertEqual(creation.get_creation(doc['name'])['language'], 'C++')
		self.assertEqual(len(creation.get_creations(search='新名称')), 1)
		with self.assertRaises(frappe.TimestampMismatchError):
			creation.save_creation('旧版本', 'Python', name=doc['name'], modified=doc['modified'])
		frappe.set_user(self.users[1])
		self.assertEqual(creation.get_creations(), [])
		for action in (lambda: creation.get_creation(doc['name']), lambda: creation.save_creation(
			'他人作品', 'Python', name=doc['name'], modified=updated['modified'])):
			with self.assertRaises(frappe.PermissionError): action()
		self.assertFalse(frappe.has_permission('LMS Creation', 'read'))
		self.assertFalse(frappe.has_permission('LMS Creation', 'write'))

	def test_guest_denied(self):
		frappe.set_user('Guest')
		for action in (creation.get_creations, lambda: creation.get_creation('missing'),
			lambda: creation.save_creation('test', 'Python'), lambda: creation.run_creation('Python', 'print(1)')):
			with self.assertRaises(frappe.PermissionError): action()

	def test_validation_and_empty_draft(self):
		self.assertFalse(creation.save_creation('空白草稿', 'Python')['code'])
		for args in [(' ', 'Python', '', ''), ('x', 'JavaScript', '', ''),
			('x', 'Python', '中' * 90000, ''), ('x', 'Python', '', '中' * 22000)]:
			with self.assertRaises(frappe.ValidationError): creation.save_creation(*args)

	@patch('lms.lms.creation.requests.post')
	@patch('lms.lms.creation._get_settings')
	def test_run_uses_sandbox_and_does_not_save(self, settings, post):
		settings.return_value.service_url = 'http://judge'
		settings.return_value.request_timeout_seconds = 10
		settings.return_value.get_password.return_value = 'test-token'
		post.return_value.json.return_value = dict(status='WRONG_ANSWER', cases=[dict(stdout='hello\n')])
		result = creation.run_creation('Python', 'print(input())', 'hello')
		self.assertEqual(result, dict(status='COMPLETED', stdout='hello\n', stderr=''))
		self.assertEqual(post.call_args.kwargs['json']['test_cases'][0]['input'], 'hello')
		self.assertEqual(creation.get_creations(), [])
		post.return_value.json.return_value = dict(status='COMPILE_ERROR', compiler_message='syntax error')
		self.assertEqual(creation.run_creation('C++', 'bad')['stderr'], 'syntax error')
		post.side_effect = requests.Timeout()
		with self.assertRaises(frappe.ValidationError): creation.run_creation('Python', 'print(1)')

	def test_filtered_list_count_sort_and_no_source(self):
		creation.save_creation('Z Python', 'Python', 'secret code')
		creation.save_creation('A Python', 'Python', 'other secret')
		creation.save_creation('C Cpp', 'C++', 'int main() {}')
		result = creation.get_creations(language='Python', sort='title', with_total=True)
		self.assertEqual(result['total'], 2)
		self.assertEqual([row.title for row in result['items']], ['A Python', 'Z Python'])
		self.assertNotIn('code', result['items'][0])
		self.assertNotIn('stdin', result['items'][0])
		self.assertEqual(creation.get_creations(search='Z', with_total=True)['total'], 1)
		self.assertEqual(creation.get_creations(start=20, with_total=True)['items'], [])
		with self.assertRaises(frappe.ValidationError): creation.get_creations(sort='name; drop table')
		frappe.set_user(self.users[1])
		self.assertEqual(creation.get_creations(with_total=True)['total'], 0)

	def test_rename_delete_ownership_and_conflict(self):
		doc = creation.save_creation('原名称', 'Python', 'print(1)', 'input')
		updated = creation.rename_creation(doc['name'], '新名称', str(doc['modified']))
		stored = creation.get_creation(doc['name'])
		self.assertEqual(stored['title'], '新名称')
		self.assertEqual(stored['code'], 'print(1)')
		self.assertEqual(stored['stdin'], 'input')
		with self.assertRaises(frappe.TimestampMismatchError):
			creation.delete_creation(doc['name'], str(doc['modified']))
		frappe.set_user(self.users[1])
		with self.assertRaises(frappe.PermissionError):
			creation.rename_creation(doc['name'], '非法修改', str(updated['modified']))
		with self.assertRaises(frappe.PermissionError):
			creation.delete_creation(doc['name'], str(updated['modified']))
		frappe.set_user('Guest')
		with self.assertRaises(frappe.PermissionError): creation.delete_creation(doc['name'], str(updated['modified']))
		frappe.set_user(self.users[0])
		creation.delete_creation(doc['name'], str(updated['modified']))
		self.assertFalse(frappe.db.exists('LMS Creation', doc['name']))
