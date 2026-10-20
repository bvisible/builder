# //// Neoffice — added file (no upstream equivalent): the patch that drops Builder AI Shortcode, a child table with no parent.
"""Builder AI Shortcode was the child table of Builder AI Settings. `drop_ai_settings_doctype` removed the parents and left it
behind: a table nothing could open, whose ten rows (on osiris) the old generator's prompt read until the component catalogue
replaced it. This patch drops it, on every instance, at the next migrate.

What is held here, because a patch runs once on every instance of the fleet and cannot be taken back:
  * it is listed, after the model sync, and its file exists: an entry without its file kills `bench migrate` on the whole fleet;
  * it drops what exists, with its rows and its table, says how many rows it held, and leaves a site that never had it alone;
  * it does not depend on developer mode, which is on at osiris and off at a client;
  * it can be run twice, and it copes with a DocType record left without its table."""

import importlib
import importlib.util
import pathlib
import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.patches import drop_builder_ai_shortcode as the_patch

APP = pathlib.Path(__file__).parent.parent
PATCHES = APP / "patches.txt"
SCRATCH = "Builder Drop Probe"


def listed():
	"""{section: [dotted path of each patch]}, comments and `execute:` lines left out."""
	sections: dict[str, list[str]] = {}
	current = None
	for line in PATCHES.read_text(encoding="utf-8").splitlines():
		line = line.strip()
		if not line or line.startswith("#"):
			continue
		if line.startswith("[") and line.endswith("]"):
			current = line[1:-1]
			sections[current] = []
		elif current and not line.startswith("execute:"):
			sections[current].append(line.split()[0])
	return sections


class TestThePatchIsListed(unittest.TestCase):
	def test_it_runs_after_the_model_sync(self):
		self.assertIn("builder.builder.patches.drop_builder_ai_shortcode", listed()["post_model_sync"])

	def test_every_listed_patch_has_its_file(self):
		"""An entry without its file kills `bench migrate` on the whole fleet."""
		for section, patches in listed().items():
			for dotted in patches:
				with self.subTest(f"{section}: {dotted}"):
					self.assertIsNotNone(
						importlib.util.find_spec(dotted), f"{dotted} is listed and has no module"
					)

	def test_it_names_the_table_it_drops(self):
		self.assertEqual(the_patch.DOCTYPES, ("Builder AI Shortcode",))
		with patch.object(the_patch, "drop", return_value={}) as drop:
			the_patch.execute()
		drop.assert_called_once_with(("Builder AI Shortcode",))

	def test_the_doctype_is_not_shipped_any_more(self):
		"""A merge must not bring it back: the folder would recreate the table at the next migrate."""
		self.assertFalse((APP / "builder/doctype/builder_ai_shortcode/builder_ai_shortcode.json").exists())


class TestTheDrop(FrappeTestCase):
	"""On a throwaway child table, so that the real one is dropped once, by the migrate, and not by a test."""

	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(self.remove_scratch)
		frappe.get_doc(
			{
				"doctype": "DocType",
				"name": SCRATCH,
				"module": "Builder",
				"custom": 1,
				"istable": 1,
				"fields": [{"fieldname": "label", "fieldtype": "Data", "label": "Label"}],
			}
		).insert(ignore_permissions=True)
		for index in range(3):
			frappe.get_doc(
				{
					"doctype": SCRATCH,
					"parent": "Nobody",
					"parenttype": "Nobody",
					"parentfield": "rows",
					"label": f"row {index}",
				}
			).insert(ignore_permissions=True)
		frappe.db.commit()

	def remove_scratch(self):
		frappe.delete_doc("DocType", SCRATCH, force=True, ignore_missing=True, ignore_permissions=True)
		frappe.db.commit()

	def test_it_drops_the_doctype_its_rows_and_its_table_and_says_how_many(self):
		self.assertTrue(frappe.db.table_exists(SCRATCH))

		dropped = the_patch.drop([SCRATCH])

		self.assertEqual(dropped, {SCRATCH: 3})
		self.assertFalse(frappe.db.exists("DocType", SCRATCH))
		self.assertFalse(frappe.db.table_exists(SCRATCH))

	def test_it_does_not_need_developer_mode(self):
		"""On at osiris, off at a client: the drop must not be one of the things that differ."""
		with patch.dict(frappe.conf, {"developer_mode": 0}):
			dropped = the_patch.drop([SCRATCH])
		self.assertEqual(dropped, {SCRATCH: 3})
		self.assertFalse(frappe.db.exists("DocType", SCRATCH))

	def test_a_second_run_changes_nothing(self):
		the_patch.drop([SCRATCH])
		self.assertEqual(the_patch.drop([SCRATCH]), {})

	def test_a_site_that_never_had_it_is_left_alone(self):
		self.assertEqual(the_patch.drop(["Builder Drop Probe That Never Existed"]), {})

	def test_a_doctype_record_left_without_its_table_is_dropped_too(self):
		frappe.db.sql_ddl(f"drop table `tab{SCRATCH}`")

		dropped = the_patch.drop([SCRATCH])

		self.assertEqual(dropped, {SCRATCH: None})
		self.assertFalse(frappe.db.exists("DocType", SCRATCH))
