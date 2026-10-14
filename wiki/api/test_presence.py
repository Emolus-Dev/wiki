import frappe

from wiki.api.presence import heartbeat, leave
from wiki.test_permissions import _ensure_user
from wiki.tests import WikiTestCase as IntegrationTestCase
from wiki.tests.factory import make_space


class TestPresence(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.ana = _ensure_user("presence_ana@example.com", ["Wiki User"])
		cls.ben = _ensure_user("presence_ben@example.com", ["Wiki User"])

	def setUp(self):
		self.space = make_space(pages=[{"title": "Runbook"}])
		self.page = "page-key"

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.cache().delete_value("wiki_presence")
		frappe.delete_doc("Wiki Space", self.space.name, force=True)

	def as_user(self, user):
		frappe.set_user(user.name if hasattr(user, "name") else user)

	def test_nobody_else_means_an_empty_list(self):
		self.as_user("presence_ana@example.com")
		self.assertEqual(heartbeat(self.space.name, self.page), [])

	def test_the_second_editor_sees_the_first_and_not_themselves(self):
		self.as_user("presence_ana@example.com")
		heartbeat(self.space.name, self.page)

		self.as_user("presence_ben@example.com")
		seen_by_ben = heartbeat(self.space.name, self.page)
		self.assertEqual(len(seen_by_ben), 1)
		self.assertNotIn("presence_ana@example.com", str(seen_by_ben))  # no email is handed out

		self.as_user("presence_ana@example.com")
		seen_by_ana = heartbeat(self.space.name, self.page)
		self.assertEqual(len(seen_by_ana), 1)
		self.assertNotIn("presence_ben@example.com", str(seen_by_ana))

	def test_leaving_removes_the_user_at_once(self):
		self.as_user("presence_ana@example.com")
		heartbeat(self.space.name, self.page)
		leave(self.space.name, self.page)

		self.as_user("presence_ben@example.com")
		self.assertEqual(heartbeat(self.space.name, self.page), [])

	def test_pages_do_not_share_presence(self):
		self.as_user("presence_ana@example.com")
		heartbeat(self.space.name, "one")
		self.as_user("presence_ben@example.com")
		self.assertEqual(heartbeat(self.space.name, "two"), [])

	def test_a_guest_is_never_tracked_or_told_anything(self):
		self.as_user("presence_ana@example.com")
		heartbeat(self.space.name, self.page)
		frappe.set_user("Guest")
		self.assertEqual(heartbeat(self.space.name, self.page), [])

	def test_a_page_key_of_its_own_making_is_ignored(self):
		self.as_user("presence_ana@example.com")
		for key in ("x" * 200, "a b", "../../etc", "", "a:b"):
			self.assertEqual(heartbeat(self.space.name, key), [])
		self.assertIsNone(frappe.cache().hget("wiki_presence", f"{self.space.name}:{'x' * 200}"))

	def test_the_last_one_to_leave_leaves_no_key_behind(self):
		self.as_user("presence_ana@example.com")
		heartbeat(self.space.name, self.page)
		leave(self.space.name, self.page)
		self.assertIsNone(frappe.cache().hget("wiki_presence", f"{self.space.name}:{self.page}"))
