"""Links to this site's uploaded files inside markdown. No Frappe imports.

Shared by the attachments list and the markdown renderer. File names are written
into links as they are stored, so a name with a space ("Manual de usuario.pdf")
or parentheses ("Manual (v2).pdf") makes a link that CommonMark does not parse:
it would render as plain text. `encode_upload_links` writes such links the way a
browser sends them.
"""

import re
from urllib.parse import quote, unquote

FENCE = re.compile(r"(```|~~~).*?\1", re.S)

# `[text](url)` and `![text](url)` where the url is one of this site's uploads.
# The url may hold spaces and one level of parentheses, and may be wrapped in
# <...> or followed by a "title".
# Every part is bounded: with open-ended `*` and `\s*` a line of 20,000 spaces
# after `[a](/files/` took seconds to scan (it grows with the square of the line).
UPLOAD_LINK = re.compile(
	r"(!?\[[^\]\n]{0,300}\]\(\s{0,5})<?(/(?:private/)?files/(?:[^()\n<>]|\([^()\n]{0,300}\)){0,500}?)>?"
	r'((?:\s{1,5}"[^"\n]{0,300}")?\s{0,5}\))'
)


def normalize_path(href: str) -> str:
	"""An upload's path as a browser sends it: no query or fragment, spaces as %20."""
	return quote(unquote(re.split(r"[?#]", href, maxsplit=1)[0].strip()), safe="/")


def encode_upload_links(markdown: str) -> str:
	"""Write the spaces of upload links as %20, so the link parses; leave fenced code alone."""
	if not markdown or "/files/" not in markdown:
		return markdown

	def fix(match: re.Match) -> str:
		head, url, tail = match.groups()
		# Only the spaces: they are what CommonMark rejects. Parentheses balance on their own.
		return f"{head}{url.replace(' ', '%20')}{tail}" if " " in url else match.group(0)

	parts = re.split(r"((?:```|~~~).*?(?:```|~~~))", markdown, flags=re.S)
	for index in range(0, len(parts), 2):
		parts[index] = UPLOAD_LINK.sub(fix, parts[index])
	return "".join(parts)
