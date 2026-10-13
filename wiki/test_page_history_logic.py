import unittest

from wiki.page_history_logic import distinct_versions


def snap(revision, blob, title="Page", deleted=0):
	return {"revision": revision, "content_blob": blob, "title": title, "is_deleted": deleted}


class TestDistinctVersions(unittest.TestCase):
	def names(self, snapshots):
		return [v["revision"] for v in distinct_versions(snapshots)]

	def test_a_page_left_alone_lists_the_merge_that_changed_it(self):
		# newest first: r4 r3 r2 r1; the content changed in r2 only
		snapshots = [snap("r4", "b"), snap("r3", "b"), snap("r2", "b"), snap("r1", "a")]
		self.assertEqual(self.names(snapshots), ["r2", "r1"])

	def test_every_change_is_a_version(self):
		snapshots = [snap("r3", "c"), snap("r2", "b"), snap("r1", "a")]
		self.assertEqual(self.names(snapshots), ["r3", "r2", "r1"])

	def test_a_title_change_alone_counts(self):
		snapshots = [snap("r2", "a", title="New"), snap("r1", "a", title="Old")]
		self.assertEqual(self.names(snapshots), ["r2", "r1"])

	def test_going_back_to_an_old_text_is_a_new_version(self):
		snapshots = [snap("r3", "a"), snap("r2", "b"), snap("r1", "a")]
		self.assertEqual(self.names(snapshots), ["r3", "r2", "r1"])

	def test_empty(self):
		self.assertEqual(distinct_versions([]), [])
