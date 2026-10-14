import unittest

from wiki.wiki.markdown import render_markdown
from wiki.wiki.upload_links import encode_upload_links


class TestEncodeUploadLinks(unittest.TestCase):
	def test_spaces_become_percent_20(self):
		self.assertEqual(
			encode_upload_links("[Manual de usuario.pdf](/files/Manual de usuario.pdf)"),
			"[Manual de usuario.pdf](/files/Manual%20de%20usuario.pdf)",
		)

	def test_a_title_and_angle_brackets_survive(self):
		self.assertEqual(
			encode_upload_links('[a](/files/my file.zip "get it")'),
			'[a](/files/my%20file.zip "get it")',
		)

	def test_links_that_already_parse_are_untouched(self):
		md = "[a](/files/a.zip) and [b](https://example.com/x y)"
		self.assertEqual(encode_upload_links(md), md)

	def test_fenced_code_is_left_alone(self):
		md = "```\n[a](/files/my file.zip)\n```\n\n[b](/files/my file.zip)"
		self.assertEqual(
			encode_upload_links(md), "```\n[a](/files/my file.zip)\n```\n\n[b](/files/my%20file.zip)"
		)


class TestSpacedUploadLinksRender(unittest.TestCase):
	def test_a_file_with_a_space_in_its_name_renders_as_a_link(self):
		html = render_markdown("Descarga el [manual](/files/Manual de usuario.pdf) aquí.")

		self.assertIn('<a href="/files/Manual%20de%20usuario.pdf"', html)
		self.assertNotIn("](", html)
