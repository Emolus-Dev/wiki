"""Allow-list sanitizer for the raw HTML an author writes inside markdown.

Published pages are public, and the markdown renderer lets authors write HTML
(a `<details>`, a table with spans, an embedded video). Whatever an author
writes is served to every visitor on the site's own origin, so a `<script>`, an
`onerror=` or a `javascript:` link in a merged page would run as the visitor,
an administrator included. This keeps the HTML that documentation needs and drops
the rest. No Frappe imports: it is tested on plain strings.

What it does:
- unknown tags are dropped and their text is kept, escaped; `script`, `style` and
  similar are dropped with their content;
- only allow-listed attributes survive, and urls must be http(s), mailto, tel,
  relative or an image `data:` uri;
- an `<iframe>` survives only for the embed providers the editor offers, over https;
- `id`, `name`, `on*` and every attribute not listed are dropped, which also removes
  Alpine's `x-*`, `@click` and `:bind`: the reader runs Alpine over the page text, so
  those would otherwise execute;
- `style` keeps simple text and box properties only (no positioning, no `url()`), and
  `class` keeps ordinary names but not the utilities that position or stack an element:
  either could lay a fake login over the page.
"""

import re
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit

# Keep in step with IFRAME_PROVIDERS in
# frontend/src/components/tiptap-extensions/iframe-embed.js (a test checks it).
IFRAME_HOSTS = (
	"youtube.com",
	"youtube-nocookie.com",
	"youtu.be",
	"vimeo.com",
	"player.vimeo.com",
	"loom.com",
	"codepen.io",
	"codesandbox.io",
	"figma.com",
	"framer.com",
	"miro.com",
	"docs.google.com",
	"drive.google.com",
	"cloudflarestream.com",
	"videodelivery.net",
	"mediadelivery.net",
	"bunnycdn.com",
	"aparat.com",
	"gist.github.com",
)

ALLOWED_TAGS = frozenset(
	"""a abbr b blockquote br caption cite code col colgroup dd del details div dl dt em
	figcaption figure h1 h2 h3 h4 h5 h6 hr i img input ins kbd label li mark ol p picture pre
	q s samp small source span strong sub summary sup table tbody td tfoot th thead tr u ul
	video audio iframe""".split()
)

# Dropped together with everything inside them.
DROP_WITH_CONTENT = frozenset(
	"script style object embed noscript template textarea title head svg math".split()
)

VOID_TAGS = frozenset("br col hr img input source".split())

GLOBAL_ATTRS = frozenset({"title", "lang", "dir", "align", "style"})
TAG_ATTRS = {
	"a": {"href", "target", "rel", "hreflang"},
	"img": {"src", "alt", "width", "height", "loading", "data-align"},
	"source": {"src", "srcset", "type", "media", "data-dark-source"},
	"picture": set(),
	"td": {"colspan", "rowspan", "headers"},
	"th": {"colspan", "rowspan", "headers", "scope"},
	"col": {"span"},
	"colgroup": {"span"},
	"ol": {"start", "type", "reversed"},
	"li": {"value"},
	"details": {"open"},
	"video": {"src", "controls", "poster", "preload", "loop", "muted", "width", "height", "playsinline"},
	"audio": {"src", "controls", "preload", "loop", "muted"},
	"input": {"type", "checked", "disabled"},
	"label": {"for"},
	"iframe": {"src", "width", "height", "allow", "allowfullscreen", "loading", "frameborder"},
	"p": {"data-align"},
	"div": {"data-align"},
}

URL_ATTRS = frozenset({"href", "src", "poster", "srcset"})
SAFE_SCHEMES = frozenset({"http", "https", "mailto", "tel"})
IMAGE_DATA_URI = re.compile(r"^data:image/(?:png|jpe?g|gif|webp|avif);base64,[A-Za-z0-9+/=]+$")
# A class is an ordinary name unless it positions or stacks the element.
_CLASS_NAME = re.compile(r"^[A-Za-z_][\w-]{0,40}$")
_POSITIONING_CLASS = re.compile(
	r"^(?:fixed|absolute|sticky|inset|top|right|bottom|left|z|translate|transform|float|overlay)(?:-.*)?$"
)

