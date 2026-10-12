from wiki.tests import WikiTestCase as FrappeTestCase
from wiki.wiki.attachments import extract_attachments, format_file_size


class TestExtractAttachments(FrappeTestCase):
	def test_lists_links_to_uploaded_files_in_order(self):
		md = "See [the manual](/files/manual.pdf) and [data](/files/data%20set.json)."

		self.assertEqual(
			[(a["name"], a["filename"], a["extension"]) for a in extract_attachments(md)],
			[("the manual", "manual.pdf", "pdf"), ("data", "data set.json", "json")],
		)

	def test_pdf_embeds_count_but_images_and_video_do_not(self):
		md = "![guide.pdf](/files/guide.pdf)\n![shot](/files/shot.png)\n![clip](/files/clip.mp4)"

		self.assertEqual([a["filename"] for a in extract_attachments(md)], ["guide.pdf"])

	def test_ignores_external_links_and_code_fences(self):
		md = "[site](https://example.com/files/a.pdf)\n```\n[x](/files/inside.zip)\n```\n[ok](/files/ok.zip)"

		self.assertEqual([a["filename"] for a in extract_attachments(md)], ["ok.zip"])

	def test_the_same_file_is_listed_once_and_private_files_are_kept(self):
		md = "[a](/files/a.zip) [again](/files/a.zip) [p](/private/files/p.xlsx)"

		self.assertEqual(
			[a["url"] for a in extract_attachments(md)], ["/files/a.zip", "/private/files/p.xlsx"]
		)

	def test_a_link_without_text_falls_back_to_the_file_name(self):
		self.assertEqual(extract_attachments("[](/files/notes.txt)")[0]["name"], "notes.txt")

	def test_each_type_gets_a_chip_colour_and_unknown_types_are_gray(self):
		md = "[a](/files/a.pdf) [b](/files/b.xlsx) [c](/files/c.json) [d](/files/d.zip)"

		self.assertEqual([a["kind"] for a in extract_attachments(md)], ["red", "green", "gray", "amber"])

	def test_file_sizes_are_human_readable(self):
		self.assertEqual(format_file_size(0), "")
		self.assertEqual(format_file_size(512), "512 B")
		self.assertEqual(format_file_size(1536), "1.5 KB")
		self.assertEqual(format_file_size(250 * 1024), "250 KB")
		self.assertEqual(format_file_size(5 * 1024 * 1024), "5.0 MB")
