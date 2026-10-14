"""Which uploads the wiki editor refuses. No Frappe imports.

A file under /files is served from the site's own origin, so one that a browser
will run (an HTML page, a script, an SVG with a script in it) is stored XSS for
whoever opens its link, an administrator included. Images, PDFs, archives and
office documents are not affected.
"""

import re

# Opened directly, a browser runs these.
ACTIVE_EXTENSIONS = frozenset(
	{"html", "htm", "xhtml", "xht", "shtml", "js", "mjs", "xml", "xsl", "xslt", "swf", "hta"}
)

_SVG_SCRIPT = re.compile(
	rb"<\s*script|<\s*foreignObject|<\s*iframe|<\s*embed|<\s*object|\son[a-z]+\s*=|javascript\s*:|data\s*:\s*text/html",
	re.I,
)


def extension_of(filename: str | None) -> str:
	name = (filename or "").strip().lower()
	return name.rsplit(".", 1)[-1] if "." in name else ""


def upload_problem(filename: str | None, head: bytes) -> str | None:
	"""Why this upload is refused, or None. `head` is the start of the file (up to 2 MB is read)."""
	extension = extension_of(filename)
	if extension in ACTIVE_EXTENSIONS:
		return f".{extension} files can run in the browser and are not accepted"
	if extension in ("svg", "svgz") and _SVG_SCRIPT.search(head or b""):
		return "This SVG contains script and is not accepted"
	return None