# Properties a page author reasonably sets on a paragraph, cell or box.
ALLOWED_CSS = frozenset(
	"""color background background-color font-size font-weight font-style font-family
	line-height letter-spacing text-align text-decoration text-transform text-indent
	white-space word-break vertical-align margin margin-top margin-right margin-bottom
	margin-left padding padding-top padding-right padding-bottom padding-left width
	max-width min-width height max-height min-height border border-top border-right
	border-bottom border-left border-radius border-color border-style border-width
	border-collapse border-spacing display opacity list-style-type""".split()
)
_CSS_FUNCTION = re.compile(r"([A-Za-z-]+)\(")
_CSS_FUNCTIONS_OK = frozenset({"rgb", "rgba", "hsl", "hsla"})
_CSS_VALUE = re.compile(r"^[\w\s#%.,()/+-]{1,80}$")
_CSS_DISPLAY_OK = frozenset({"none", "block", "inline", "inline-block", "table", "list-item"})
SAFE_ALLOW_FEATURES = frozenset(
	{
		"accelerometer",
		"autoplay",
		"clipboard-write",
		"encrypted-media",
		"fullscreen",
		"gyroscope",
		"picture-in-picture",
		"web-share",
	}
)
_NUMBER = re.compile(r"^\d{1,5}(?:px|%)?$")
_CONTROL_CHARS = re.compile(r"[\x00-\x20\x7f-\x9f​-‏  ﻿]+")


def is_safe_url(value: str, *, image: bool = False) -> bool:
	"""http(s), mailto, tel, a relative path or `#anchor`; `data:` only for an image src."""
	stripped = _CONTROL_CHARS.sub("", value or "")
	if not stripped:
		return False
	if image and IMAGE_DATA_URI.match(stripped):
		return True
	try:
		parts = urlsplit(stripped)
	except ValueError:
		return False
	if parts.scheme:
		return parts.scheme.lower() in SAFE_SCHEMES
	# `//host/path` is protocol-relative: fine for a link, but resolve it as https below.
	return True


def is_allowed_iframe_src(value: str) -> bool:
	try:
		parts = urlsplit((value or "").strip())
	except ValueError:
		return False
	host = (parts.hostname or "").lower()
	if parts.scheme != "https" or not host:
		return False
	return any(host == allowed or host.endswith("." + allowed) for allowed in IFRAME_HOSTS)


def clean_style(value: str) -> str:
	"""The declarations of a `style` attribute that are plain text and box formatting."""
	kept = []
	for declaration in (value or "").split(";"):
		prop, _, val = declaration.partition(":")
		prop, val = prop.strip().lower(), val.strip()
		if prop not in ALLOWED_CSS or not _CSS_VALUE.match(val) or "\\" in val:
			continue
		lowered = val.lower()
		if "url" in lowered or "expression" in lowered or "javascript" in lowered or "var(" in lowered:
			continue
		if any(name.lower() not in _CSS_FUNCTIONS_OK for name in _CSS_FUNCTION.findall(val)):
			continue
		if prop == "display" and lowered not in _CSS_DISPLAY_OK:
			continue
		kept.append(f"{prop}: {val};")
	return " ".join(kept)


