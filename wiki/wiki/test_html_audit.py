import unittest

from wiki.wiki.html_audit import removed_from


class TestRemovedFrom(unittest.TestCase):
	def test_clean_pages_lose_nothing(self):
		self.assertEqual(removed_from("# Title\n\nPlain text and `code`."), [])
		self.assertEqual(
			removed_from('<details><summary>x</summary>y</details>\n\n<span style="color: red;">c</span>'), []
		)

	def test_reports_what_is_taken_out(self):
		lost = removed_from('<div onclick="x()" id="a">hi</div>\n\n<svg><path/></svg>')
		self.assertIn("<div onclick>", lost)
		self.assertIn("<div id>", lost)
		self.assertIn("<svg>", lost)

	def test_an_embed_from_an_unknown_host_is_reported(self):
		self.assertIn("<iframe>", removed_from('<iframe src="https://example.com/x"></iframe>'))
		self.assertNotIn("<iframe>", removed_from('<iframe src="https://www.youtube.com/embed/a"></iframe>'))

	def test_html_inside_a_code_fence_is_not_html(self):
		self.assertEqual(removed_from("```html\n<script>alert(1)</script>\n```"), [])
