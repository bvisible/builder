# //// Neoffice — added file (no upstream equivalent): the agent writes a page's draft only over
# //// the draft it read (neoffice-maintenance#395).
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe

from builder.ai import page_writer

MINE = {"blockId": "root", "originalElement": "body", "children": [{"blockId": "mine", "children": []}]}
THEIRS = '[{"blockId": "root", "originalElement": "body", "children": [{"blockId": "theirs", "children": []}]}]'


class TestSaveDraftBlocksOverWhatItRead(unittest.TestCase):
	"""After a site build, the agent's next edit landed on the page as it was before the build
	and was saved over the build's draft without a word."""

	def setUp(self):
		frappe.db.savepoint("draft_version_test")
		self.page = frappe.get_doc({"doctype": "Builder Page", "page_title": "Draft version test", "published": 0}).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.db.rollback(save_point="draft_version_test")
		if frappe.db.exists("Builder Page", self.page.name):
			frappe.delete_doc("Builder Page", self.page.name, ignore_permissions=True, force=True)

	def test_a_write_over_the_draft_it_read_passes(self):
		_, base = page_writer.load_page_draft(self.page.name)
		written = page_writer.save_draft_blocks(self.page.name, MINE, expected=base)
		self.assertIsNotNone(written)
		self.assertEqual(frappe.db.get_value("Builder Page", self.page.name, "draft_blocks"), written)

	def test_blocks_written_elsewhere_are_not_overwritten(self):
		_, base = page_writer.load_page_draft(self.page.name)
		frappe.db.set_value("Builder Page", self.page.name, "draft_blocks", THEIRS)
		self.assertIsNone(page_writer.save_draft_blocks(self.page.name, MINE, expected=base))
		self.assertEqual(frappe.db.get_value("Builder Page", self.page.name, "draft_blocks"), THEIRS)

	def test_a_settings_change_is_no_conflict(self):
		_, base = page_writer.load_page_draft(self.page.name)
		# a settings tool moves `modified`, not the blocks
		frappe.db.set_value("Builder Page", self.page.name, "page_title", "Draft version test, renamed")
		self.assertIsNotNone(page_writer.save_draft_blocks(self.page.name, MINE, expected=base))

	def test_the_comparison_counts_case(self):
		frappe.db.set_value("Builder Page", self.page.name, "draft_blocks", '[{"color": "#FFFFFF"}]')
		self.assertIsNone(page_writer.save_draft_blocks(self.page.name, MINE, expected='[{"color": "#ffffff"}]'))


class TestPersistTree(unittest.TestCase):
	def runner(self, base="what the tree read"):
		from builder.ai.agent.loop import WorkingTree

		return SimpleNamespace(page_id="page-1", tree=WorkingTree(MINE, base=base), emit=MagicMock())

	def test_a_saved_round_moves_the_base(self):
		from builder.ai.agent import loop

		runner = self.runner()
		with patch("builder.ai.page_writer.save_draft_blocks", return_value="what the round wrote") as save:
			self.assertTrue(loop.AgentRunner.persist_tree(runner))
		save.assert_called_once_with("page-1", MINE, expected="what the tree read")
		self.assertEqual(runner.tree.base, "what the round wrote")
		runner.emit.assert_not_called()

	def test_a_page_changed_elsewhere_reloads_and_refetches(self):
		from builder.ai.agent import loop

		runner = self.runner()
		new_root = {"blockId": "root", "children": [{"blockId": "theirs", "children": []}]}
		with patch("builder.ai.page_writer.save_draft_blocks", return_value=None), patch("builder.ai.page_writer.load_page_draft", return_value=(new_root, THEIRS)):
			self.assertFalse(loop.AgentRunner.persist_tree(runner))
		self.assertEqual(runner.tree.root, new_root)
		self.assertEqual(runner.tree.base, THEIRS)
		runner.emit.assert_called_once_with("refetch", resources=["page", "page_data", "canvas"], after_commit=False)
		self.assertIn("NOT SAVED", loop.PAGE_CHANGED_ELSEWHERE)
