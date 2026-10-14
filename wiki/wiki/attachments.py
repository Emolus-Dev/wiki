"""The files a page offers for download, read from its markdown.

An attachment is an ordinary link to an uploaded file (`[name](/files/x.xlsx)`),
or a PDF embed. Nothing is stored beside the content, so attachments travel
through change requests with the page like everything else it says.
"""

import re
from urllib.parse import unquote

import frappe

from wiki.wiki.upload_links import FENCE, UPLOAD_LINK, normalize_path

# Shown inline on the page, so listing them again as downloads would repeat them.
_INLINE_MEDIA = {
	"png",
	"jpg",
	"jpeg",
	"gif",
	"webp",
	"avif",
	"svg",
	"bmp",
	"mp4",
	"webm",
	"ogg",
	"mov",
	"avi",
	"mkv",
	"m4v",
}

# Drives the colour of a file's type chip.
_KINDS = {
	"pdf": "red",
	"doc": "blue",
	"docx": "blue",
	"odt": "blue",
	"rtf": "blue",
	"txt": "blue",
	"md": "blue",
	"xls": "green",
	"xlsx": "green",
	"ods": "green",
	"csv": "green",
	"zip": "amber",
	"gz": "amber",
	"tar": "amber",
	"7z": "amber",
	"rar": "amber",
}

_FILE_PREFIXES = ("/files/", "/private/files/")


def _label_of(head: str) -> str:
	"""The text between the brackets of a link head such as `![name](`."""
	return head[head.index("[") + 1 : head.rindex("]")]


def extract_attachments(markdown: str) -> list[dict]:
	"""Links to uploaded files in `markdown`, in order, without repeats."""
	attachments: list[dict] = []
	seen: set[str] = set()

	for match in UPLOAD_LINK.finditer(FENCE.sub(" ", markdown or "")):
		label, path = _label_of(match.group(1)), normalize_path(match.group(2))

		filename = unquote(path.rsplit("/", 1)[-1])
		extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
		if extension in _INLINE_MEDIA or path in seen:
			continue

		seen.add(path)
		attachments.append(
			{
				"url": path,
				"name": (label or "").strip() or filename,
				"filename": filename,
				"extension": extension,
				"kind": _KINDS.get(extension, "gray"),
			}
		)

	return attachments


def format_file_size(size: int | None) -> str:
	if not size:
		return ""
	units = ("B", "KB", "MB", "GB")
	value = float(size)
	for unit in units:
		if value < 1024 or unit == units[-1]:
			return f"{value:.0f} {unit}" if unit == "B" or value >= 10 else f"{value:.1f} {unit}"
		value /= 1024
	return ""


def get_page_attachments(markdown: str) -> list[dict]:
	"""`extract_attachments` plus each file's size, read in one query.

	Sizes come from the File record when there is one; a file with no record
	still lists, just without a size.
	"""
	attachments = extract_attachments(markdown)
	if not attachments:
		return attachments

	# The link is written percent-encoded, the File record holds the plain name.
	rows = frappe.get_all(
		"File",
		filters={
			"file_url": ("in", [a["url"] for a in attachments] + [unquote(a["url"]) for a in attachments])
		},
		fields=["file_url", "file_size"],
	)
	sizes = {row.file_url: row.file_size for row in rows}
	for attachment in attachments:
		size = sizes.get(attachment["url"]) or sizes.get(unquote(attachment["url"]))
		attachment["size"] = format_file_size(size)
	return attachments
