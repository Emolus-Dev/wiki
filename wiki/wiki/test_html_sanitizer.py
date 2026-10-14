import re
import unittest
from pathlib import Path

from wiki.wiki.html_sanitizer import IFRAME_HOSTS, clean_style, is_safe_url, sanitize_html
from wiki.wiki.markdown import render_markdown

ROOT = Path(__file__).resolve().parents[2]


class TestRawHtmlIsSanitized(unittest.TestCase):
	"""What a page author writes is served to every visitor, signed in or not."""

	def render(self, markdown: str) -> str:
		return render_markdown(markdown)

	def assertInert(self, html: str):
		lowered = html.lower()
		for needle in (
			"<script",
			"onerror",
			"onload",
			"onclick",
			"onmouseover",
			"javascript:",
			"<form",
			"<meta",
			"<style",
		):
			self.assertNotIn(needle, lowered, html)

	def test_scripts_and_event_handlers_are_removed(self):
		for source in (
			"<script>alert(1)</script>",
			"<img src=x onerror=alert(1)>",
			'<div onmouseover="alert(1)">x</div>',
			"<svg onload=alert(1)><circle/></svg>",
			"<style>body{display:none}</style>",
			'<meta http-equiv="refresh" content="0;url=https://evil.example">',
			'<form action="https://evil.example"><input type="password"></form>',
			"text <b onclick=alert(1)>bold</b> text",
		):
			self.assertInert(self.render(source))

	def test_dangerous_urls_are_removed(self):
		for source in (
			'<a href="javascript:alert(1)">x</a>',
			'<a href="  java\tscript:alert(1)">x</a>',
			'<a href="&#106;avascript:alert(1)">x</a>',
			'<a href="data:text/html;base64,PHNjcmlwdD4=">x</a>',
			'<a href="vbscript:msgbox(1)">x</a>',
			'<img src="data:text/html;base64,PHNjcmlwdD4=">',
			"[x](javascript:alert(1))",
		):
			html = self.render(source)
			# Literal text such as `[x](javascript:...)` is harmless; a live url is not.
			self.assertNotRegex(
				html, r"(?i)(?:href|src)\s*=\s*[\"']?\s*(?:javascript|vbscript|data:text)", html
			)

	def test_alpine_directives_cannot_reach_the_page(self):
		# The reader runs Alpine over the page text: these attributes would execute.
		html = self.render('<div x-init="alert(1)" @click="steal()" :class="y" x-html="z">a</div>')
		for needle in ("x-init", "@click", ":class", "x-html"):
			self.assertNotIn(needle, html)

	def test_an_iframe_survives_only_for_a_known_embed_host_over_https(self):
		ok = self.render('<iframe src="https://www.youtube.com/embed/abc" width="560" height="315"></iframe>')
		self.assertIn('src="https://www.youtube.com/embed/abc"', ok)
		self.assertIn("referrerpolicy=", ok)

		for bad in (
			'<iframe src="https://evil.example/x"></iframe>',
			'<iframe src="http://www.youtube.com/embed/abc"></iframe>',
			'<iframe src="javascript:alert(1)"></iframe>',
			'<iframe src="https://youtube.com.evil.example/x"></iframe>',
			'<iframe srcdoc="<script>alert(1)</script>"></iframe>',
		):
			self.assertNotIn("<iframe", self.render(bad), bad)

	def test_an_iframe_cannot_gain_permissions(self):
		html = self.render(
			'<iframe src="https://www.youtube.com/embed/a" allow="autoplay; camera; microphone; geolocation"></iframe>'
		)
		self.assertIn('allow="autoplay"', html)
		self.assertNotIn("camera", html)

	def test_a_style_cannot_position_or_load_anything(self):
		html = self.render(
			'<div style="position:fixed;top:0;left:0;z-index:9999;background:url(https://evil.example/x)">fake login</div>'
		)
		for needle in ("position", "z-index", "url(", "top:", "left:"):
			self.assertNotIn(needle, html)

	def test_positioning_classes_are_removed_and_plain_ones_kept(self):
		html = self.render('<div class="note fixed inset-0 z-50">x</div>')
		self.assertIn('class="note"', html)

	def test_formatting_authors_rely_on_still_works(self):
		self.assertIn(
			'<span style="color: red;">c</span>', self.render('Text <span style="color: red;">c</span>')
		)
		self.assertIn(
			"<details open><summary>More</summary>",
			self.render("<details open><summary>More</summary>x</details>"),
		)
		self.assertIn('<td colspan="2">', self.render('<table><tr><td colspan="2">a</td></tr></table>'))
		self.assertIn(
			'<a href="https://example.com">x</a>', self.render('<a href="https://example.com">x</a>')
		)

	def test_external_links_opened_in_a_new_tab_cannot_reach_back(self):
		self.assertIn(
			'rel="noopener noreferrer"', self.render('<a href="https://example.com" target="_blank">x</a>')
		)

	def test_text_is_escaped_not_dropped(self):
		self.assertIn("a &lt; b", self.render("a < b"))
		self.assertIn("&amp;", sanitize_html("<p>a &amp; b</p>"))