def _clean_attrs(tag: str, attrs: list[tuple[str, str | None]]) -> str | None:
	"""The attribute string for `tag`, or None when the tag must not be kept at all."""
	allowed = GLOBAL_ATTRS | TAG_ATTRS.get(tag, set())
	out: list[str] = []
	values = {name.lower(): (value if value is not None else "") for name, value in attrs}

	if tag == "iframe":
		if not is_allowed_iframe_src(values.get("src", "")):
			return None
	if tag == "input" and values.get("type", "").lower() != "checkbox":
		return None

	for name, value in attrs:
		name = name.lower()
		value = value if value is not None else ""
		if name == "class":
			tokens = [t for t in value.split() if _CLASS_NAME.match(t) and not _POSITIONING_CLASS.match(t)]
			if tokens:
				out.append(f'class="{escape(" ".join(tokens), quote=True)}"')
			continue
		if name == "style":
			cleaned_style = clean_style(value)
			if cleaned_style:
				out.append(f'style="{escape(cleaned_style, quote=True)}"')
			continue
		if name not in allowed or name.startswith("on"):
			continue
		if name in URL_ATTRS:
			if name == "srcset":
				if not all(
					is_safe_url(part.strip().split()[0], image=True)
					for part in value.split(",")
					if part.strip()
				):
					continue
			elif not is_safe_url(
				value, image=(tag in ("img", "source", "video") and name in ("src", "poster"))
			):
				continue
		if name in ("width", "height", "colspan", "rowspan", "span", "start", "value") and not _NUMBER.match(
			value.strip()
		):
			continue
		if name == "allow":
			features = [f.strip() for f in value.split(";") if f.strip()]
			value = "; ".join(f for f in features if f in SAFE_ALLOW_FEATURES)
			if not value:
				continue
		if name == "target" and value not in ("_blank", "_self"):
			continue
		if name in (
			"controls",
			"checked",
			"disabled",
			"open",
			"loop",
			"muted",
			"allowfullscreen",
			"playsinline",
			"reversed",
		):
			out.append(name)
			continue
		out.append(f'{name}="{escape(value, quote=True)}"')

	if tag == "a":
		if 'target="_blank"' in out:
			# A page opened this way gets no handle on this one.
			out = [a for a in out if not a.startswith("rel=")] + ['rel="noopener noreferrer"']
	if tag == "iframe":
		out += ['referrerpolicy="strict-origin-when-cross-origin"', 'loading="lazy"']
	return " ".join(out)


class _Sanitizer(HTMLParser):
	def __init__(self):
		super().__init__(convert_charrefs=False)
		self.out: list[str] = []
		self.skip_depth = 0
		self.skip_tag: str | None = None

	# -- tags ---------------------------------------------------------------
	def handle_starttag(self, tag, attrs):
		tag = tag.lower()
		if self.skip_depth:
			if tag == self.skip_tag:
				self.skip_depth += 1
			return
		if tag in DROP_WITH_CONTENT:
			if tag not in VOID_TAGS:
				self.skip_depth, self.skip_tag = 1, tag
			return
		if tag not in ALLOWED_TAGS:
			return
		cleaned = _clean_attrs(tag, attrs)
		if cleaned is None:
			if tag == "iframe":
				# An embed from an unknown host is dropped with whatever was inside it.
				self.skip_depth, self.skip_tag = 1, "iframe"
			return
		self.out.append(f"<{tag}{(' ' + cleaned) if cleaned else ''}>")

	def handle_startendtag(self, tag, attrs):
		tag = tag.lower()
		if self.skip_depth or tag in DROP_WITH_CONTENT or tag not in ALLOWED_TAGS:
			return
		cleaned = _clean_attrs(tag, attrs)
		if cleaned is None:
			return
		self.out.append(
			f"<{tag}{(' ' + cleaned) if cleaned else ''}>"
			if tag in VOID_TAGS
			else f"<{tag}{(' ' + cleaned) if cleaned else ''}></{tag}>"
		)

	def handle_endtag(self, tag):
		tag = tag.lower()
		if self.skip_depth:
			if tag == self.skip_tag:
				self.skip_depth -= 1
				if not self.skip_depth:
					self.skip_tag = None
			return
		if tag in ALLOWED_TAGS and tag not in VOID_TAGS:
			self.out.append(f"</{tag}>")

	# -- text ---------------------------------------------------------------
	def handle_data(self, data):
		if not self.skip_depth:
			self.out.append(escape(data, quote=False))

	def handle_entityref(self, name):
		if not self.skip_depth:
			self.out.append(f"&{name};")

	def handle_charref(self, name):
		if not self.skip_depth:
			self.out.append(f"&#{name};")

	def handle_comment(self, data):
		pass

	def handle_decl(self, decl):
		pass

	def handle_pi(self, data):
		pass

	def unknown_decl(self, data):
		pass


def sanitize_html(html: str) -> str:
	"""`html` with everything outside the allow-list removed."""
	if not html or "<" not in html:
		return html or ""
	parser = _Sanitizer()
	parser.feed(html)
	parser.close()
	return "".join(parser.out)
