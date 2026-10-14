import os
from urllib.parse import unquote

import frappe
from frappe.translate import get_all_translations

CONVERTIBLE_IMAGE_EXTENSIONS = (".png", ".jpeg", ".jpg")


@frappe.whitelist()
def get_space_capabilities(space: str) -> dict:
	"""Return the current user's read/write capabilities for a Wiki Space.

	Used by the SPA to show/hide the Merge and contribute actions. Enforcement
	always remains server-side in the permission hooks and Change Request
	controller.
	"""
	from wiki.permissions import (
		can_contribute_to_space,
		can_delete_space,
		can_read_space,
		can_write_space,
	)

	return {
		"can_read": can_read_space(space),
		"can_write": can_write_space(space),
		"can_contribute": can_contribute_to_space(space),
		"can_delete": can_delete_space(space),
	}


@frappe.whitelist()
def get_user_info() -> dict:
	"""Get basic information about the logged-in user."""
	if frappe.session.user == "Guest":
		return {"is_logged_in": False}

	user = frappe.get_cached_doc("User", frappe.session.user)

	return {
		"name": user.name,
		"is_logged_in": True,
		"first_name": user.first_name,
		"last_name": user.last_name,
		"full_name": user.full_name,
		"email": user.email,
		"user_image": user.user_image,
		"roles": user.roles,
		"brand_image": frappe.get_single_value("Website Settings", "banner_image"),
		"language": user.language,
	}


@frappe.whitelist(allow_guest=True)
def get_translations():
	if frappe.session.user != "Guest":
		language = frappe.db.get_value("User", frappe.session.user, "language")
	else:
		language = frappe.db.get_single_value("Wiki Settings", "public_language")

	language = language or frappe.db.get_single_value("System Settings", "language")

	return get_all_translations(language)


@frappe.whitelist()
def get_file_sizes(urls: list[str] | str) -> dict[str, str]:
	"""Human-readable sizes of uploaded files by `file_url`, for the editor's
	attachments list. Sizes only: the files themselves stay behind their own
	permissions."""
	from wiki.wiki.attachments import format_file_size

	if isinstance(urls, str):
		urls = frappe.parse_json(urls)

	urls = [
		url for url in (urls or []) if isinstance(url, str) and url.startswith(("/files/", "/private/files/"))
	]
	if not urls:
		return {}

	# Links are percent-encoded; the File record holds the plain name.
	wanted = urls[:50]
	lookup = {unquote(url): url for url in wanted} | {url: url for url in wanted}
	rows = frappe.get_all(
		"File",
		filters={"file_url": ("in", list(lookup))},
		fields=["name", "file_url", "file_size", "is_private"],
	)
	# A public file's size is no secret. A private one is reported only to someone who
	# may read that file, or the list would tell anyone the size of any private upload.
	return {
		lookup[row.file_url]: format_file_size(row.file_size)
		for row in rows
		if not row.is_private or frappe.has_permission("File", "read", doc=row.name)
	}


def _to_webp(path_or_url: str) -> str:
	"""Swap any file extension for `.webp` (works for both fs paths and URLs)."""
	return os.path.splitext(path_or_url)[0] + ".webp"


def _save_webp_without_overwrite(image, name: str, is_private: bool = False) -> str:
	"""Write `image` to a new file, never over an existing one.

	generate_file_name only checks that the name is free. Two same-named
	uploads converting at once (several images pasted together) both passed
	that check, and the second write replaced the first image.
	"""
	from frappe.core.doctype.file.utils import get_file_name
	from frappe.utils import get_files_path

	for _ in range(5):
		path = get_files_path(name, is_private=is_private)
		try:
			# nosemgrep: frappe-semgrep-rules.rules.security.frappe-security-file-traversal
			f = open(path, "xb")
		except FileExistsError:
			name = get_file_name(name, frappe.generate_hash(length=6))
			continue
		try:
			with f:
				image.save(f, "WEBP")
		except Exception:
			os.remove(path)
			raise
		return name
	raise FileExistsError(name)


