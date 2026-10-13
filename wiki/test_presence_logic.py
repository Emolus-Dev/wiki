import unittest

from wiki.presence_logic import PRESENCE_TTL, fresh_editors


class TestFreshEditors(unittest.TestCase):
	def test_lists_other_active_users_without_me(self):
		others, stale = fresh_editors({"a@x": 100, "me@x": 100, "b@x": 95}, now=110, me="me@x")
		self.assertEqual(others, ["a@x", "b@x"])
		self.assertEqual(stale, [])

	def test_a_silent_user_is_stale_and_not_listed(self):
		others, stale = fresh_editors({"a@x": 100, "old@x": 100 - PRESENCE_TTL - 1}, now=100, me="me@x")
		self.assertEqual(others, ["a@x"])
		self.assertEqual(stale, ["old@x"])

	def test_exactly_at_the_limit_is_still_active(self):
		others, _ = fresh_editors({"a@x": 100}, now=100 + PRESENCE_TTL, me="me@x")
		self.assertEqual(others, ["a@x"])

	def test_nobody_else_is_an_empty_list(self):
		self.assertEqual(fresh_editors({}, now=1, me="me@x"), ([], []))
		self.assertEqual(fresh_editors({"me@x": 1}, now=1, me="me@x"), ([], []))

	def test_values_may_come_back_as_strings(self):
		others, _ = fresh_editors({"a@x": "100.5"}, now=101, me="me@x")
		self.assertEqual(others, ["a@x"])
