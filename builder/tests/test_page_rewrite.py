# //// Neoffice — added file (no upstream equivalent): the agent's working tree after a server
# //// tool rewrote the page open in the editor.
import unittest
from types import SimpleNamespace
from unittest.mock import patch

OLD = {"blockId": "root", "originalElement": "body", "children": [{"blockId": "old", "blockName": "five-panel-drop", "children": []}]}
NEW = {
	"blockId": "root",
	"originalElement": "body",
	"children": [{"blockId": name, "blockName": name, "children": []} for name in ("hero", "categories", "statement", "closing")],
}


class TestFollowPageRewrite(unittest.TestCase):
	def runner(self):
		from builder.ai.agent.loop import WorkingTree

		return SimpleNamespace(page_id="page-1", tree=WorkingTree(OLD), pending_state="before the turn")

	def test_the_tree_follows_a_site_build(self):
		"""After a site build refilled the open page, the agent's next edits matched the old
		page's blocks and its draft was saved back over the new one."""
		from builder.ai.agent import loop

		runner = self.runner()
		with (
			patch("builder.ai.page_writer.load_page_root", return_value=NEW),
			patch.object(loop.frappe.db, "exists", return_value=True),
			patch.object(loop, "capture_page_state", return_value="after the build"),
		):
			self.assertTrue(loop.AgentRunner.follow_page_rewrite(runner, "generate_site", "Site built."))
		self.assertEqual([c["blockName"] for c in runner.tree.root["children"]], ["hero", "categories", "statement", "closing"])
		# "Revert" now undoes what came after the build, not the build
		self.assertEqual(runner.pending_state, "after the build")

	def test_a_page_the_build_removed_leaves_an_empty_tree(self):
		from builder.ai.agent import loop

		runner = self.runner()
		with patch.object(loop.frappe.db, "exists", return_value=False):
			self.assertTrue(loop.AgentRunner.follow_page_rewrite(runner, "generate_site", "Site built."))
		self.assertIsNone(runner.tree.root)
		self.assertEqual(runner.pending_state, "before the turn")

	def test_other_tools_and_failures_leave_the_tree(self):
		from builder.ai.agent import loop

		runner = self.runner()
		with patch("builder.ai.page_writer.load_page_root", return_value=NEW) as load:
			self.assertFalse(loop.AgentRunner.follow_page_rewrite(runner, "update_block", "Applied to block old."))
			self.assertFalse(loop.AgentRunner.follow_page_rewrite(runner, "generate_site", "FAILED: the build stopped."))
			load.assert_not_called()
		self.assertEqual(runner.tree.root["children"][0]["blockName"], "five-panel-drop")