def convert_file_to_webp(file_doc) -> str:
	"""Convert a local PNG/JPEG File doc to WebP in place.

	Replaces the file on disk, deletes the original, and updates the doc's
	file_url. Returns the new (or unchanged, if not convertible) file_url.
	"""
	from frappe.core.doctype.file.file import get_local_image
	from frappe.core.doctype.file.utils import delete_file, generate_file_name
	from frappe.utils import get_files_path

	if not file_doc:
		return ""

	file_url = file_doc.file_url or ""
	# Only act on local site files of a convertible raster format.
	is_private = file_url.startswith("/private/files")
	if not (is_private or file_url.startswith("/files")) or not file_url.lower().endswith(
		CONVERTIBLE_IMAGE_EXTENSIONS
	):
		return file_url

	webp_name = generate_file_name(
		_to_webp(file_doc.file_name or os.path.basename(file_url)), is_private=is_private
	)

	try:
		image, _, _ = get_local_image(file_url)
		webp_name = _save_webp_without_overwrite(image, webp_name, is_private=is_private)
	except Exception:
		# Corrupt or unsupported image — keep the original upload rather than
		# failing the whole request and losing the author's image.
		frappe.log_error(title="Wiki WebP conversion failed")
		return file_url

	# delete_file resolves public/private from the URL's leading segment, so it
	# must be given the /files/... url — not the absolute filesystem path.
	delete_file(file_url)

	file_doc.file_url = f"{'/private' if is_private else ''}/files/{webp_name}"
	file_doc.file_name = webp_name
	file_doc.save()
	return file_doc.file_url


def _share_private_upload_with_the_space(file_doc) -> None:
	"""Let everyone who can read the space open a private file uploaded into it.

	Frappe opens a private file only for its owner, or for whoever may read the document it
	is attached to. An attachment is a link inside a page, with no document to attach to, so
	without this only the uploader (and administrators) could download it. It is attached to
	the Wiki Space, whose read permission is the wiki's own access control. Anything that
	fails here leaves the file private to its owner: it never becomes more open.
	"""
	from wiki.permissions import can_read_space

	space = frappe.form_dict.get("space")
	if not file_doc or not file_doc.is_private or not isinstance(space, str) or not space:
		return
	if not frappe.db.exists("Wiki Space", space) or not can_read_space(space):
		return
	frappe.db.set_value(
		"File",
		file_doc.name,
		{"attached_to_doctype": "Wiki Space", "attached_to_name": space},
		update_modified=False,
	)
	file_doc.attached_to_doctype = "Wiki Space"
	file_doc.attached_to_name = space


def _refuse_active_uploads():
	"""Pages, scripts and scripted SVGs would run from the site's own origin; see upload_guard."""
	from wiki.upload_guard import upload_problem

	upload = (frappe.request.files or {}).get("file") if frappe.request else None
	if upload is None:
		return
	head = upload.stream.read(2_000_000)
	upload.stream.seek(0)
	if problem := upload_problem(upload.filename, head):
		frappe.throw(frappe._(problem), frappe.ValidationError)


@frappe.whitelist()
def upload_wiki_asset():
	"""Upload handler for wiki editor assets.

	Wraps Frappe's standard file upload. When the `auto_convert_images_to_webp`
	Wiki Setting is enabled, uploaded PNG/JPEG images are converted to WebP
	before the File doc is returned, so the editor receives the optimized URL.
	"""
	from frappe.handler import upload_file

	_refuse_active_uploads()
	file_doc = upload_file()
	_share_private_upload_with_the_space(file_doc)
	if (
		file_doc
		and (file_doc.file_url or "").lower().endswith(CONVERTIBLE_IMAGE_EXTENSIONS)
		and frappe.get_cached_value("Wiki Settings", "Wiki Settings", "auto_convert_images_to_webp")
	):
		convert_file_to_webp(file_doc)
	return file_doc
