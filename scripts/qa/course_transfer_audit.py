"""Run inside bench with its Python; every case rolls back database changes.
Usage: env/bin/python /workspace/lms/scripts/qa/course_transfer_audit.py
Assertions describe desired round-trip integrity; failures are audit findings.
"""
import io
import json
import os
import tempfile
import unittest
import uuid
import zipfile
from unittest.mock import patch

import frappe

os.chdir('/home/frappe/bench-data/frappe-bench/sites')
frappe.init(site='school.localhost')
frappe.connect()
frappe.set_user('Administrator')
frappe.flags.in_test = True
from lms.lms import course_import_export as ce
from lms.lms.api import export_course_as_zip, import_course_from_zip


class CourseTransferAudit(unittest.TestCase):
    def setUp(self):
        self.prefix = 'transfer-audit-' + uuid.uuid4().hex[:10]
        self.paths = []
        frappe.set_user('Administrator')

    def tearDown(self):
        # File writes are outside SQL transactions; remove only newly created files.
        for name in frappe.get_all('File', filters={'file_name': ['like', self.prefix + '%']}, pluck='name'):
            doc = frappe.get_doc('File', name)
            path = doc.get_full_path()
            if os.path.isfile(path):
                os.remove(path)
        frappe.db.rollback()
        frappe.set_user('Administrator')
        for path in self.paths:
            if os.path.isfile(path):
                os.remove(path)

    def doc(self, dt, **values):
        return frappe.get_doc(dict(doctype=dt, **values)).insert(ignore_permissions=True)

    def exercise(self, title=None):
        return self.doc('LMS Programming Exercise', title=title or self.prefix,
                        problem_statement='<p>求和</p>', language='C++',
                        test_cases=[dict(input='1 2', expected_output='3')])

    def course(self, blocks=None, chapters=None, **extra):
        c = self.doc('LMS Course', title=self.prefix, short_introduction='导入导出测试',
                     description='<p>课程正文</p>', instructors=[dict(instructor='Administrator')], **extra)
        chapter_names = []
        for title, lessons in chapters or [('第一章', [('第一课', blocks or [dict(type='paragraph', data=dict(text='中文文本'))])])]:
            ch = self.doc('Course Chapter', course=c.name, title=title)
            for lesson_title, content in lessons:
                le = self.doc('Course Lesson', course=c.name, chapter=ch.name,
                              title=lesson_title, content=json.dumps(dict(blocks=content)))
                ch.append('lessons', dict(lesson=le.name))
            ch.save(ignore_permissions=True)
            chapter_names.append(ch.name)
        c.reload()
        for name in chapter_names:
            c.append('chapters', dict(chapter=name))
        c.save(ignore_permissions=True)
        return c

    def export(self, c):
        # Only suppress the deferred temporary-file deletion job.
        with patch.object(ce, 'schedule_file_deletion'):
            export_course_as_zip(c.name)
        self.assertEqual(frappe.local.response.type, 'download')
        self.paths.append(frappe.get_site_path('private', 'files', frappe.local.response.filename))
        return frappe.local.response.filecontent

    def import_zip(self, raw):
        path = frappe.get_site_path('private', 'files', self.prefix + '-' + uuid.uuid4().hex + '.zip')
        self.paths.append(path)
        with open(path, 'wb') as f:
            f.write(raw)
        return frappe.get_doc('LMS Course', import_course_from_zip('/private/files/' + os.path.basename(path)))

    def edit(self, raw, change):
        out = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(raw)) as src, zipfile.ZipFile(out, 'w') as dst:
            for name in src.namelist():
                value = src.read(name)
                result = change(name, json.loads(value)) if name.endswith('.json') else value
                if result is not None:
                    dst.writestr(name, json.dumps(result) if name.endswith('.json') else result)
        return out.getvalue()

    def lessons(self, c):
        return [frappe.get_doc('Course Lesson', row.lesson)
                for ch in c.chapters for row in frappe.get_doc('Course Chapter', ch.chapter).lessons]

    def program(self, name):
        return [dict(type='program', data=dict(exercise=name))]

    def ref(self, c):
        return json.loads(self.lessons(c)[0].content)['blocks'][0]['data']['exercise']

    def test_01_text_structure_roundtrip(self):
        c = self.course(enforce_lesson_completion=1)
        new = self.import_zip(self.export(c))
        self.assertNotEqual(new.name, c.name)
        self.assertEqual(new.description, c.description)
        self.assertEqual(new.enforce_lesson_completion, 1)
        self.assertEqual(len(new.chapters), 1)
        self.assertEqual(self.lessons(new)[0].content, self.lessons(c)[0].content)

    def test_02_export_contains_manual_statement_and_cases(self):
        e = self.exercise()
        raw = self.export(self.course(self.program(e.name)))
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            a = [n for n in z.namelist() if n.startswith('assessments/lms_programming')]
            self.assertEqual(len(a), 1)
            self.assertEqual(json.loads(z.read(a[0]))['problem_statement'], e.problem_statement)
            self.assertTrue(any(n.startswith('assessments/test_cases/') for n in z.namelist()))

    def test_03_manual_import_into_absent_target(self):
        e = self.exercise()
        raw = self.export(self.course(self.program(e.name)))
        frappe.db.delete('LMS Test Case', {'parent': e.name})
        frappe.db.delete('LMS Programming Exercise', {'name': e.name})
        c = self.import_zip(raw)
        actual = frappe.get_doc('LMS Programming Exercise', self.ref(c))
        self.assertEqual(actual.problem_statement, e.problem_statement)
        self.assertEqual([(x.input, x.expected_output) for x in actual.test_cases], [('1 2', '3')])
        print('MANUAL_IDS', e.name, actual.name, 'DISPLAY_NUMBERS', e.exercise_number, actual.exercise_number)

    def test_04_same_site_import(self):
        e = self.exercise()
        new = self.import_zip(self.export(self.course(self.program(e.name))))
        self.assertEqual(self.ref(new), e.name)

    def test_05_missing_exercise_is_retained(self):
        missing = self.prefix + '-missing'
        c = self.import_zip(self.export(self.course(self.program(missing))))
        self.assertEqual(self.ref(c), missing)
        self.assertFalse(frappe.db.exists('LMS Programming Exercise', missing))

    def test_06_later_new_exercise_does_not_rebind_by_title(self):
        missing = self.prefix + '-missing'
        c = self.import_zip(self.export(self.course(self.program(missing))))
        e = self.exercise(title=missing)
        self.assertNotEqual(e.name, self.ref(c))
        self.assertFalse(frappe.db.exists('LMS Programming Exercise', self.ref(c)))

    def test_07_later_exact_docname_restores_reference(self):
        missing = self.prefix + '-missing'
        c = self.import_zip(self.export(self.course(self.program(missing))))
        e = self.exercise()
        frappe.rename_doc('LMS Programming Exercise', e.name, missing, force=True)
        self.assertTrue(frappe.db.exists('LMS Programming Exercise', self.ref(c)))

    def test_08_repeat_text_import(self):
        raw = self.export(self.course())
        a, b = self.import_zip(raw), self.import_zip(raw)
        self.assertNotEqual(a.name, b.name)
        self.assertEqual(len(self.lessons(b)), 1)

    def test_09_repeated_program_reference(self):
        e = self.exercise()
        c = self.course(chapters=[('C', [('A', self.program(e.name)), ('B', self.program(e.name))])])
        new = self.import_zip(self.export(c))
        self.assertEqual(len(self.lessons(new)), 2)

    def test_10_duplicate_chapter_titles_preserve_structure(self):
        p = [dict(type='paragraph', data=dict(text='text'))]
        c = self.course(chapters=[('Same', [('A', p)]), ('Same', [('B', p)])])
        new = self.import_zip(self.export(c))
        self.assertEqual([len(frappe.get_doc('Course Chapter', ch.chapter).lessons) for ch in new.chapters], [1, 1])

    def test_11_duplicate_lesson_titles_preserve_identity(self):
        a = [dict(type='paragraph', data=dict(text='A'))]
        b = [dict(type='paragraph', data=dict(text='B'))]
        c = self.course(chapters=[('C', [('Same', a), ('Same', b)])])
        new = self.import_zip(self.export(c))
        self.assertEqual(len({le.name for le in self.lessons(new)}), 2)

    def test_12_visibility_flag_roundtrip(self):
        c = self.course(is_public=0)
        self.assertEqual(self.import_zip(self.export(c)).is_public, 0)

    def test_13_instructor_content_exercise_is_exported(self):
        e = self.exercise()
        c = self.course()
        le = self.lessons(c)[0]
        le.instructor_content = json.dumps(dict(blocks=self.program(e.name)))
        le.save(ignore_permissions=True)
        with zipfile.ZipFile(io.BytesIO(self.export(c))) as z:
            self.assertTrue(any(n.startswith('assessments/lms_programming') for n in z.namelist()))

    def test_14_icpc_new_target_roundtrip(self):
        # Real existing ICPC records are read only; synthetic exported ID ensures absent target.
        names = frappe.get_all('LMS Programming Exercise', filters={'source_type': 'icpc'}, pluck='name', limit=1)
        if not names:
            self.skipTest('No ICPC fixture available')
        raw = self.export(self.course(self.program(names[0])))
        synthetic = self.prefix + '-icpc'
        def change(n, d):
            if n.startswith('assessments/lms_programming'):
                d['name'] = synthetic
            if n.startswith('lessons/'):
                content = json.loads(d['content'])
                content['blocks'][0]['data']['exercise'] = synthetic
                d['content'] = json.dumps(content)
            return d
        self.import_zip(self.edit(raw, change))

    def test_15_invalid_zip_rejected(self):
        with self.assertRaises(frappe.ValidationError):
            self.import_zip(b'not a zip')

    def test_16_missing_course_json_rejected(self):
        with self.assertRaises(frappe.ValidationError):
            self.import_zip(self.edit(self.export(self.course()), lambda n, d: None if n == 'course.json' else d))

    def test_17_guest_import_denied(self):
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):
            import_course_from_zip('/private/files/nonexistent.zip')

    def test_18_guest_export_denied(self):
        c = self.course()
        frappe.set_user('Guest')
        with self.assertRaises(frappe.PermissionError):
            export_course_as_zip(c.name)

    def test_19_same_title_exercise_mapping(self):
        old = self.exercise()
        new = self.exercise(title=old.title)
        c = self.import_zip(self.export(self.course(self.program(old.name))))
        self.assertEqual(self.ref(c), old.name)

    def test_20_empty_program_block(self):
        raw = self.export(self.course())
        def change(n, d):
            if n.startswith('lessons/'):
                d['content'] = json.dumps(dict(blocks=[dict(type='program', data={})]))
            return d
        with self.assertRaises(frappe.ValidationError):
            self.import_zip(self.edit(raw, change))


    def test_21_manual_reimport_new_target(self):
        e = self.exercise()
        raw = self.export(self.course(self.program(e.name)))
        frappe.db.delete('LMS Test Case', {'parent': e.name})
        frappe.db.delete('LMS Programming Exercise', {'name': e.name})
        a = self.import_zip(raw)
        b = self.import_zip(raw)
        self.assertEqual(self.ref(a), self.ref(b), 'Repeated imports should reuse the imported exercise')
        self.assertEqual(frappe.db.count('LMS Programming Exercise', {'title': e.title}), 1)

    def test_22_quiz_roundtrip_preserves_marks(self):
        q = self.doc('LMS Question', question=self.prefix + '?', type='Choices',
                     option_1='Yes', is_correct_1=1, option_2='No')
        quiz = self.doc('LMS Quiz', title=self.prefix, passing_percentage=70,
                        questions=[dict(question=q.name, marks=5)])
        c = self.course([dict(type='quiz', data=dict(quiz=quiz.name))])
        raw = self.export(c)
        frappe.db.delete('LMS Quiz Question', {'parent': quiz.name})
        frappe.db.delete('LMS Quiz', {'name': quiz.name})
        frappe.db.delete('LMS Question', {'name': q.name})
        new = self.import_zip(raw)
        ref = json.loads(self.lessons(new)[0].content)['blocks'][0]['data']['quiz']
        actual = frappe.get_doc('LMS Quiz', ref)
        self.assertEqual(actual.questions[0].marks, 5)
        self.assertEqual(actual.passing_percentage, 70)

    def test_23_assignment_roundtrip(self):
        a = self.doc('LMS Assignment', title=self.prefix, question='Explain', type='Text', grade_assignment=1)
        raw = self.export(self.course([dict(type='assignment', data=dict(assignment=a.name))]))
        frappe.db.delete('LMS Assignment', {'name': a.name})
        c = self.import_zip(raw)
        ref = json.loads(self.lessons(c)[0].content)['blocks'][0]['data']['assignment']
        self.assertEqual(frappe.get_doc('LMS Assignment', ref).question, a.question)

    def test_24_private_attachment_roundtrip(self):
        f = self.doc('File', file_name=self.prefix + '.txt', content=b'audit attachment', is_private=1)
        raw = self.export(self.course([dict(type='upload', data=dict(file_url=f.file_url, file_type='text/plain'))]))
        old_url = f.file_url
        os.remove(f.get_full_path())
        frappe.db.delete('File', {'name': f.name})
        c = self.import_zip(raw)
        url = json.loads(self.lessons(c)[0].content)['blocks'][0]['data']['file_url']
        imported = frappe.db.get_value('File', {'file_url': url}, ['name', 'is_private'], as_dict=True)
        self.assertTrue(imported, f'Imported lesson still references {old_url}, but no File exists there')
        self.assertEqual(imported.is_private, 1)

    def test_25_missing_quiz_rejected(self):
        raw = self.export(self.course())
        def change(n, d):
            if n.startswith('lessons/'):
                d['content'] = json.dumps(dict(blocks=[dict(type='quiz', data=dict(quiz=self.prefix))]))
                d['lesson_type'] = 'Quiz'
            return d
        with self.assertRaises(frappe.ValidationError):
            self.import_zip(self.edit(raw, change))

    def test_26_external_video_roundtrip(self):
        blocks = [dict(type='embed', data=dict(service='youtube', source='https://www.youtube.com/watch?v=abc', embed='https://www.youtube.com/embed/abc'))]
        c = self.course(blocks)
        self.assertEqual(self.lessons(self.import_zip(self.export(c)))[0].content, self.lessons(c)[0].content)

    def test_27_empty_course_roundtrip(self):
        c = self.doc('LMS Course', title=self.prefix, short_introduction='empty', description='empty',
                     instructors=[dict(instructor='Administrator')])
        new = self.import_zip(self.export(c))
        self.assertEqual(len(new.chapters), 0)


if __name__ == '__main__':
    from lms.lms.test_course_import_export import TestImportExportContentGuards
    suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(TestImportExportContentGuards),
                                unittest.defaultTestLoader.loadTestsFromTestCase(CourseTransferAudit)])
    try:
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    finally:
        frappe.db.rollback()
        frappe.destroy()
    raise SystemExit(not result.wasSuccessful())