class TestGeneratedHtmlEscapesAuthorText(unittest.TestCase):
	def test_callout_and_details_titles_are_text(self):
		for kind in ("note", "details"):
			html = render_markdown(f":::{kind}[<img src=x onerror=alert(1)>]\nbody\n:::")
			self.assertNotIn("<img", html)
			self.assertIn("&lt;img", html)

	def test_a_quote_in_an_alt_or_name_cannot_open_a_new_attribute(self):
		for source in (
			'![a" onmouseover="alert(1)](/files/a.mp4)',
			'![x" onmouseover="alert(1).pdf](/files/a.pdf)',
			'![a" onerror="alert(1)](/files/a.png)',
			'![a](/files/a.png "t\\" onmouseover=\\"alert(1)")',
		):
			html = render_markdown(source)
			self.assertNotRegex(html, r'"\s+on\w+=', html)

	def test_the_picture_block_the_editor_writes_is_escaped_once(self):
		html = render_markdown(
			'<picture><img src="/files/a.png" alt="Tom &amp; Jerry &quot;x&quot;" /></picture>'
		)
		self.assertIn('alt="Tom &amp; Jerry &quot;x&quot;"', html)


class TestUrlAndStyleHelpers(unittest.TestCase):
	def test_safe_urls(self):
		for url in (
			"https://a.b/c",
			"http://a.b",
			"/files/a.pdf",
			"relative/x",
			"#top",
			"mailto:a@b.c",
			"tel:+123",
		):
			self.assertTrue(is_safe_url(url), url)
		for url in ("javascript:alert(1)", "JaVaScRiPt:alert(1)", "data:text/html,x", "vbscript:x", "", " "):
			self.assertFalse(is_safe_url(url), url)

	def test_data_uri_only_for_images(self):
		self.assertTrue(is_safe_url("data:image/png;base64,AAAA", image=True))
		self.assertFalse(is_safe_url("data:image/svg+xml;base64,AAAA", image=True))
		self.assertFalse(is_safe_url("data:image/png;base64,AAAA"))

	def test_style_keeps_formatting_and_drops_the_rest(self):
		self.assertEqual(
			clean_style("color: red; position: fixed; margin: 0 auto"), "color: red; margin: 0 auto;"
		)
		self.assertEqual(clean_style("background: url(x)"), "")
		self.assertEqual(clean_style("color: rgb(1, 2, 3)"), "color: rgb(1, 2, 3);")
		self.assertEqual(clean_style("width: calc(100% - 1px)"), "")
		self.assertEqual(clean_style("display: flex"), "")


class TestIframeHostsMatchTheEditor(unittest.TestCase):
	def test_server_and_editor_allow_the_same_embed_hosts(self):
		source = (ROOT / "frontend/src/components/tiptap-extensions/iframe-embed.js").read_text()
		block = source[source.index("IFRAME_PROVIDERS") : source.index("function hostOf")]
		editor_hosts = set(re.findall(r"'([a-z0-9.-]+\.[a-z]{2,})'", block))
		self.assertEqual(editor_hosts, set(IFRAME_HOSTS))


class TestRenderingCannotBeTiedUp(unittest.TestCase):
	"""A page is public; hostile content must not cost a worker minutes."""

	def timed(self, markdown: str) -> float:
		import time

		start = time.perf_counter()
		render_markdown(markdown)
		return time.perf_counter() - start

	def test_long_runs_after_a_link_head_render_quickly(self):
		for source in ("[a](/files/" + " " * 50000, "![a](/files/x.png" + " " * 50000, "![a](" + "(" * 50000):
			self.assertLess(self.timed(source), 1.0)

	def test_thousands_of_unclosed_fences_render_quickly(self):
		for source in (":::note\n" * 20000, ":::code-group\n" * 20000):
			self.assertLess(self.timed(source), 2.0)

	def test_ordinary_callouts_still_render(self):
		html = render_markdown(":::note\nhi\n:::\n\n:::tip\nyo\n:::")
		self.assertIn("callout-note", html)
		self.assertIn("callout-tip", html)


class TestEmbedUrlsMustBeSafe(unittest.TestCase):
	def test_a_script_url_with_a_media_extension_is_not_embedded(self):
		for source in (
			"![x.pdf](javascript:alert(1)//.pdf)",
			"![v](javascript:alert(1)//.mp4)",
			"![x](vbscript:a.pdf)",
		):
			html = render_markdown(source)
			self.assertNotRegex(html, r"(?i)(?:href|src)=\"(?:javascript|vbscript)", html)

	def test_normal_embeds_still_render(self):
		self.assertIn("wiki-pdf-embed", render_markdown("![guide.pdf](/files/guide.pdf)"))
		self.assertIn("<video", render_markdown("![clip](/files/clip.mp4)"))
