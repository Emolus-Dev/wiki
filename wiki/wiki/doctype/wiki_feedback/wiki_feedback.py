# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.rate_limiter import rate_limit
from frappe.utils import validate_email_address

from wiki.telemetry import capture


class WikiFeedback(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		email_id: DF.Data | None
		feedback: DF.SmallText | None
		rating: DF.Rating
		status: DF.Literal["Open", "Closed"]
		type: DF.Literal["Good", "Bad", "Ok"]
		wiki_document: DF.Link
		wiki_page: DF.Link | None
	# end: auto-generated types

	def after_insert(self):
		capture("feedback_submitted", sentiment=self.sentiment(), has_comment=bool(self.feedback))

	def sentiment(self) -> str:
		"""One scale for both APIs. `type` carries the new one's Good / Ok / Bad,
		but it also defaults to Ok, so a legacy row's star rating wins."""
		rating = float(self.rating or 0)
		if not rating:
			return (self.type or "ok").lower()
		if rating >= 0.8:
			return "good"
		return "ok" if rating >= 0.5 else "bad"


MAX_FEEDBACK_LENGTH = 2000


def _check_page_is_public_to_this_visitor(wiki_document: str) -> None:
	"""Feedback is for pages the visitor can read. One error for "no such page" and "not yours",
	so the form cannot be used to find out which page names exist."""
	not_found = (frappe._("Page not found"), frappe.DoesNotExistError)
	if not isinstance(wiki_document, str) or not frappe.db.exists("Wiki Document", wiki_document):
		frappe.throw(*not_found)
	doc = frappe.get_cached_doc("Wiki Document", wiki_document)
	doc.check_space_access("read")
	doc.check_published()


def get_feedback_limit():
	wiki_settings = frappe.get_single("Wiki Settings")
	return wiki_settings.feedback_submission_limit or 20


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=get_feedback_limit, seconds=60 * 60)
def submit_feedback(
	wiki_document=None,
	type=None,
	feedback=None,
	email=None,
	# Legacy parameters for backwards compatibility
	name=None,
	rating=None,
	feedback_index=None,
):
	"""
	Submit feedback for a wiki document.

	New API (Wiki Document):
	    wiki_document: Name of the Wiki Document
	    type: "Good", "Ok", or "Bad"
	    feedback: Optional text feedback
	    email: Optional email address

	Legacy API (Wiki Page):
	    name: Name of the Wiki Page
	    rating: Star rating (1-5)
	    feedback: Optional text feedback
	    email: Optional email address
	"""
	email = validate_email_address(email) if email else None
	# A visitor's comment is a line or two; this keeps the table from being used as storage.
	feedback = (feedback or "")[:MAX_FEEDBACK_LENGTH] or None

	# New API: Wiki Document with type
	if wiki_document and type:
		_check_page_is_public_to_this_visitor(wiki_document)
		frappe.get_doc(
			{
				"doctype": "Wiki Feedback",
				"wiki_document": wiki_document,
				"type": type,
				"feedback": feedback,
				"email_id": email,
			}
		).insert()
		return

	# Legacy API: Wiki Page with rating
	if name and rating is not None:
		frappe.get_doc(
			{
				"doctype": "Wiki Feedback",
				"wiki_page": name,
				"rating": rating,
				"feedback": feedback,
				"email_id": email,
			}
		).insert()
		return

	frappe.throw(frappe._("Invalid feedback submission parameters"))
