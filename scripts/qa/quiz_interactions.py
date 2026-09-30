"""Integration checks in local bench; every test rolls back its data."""
import json
import os
import unittest
from unittest.mock import patch

import frappe
os.chdir('/home/frappe/bench-data/frappe-bench/sites')
frappe.init(site='school.localhost')
frappe.connect()
frappe.set_user('Administrator')
from lms.lms.quiz_interactions import grade_answer, public_question, check_match
from lms.lms.doctype.lms_quiz.lms_quiz import process_results, check_answer, submit_quiz
from lms.lms.utils import get_quiz_with_questions

class InteractiveQuizTests(unittest.TestCase):
    def tearDown(self):
        frappe.db.rollback()
    def make(self, kind):
        q = frappe.get_doc(dict(doctype='LMS Question', question='Interactive QA', type=kind,
            interactive_items=json.dumps([dict(text='A', right='X'), dict(text='B', right='Y')]))).insert()
        quiz = frappe.get_doc(dict(doctype='LMS Quiz', title='Interactive QA ' + frappe.generate_hash(length=8), passing_percentage=100,
            questions=[dict(question=q.name, marks=2)], show_answers=0)).insert()
        return q, quiz, json.loads(q.interactive_items)
    def test_ordering(self):
        q, quiz, items = self.make('Ordering')
        answer = [i['id'] for i in items]
        self.assertTrue(grade_answer(q.name, answer)[0])
        for wrong in (answer[::-1], answer[:1], answer + answer[:1], ['forged']):
            self.assertFalse(grade_answer(q.name, wrong)[0])
        payload = get_quiz_with_questions(quiz.name)['questions_by_name'][q.name]
        self.assertNotIn('interactive_items', payload)
        self.assertNotEqual([i['id'] for i in payload['items']], answer)
        result = submit_quiz(quiz.name, json.dumps([dict(question_name=q.name, answer=answer)]))
        self.assertEqual(result['score'], 2)
        self.assertTrue(result['pass'])
    def test_matching(self):
        q, quiz, items = self.make('Matching')
        answer = [i['id'] + ':' + i['right_id'] for i in items]
        self.assertTrue(grade_answer(q.name, answer[::-1])[0])
        for wrong in (answer[:1], [answer[0], answer[0]], ['forged']):
            self.assertFalse(grade_answer(q.name, wrong)[0])
        self.assertTrue(check_match(quiz.name, q.name, items[0]['id'], items[0]['right_id']))
        self.assertFalse(check_match(quiz.name, q.name, items[0]['id'], items[1]['right_id']))
        with patch('lms.lms.permissions.can_access_quiz', return_value=False):
            with self.assertRaises(frappe.PermissionError):
                check_match(quiz.name, q.name, items[0]['id'], items[0]['right_id'])
        payload = get_quiz_with_questions(quiz.name)['questions_by_name'][q.name]
        self.assertNotIn('interactive_items', payload)
        self.assertTrue(set(i['id'] for i in payload['items']).isdisjoint(i['id'] for i in payload['right_items']))
        result = submit_quiz(quiz.name, json.dumps([dict(question_name=q.name, answer=answer)]))
        self.assertEqual(result['score'], 2)
        stored = frappe.get_doc('LMS Quiz Submission', result['submission'])
        self.assertEqual(stored.result[0].answer, 'A ↔ X; B ↔ Y')
    def test_validation_and_editing(self):
        q, quiz, items = self.make('Ordering')
        q.type = 'Matching'; q.save()
        self.assertEqual(frappe.db.get_value('LMS Quiz Question', {'parent': quiz.name}, 'type'), 'Matching')
        q.interactive_items = json.dumps([dict(text='A', right='X'), dict(text='A', right='Y')])
        with self.assertRaises(frappe.ValidationError): q.save()
    def test_live_check_uses_stored_type(self):
        q, quiz, items = self.make('Ordering')
        self.assertEqual(check_answer(quiz.name, q.name, 'Choices', json.dumps([i['id'] for i in items])), 1)

if __name__ == '__main__':
    try: unittest.main(verbosity=2)
    finally: frappe.db.rollback(); frappe.destroy()
