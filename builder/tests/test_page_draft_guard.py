# //// Neoffice — added file (no upstream equivalent): the guard of neoffice-maintenance#306.
# //// Upstream saves the editor's draft through frappe.client.set_value, which re-reads the
# //// document before writing — check_if_latest then compares it to itself and the optimistic
# //// lock never fires. builder.api.save_page_draft takes the version the editor loaded and
# //// refuses a draft computed on an older one.
"""The draft save refuses a draft computed on a version the page has left behind."""

import unittest

import frappe

from builder.api import save_page_draft


class TestPageDraftGuard(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_name": f"draft-guard-{frappe.generate_hash(length=6)}",
				"blocks": '[{"blockId": "built", "element": "section"}]',
				"draft_blocks": '[{"blockId": "built", "element": "section"}]',
			}
		).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.delete_doc("Builder Page", self.page.name, force=True, ignore_permissions=True)
		frappe.db.commit()

	def test_a_draft_on_the_current_version_is_written(self):
		payload = '[{"blockId": "edited", "element": "section"}]'
		save_page_draft(page=self.page.name, draft_blocks=payload, loaded_modified=str(self.page.modified))
		self.assertEqual(frappe.db.get_value("Builder Page", self.page.name, "draft_blocks"), payload)

	def test_a_draft_on_an_older_version_is_refused_and_writes_nothing(self):
		# what a server tool does: it rewrites the page, so `modified` moves on
		rewritten = '[{"blockId": "generated", "element": "section"}]'
		stale_version = str(self.page.modified)
		doc = frappe.get_doc("Builder Page", self.page.name)
		doc.blocks = rewritten
		doc.draft_blocks = rewritten
		doc.save(ignore_permissions=True)
		frappe.db.commit()
		self.assertNotEqual(str(doc.modified), stale_version)

		# the editor, still holding the pre-build state, tries to save it
		with self.assertRaises(frappe.TimestampMismatchError):
			save_page_draft(
				page=self.page.name,
				draft_blocks='[{"blockId": "old-design", "element": "section"}]',
				loaded_modified=stale_version,
			)

		# nothing was written: the built page is still there
		self.assertEqual(frappe.db.get_value("Builder Page", self.page.name, "draft_blocks"), rewritten)

	def test_no_version_sent_keeps_the_old_behaviour(self):
		# an older editor bundle sends no version; it must still be able to save
		payload = '[{"blockId": "no-token", "element": "section"}]'
		save_page_draft(page=self.page.name, draft_blocks=payload)
		self.assertEqual(frappe.db.get_value("Builder Page", self.page.name, "draft_blocks"), payload)


if __name__ == "__main__":
	unittest.main()
