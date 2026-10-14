import unittest

from wiki.upload_guard import extension_of, upload_problem


class TestUploadGuard(unittest.TestCase):
	def test_pages_and_scripts_are_refused(self):
		for name in ("a.html", "A.HTM", "x.xhtml", "evil.js", "m.mjs", "d.xml", "t.xsl", "p.hta", "x.shtml"):
			self.assertIsNotNone(upload_problem(name, b""), name)

	def test_documents_and_images_are_accepted(self):
		for name in (
			"manual.pdf",
			"shot.png",
			"photo.jpeg",
			"data.xlsx",
			"notes.txt",
			"a.zip",
			"clip.mp4",
			"noext",
			"",
		):
			self.assertIsNone(upload_problem(name, b"%PDF-1.4"), name)

	def test_a_plain_svg_is_accepted(self):
		svg = b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0h10v10z"/></svg>'
		self.assertIsNone(upload_problem("logo.svg", svg))

	def test_an_svg_with_script_is_refused(self):
		for body in (
			b"<svg><script>alert(1)</script></svg>",
			b'<svg onload="alert(1)"></svg>',
			b'<svg><a xlink:href="javascript:alert(1)"><text>x</text></a></svg>',
			b"<svg><foreignObject><iframe src=x></iframe></foreignObject></svg>",
			b"<svg><SCRIPT >x</SCRIPT></svg>",
		):
			self.assertIsNotNone(upload_problem("x.svg", body), body)

	def test_only_the_last_extension_counts(self):
		self.assertEqual(extension_of("archive.tar.gz"), "gz")
		self.assertIsNotNone(upload_problem("report.pdf.html", b""))
		self.assertIsNone(upload_problem("page.html.pdf", b""))
