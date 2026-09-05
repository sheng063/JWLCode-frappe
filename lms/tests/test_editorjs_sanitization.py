import json
import unittest

from frappe.utils.html_utils import sanitize_html
from lms.lms.utils import sanitize_editorjs


class TestEditorJsonSanitization(unittest.TestCase):
	def test_rich_content_survives_the_second_html_filter(self):
		markup = (
			'<p>公式与图片</p><img src="/files/lesson.png" alt="示例">'
			'<math><mfrac><mn>10</mn><mn>2</mn></mfrac><mo>=</mo><mn>5</mn></math>'
		)
		raw = json.dumps({"blocks": [{"type": "markdown", "data": {"text": markup}}]})
		stored = sanitize_html(sanitize_editorjs(raw))
		text = json.loads(stored)["blocks"][0]["data"]["text"]
		self.assertIn('src="/files/lesson.png"', text)
		self.assertIn("<mfrac>", text)
		self.assertIn("公式与图片", text)
		self.assertEqual(sanitize_editorjs(stored), stored)

	def test_escaping_does_not_bypass_html_sanitization(self):
		raw = json.dumps({"blocks": [{"type": "markdown", "data": {
			"text": '<img src="/files/lesson.png" onerror="alert(1)"><script>alert(2)</script>'
		}}]})
		stored = sanitize_html(sanitize_editorjs(raw))
		text = json.loads(stored)["blocks"][0]["data"]["text"]
		self.assertNotIn("onerror", text)
		self.assertNotIn("<script", text)
		self.assertIn('src="/files/lesson.png"', text)
