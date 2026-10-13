import frappe

from wiki.api.page_history import get_page_history, get_page_version
from wiki.frappe_wiki.doctype.wiki_revision.wiki_revision import (
	get_or_create_content_blob,
)
from wiki.test_permissions import _ensure_role, _ensure_user
from wiki.tests import WikiTestCase as IntegrationTestCase
from wiki.tests.factory import make_space

ROLE = "_Test Page History Reader"
KEY = "hist-key-1"


def _merge(space, blob, title="Runbook", when="2026-01-01 10:00:00"):
	revision = frappe.get_doc(
		{
			"doctype": "Wiki Revision",
			"wiki_space": space,
			"is_merge": 1,
			"created_by": "Administrator",
			"created_at": when,
		}
	).insert(ignore_permissions=True)
	frappe.get_doc(
		{
			"doctype": "Wiki Revision Item",
			"revision": revision.name,
			"doc_key": KEY,
			"title": title,
			"content_blob": blob,
		}
	).insert(ignore_permissions=True)
	return revision


class TestPageHistory(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_ensure_role(ROLE)
		cls.outsider = _ensure_user("history_outsider@example.com", ["Wiki User"])

	def setUp(self):
		self.space = make_space(roles=[(ROLE, "Read")])
		self.blob_a = get_or_create_content_blob("first draft")
		self.blob_b = get_or_create_content_blob("second draft")

	def tearDown(self):
		frappe.set_user("Administrator")
		for revision in frappe.get_all("Wiki Revision", {"wiki_space": self.space.name}, pluck="name"):
			frappe.db.delete("Wiki Revision Item", {"revision": revision})
			frappe.delete_doc("Wiki Revision", revision, force=True)
		frappe.delete_doc("Wiki Space", self.space.name, force=True)

	def test_lists_only_the_merges_that_changed_the_page(self):
		first = _merge(self.space.name, self.blob_a, when="2026-01-01 10:00:00")
		_merge(self.space.name, self.blob_a, when="2026-01-02 10:00:00")
		third = _merge(self.space.name, self.blob_b, when="2026-01-03 10:00:00")

		versions = get_page_history(self.space.name, KEY)
		self.assertEqual([v["revision"] for v in versions], [third.name, first.name])
		self.assertEqual(versions[0]["created_by"], "Administrator")

	def test_returns_one_versions_text(self):
		first = _merge(self.space.name, self.blob_a)
		version = get_page_version(self.space.name, KEY, first.name)
		self.assertEqual(version["content"], "first draft")
		self.assertEqual(version["title"], "Runbook")

	def test_a_revision_of_another_space_is_not_found(self):
		other = make_space()
		try:
			foreign = _merge(other.name, self.blob_a)
			with self.assertRaises(frappe.DoesNotExistError):
				get_page_version(self.space.name, KEY, foreign.name)
		finally:
			for revision in frappe.get_all("Wiki Revision", {"wiki_space": other.name}, pluck="name"):
				frappe.db.delete("Wiki Revision Item", {"revision": revision})
				frappe.delete_doc("Wiki Revision", revision, force=True)
			frappe.delete_doc("Wiki Space", other.name, force=True)

	def test_a_user_without_space_access_is_refused(self):
		_merge(self.space.name, self.blob_a)
		frappe.set_user("history_outsider@example.com")
		with self.assertRaises(frappe.PermissionError):
			get_page_history(self.space.name, KEY)

	def test_a_page_with_no_merges_has_no_history(self):
		self.assertEqual(get_page_history(self.space.name, "never-merged"), [])
