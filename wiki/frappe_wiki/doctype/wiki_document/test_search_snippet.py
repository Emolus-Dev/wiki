from wiki.frappe_wiki.doctype.wiki_document.search import (
	_clean_snippet,
	_merge_token_hits,
	_query_tokens,
	_widen_hits,
	_word_variants,
)
from wiki.frappe_wiki.doctype.wiki_document.wiki_sqlite_search import WikiSQLiteSearch
from wiki.tests import WikiTestCase as IntegrationTestCase


class TestSearchSnippet(IntegrationTestCase):
	def test_clean_snippet_drops_markdown_and_keeps_the_highlight(self):
		raw = "<mark>Git</mark> - Guía Completa ok --- ## Configuración Inicial ### Guardar credenciales"
		cleaned = _clean_snippet(raw)

		self.assertIn("<mark>Git</mark>", cleaned)
		self.assertNotIn("#", cleaned)
		self.assertNotIn("---", cleaned)
		self.assertIn("Configuración Inicial", cleaned)
		self.assertIn("Guardar credenciales", cleaned)

	def test_strip_markdown_cleans_text_the_indexer_already_flattened(self):
		flat = "Git guía --- ## Configuración ### Identidad global"
		plain = WikiSQLiteSearch()._strip_markdown(flat)

		self.assertNotIn("#", plain)
		self.assertNotIn("---", plain)
		self.assertIn("Configuración", plain)
		self.assertIn("Identidad global", plain)

	def test_page_text_cannot_become_markup_next_to_a_match(self):
		# FTS wraps the match in <mark>; a half-written tag before it must stay text.
		snippet = _clean_snippet("Intro <img src=x onerror=alert(1) <mark>match</mark> and more")

		self.assertNotIn("<img", snippet)
		self.assertIn("&lt;img", snippet)
		self.assertIn("<mark>match</mark>", snippet)

	def test_quotes_and_ampersands_in_page_text_are_escaped(self):
		self.assertEqual(_clean_snippet('a "b" & <mark>c</mark>'), "a &quot;b&quot; &amp; <mark>c</mark>")

	def test_query_tokens_drop_short_and_repeated_words_and_cap_the_count(self):
		self.assertEqual(_query_tokens("a git Git  config"), ["git", "config"])
		self.assertEqual(len(_query_tokens("aa bb cc dd ee ff gg")), 5)

	def test_a_word_is_also_searched_by_its_stem(self):
		self.assertEqual(_word_variants("configuración"), ["configuración", "configur"])
		self.assertEqual(_word_variants("git"), ["git"])
		self.assertEqual(_word_variants("deploy"), ["deploy"])

	def test_a_single_word_with_a_stem_is_widened(self):
		class Engine:
			def __init__(self):
				self.asked = []

			def search(self, query, filters=None):
				self.asked.append(query)
				return {"results": [{"name": "page"}] if query == "configur" else []}

		engine = Engine()
		hits = _widen_hits(engine, "configuración", {}, [])

		self.assertEqual(engine.asked, ["configuración", "configur"])
		self.assertEqual([hit["name"] for hit in hits], ["page"])

	def test_a_good_first_pass_is_left_alone(self):
		class Engine:
			def search(self, *args, **kwargs):
				raise AssertionError("must not search again")

		first = [{"name": str(i)} for i in range(5)]
		self.assertIs(_widen_hits(Engine(), "configuración", {}, first), first)

	def test_merge_ranks_pages_matching_more_words_first(self):
		page = lambda name: {"name": name}  # noqa: E731
		full = [page("both")]
		per_token = [[page("only-git"), page("both")], [page("only-config"), page("both"), page("also-git")]]

		merged = _merge_token_hits(full, per_token)

		self.assertEqual([hit["name"] for hit in merged], ["both", "only-git", "only-config", "also-git"])

	def test_merge_adds_pages_the_whole_query_missed(self):
		page = lambda name: {"name": name}  # noqa: E731

		merged = _merge_token_hits([], [[page("a")], [page("b")]])

		self.assertEqual([hit["name"] for hit in merged], ["a", "b"])
