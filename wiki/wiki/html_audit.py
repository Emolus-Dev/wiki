"""Which pages the HTML sanitizer changes. For the deploy that introduced it.

    bench --site <site> execute wiki.wiki.html_audit.run

lists every Wiki Document whose raw HTML loses something (a tag, an attribute, an iframe
from a host the editor does not offer) and says what. Nothing is written. The pure part,
`removed_from`, is tested on strings.
"""

from collections import Counter
from html.parser import HTMLParser

from markdown_it import MarkdownIt

from wiki.wiki.html_sanitizer import sanitize_html


class _Inventory(HTMLParser):
	def __init__(self):
		super().__init__(convert_charrefs=True)
		self.items: Counter = Counter()

	def handle_starttag(self, tag, attrs):
		self.items[f"<{tag}>"] += 1
		for name, _value in attrs:
			self.items[f"<{tag} {name.lower()}>"] += 1

	handle_startendtag = handle_starttag


def _inventory(html: str) -> Counter:
	parser = _Inventory()
	parser.feed(html)
	return parser.items


def removed_from(markdown: str) -> list[str]:
	"""What the sanitizer would take out of the raw HTML in `markdown`, e.g. `<svg>`, `<div onclick>`."""
	if not markdown or "<" not in markdown:
		return []

	lost: Counter = Counter()
	tokens = MarkdownIt("commonmark", {"html": True}).parse(markdown)
	stack = list(tokens)
	while stack:
		token = stack.pop()
		stack.extend(token.children or [])
		if token.type not in ("html_block", "html_inline") or not token.content.strip():
			continue
		before, after = _inventory(token.content), _inventory(sanitize_html(token.content))
		lost.update(before - after)
	return sorted(lost)


def run():
	import frappe

	rows = frappe.get_all(
		"Wiki Document",
		filters={"is_group": 0, "content": ("like", "%<%")},
		fields=["name", "title", "route", "content"],
	)
	changed = 0
	for row in rows:
		lost = removed_from(row.content)
		if lost:
			changed += 1
			print(f"{row.route or row.name}  ({row.title})\n    would lose: {', '.join(lost)}")
	print(f"\n{changed} of {len(rows)} pages with raw HTML would change.")
