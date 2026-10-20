# //// Neoffice — added file (no upstream equivalent): the patch that drops the five tables the legacy-AI drop patches left behind.
"""The patches that "dropped" Builder Chat Session, Builder Chat Message, Builder Site Config, Builder Site Config Page and
Builder Page Library removed their DocType records and left their tables: `frappe.delete_doc("DocType", ...)` does not drop a
table. On osiris they held 50 conversations and 253 messages of the pre-1.33 generator, and nothing reads them. This patch
drops the tables, after saying how many rows each held.

The drop itself is tested on a throwaway table (test_drop_builder_ai_shortcode.py), so that no test removes the real ones.
What is held here is what is specific to these five: which they are, when the patch runs, what it says, and that nothing in
the code base reads them (the reason it is safe)."""

import pathlib
import unittest
from unittest.mock import patch

import frappe

from builder.builder.patches import drop_legacy_ai_tables as the_patch
from builder.tests.test_drop_builder_ai_shortcode import listed

APP = pathlib.Path(__file__).parent.parent
FIVE = (
	"Builder Chat Message",
	"Builder Chat Session",
	"Builder Site Config Page",
	"Builder Site Config",
	"Builder Page Library",
)


class TestTheFiveTables(unittest.TestCase):
	def test_they_are_the_five_the_older_patches_left(self):
		self.assertEqual(the_patch.DOCTYPES, FIVE)

	def test_it_runs_after_the_patches_that_removed_their_records(self):
		"""So that a site which still has the DocType loses the record first, and its table after."""
		patches = listed()["post_model_sync"]
		mine = patches.index("builder.builder.patches.drop_legacy_ai_tables")
		for earlier in (
			"builder.builder.patches.drop_builder_chat_session",
			"builder.builder.patches.drop_builder_site_config",
		):
			self.assertLess(patches.index(earlier), mine, earlier)

	def test_it_drops_exactly_those(self):
		with (
			patch.object(the_patch, "drop", return_value={"Builder Chat Message": 253}) as drop,
			patch("frappe.db.commit") as commit,
		):
			the_patch.execute()
		drop.assert_called_once_with(FIVE)
		commit.assert_called_once()

	def test_the_row_counts_are_journaled_by_the_drop_it_uses(self):
		"""The count is said by drop(), before each table goes (test_drop_builder_ai_shortcode): this patch must use it."""
		from builder.builder.patches import drop_builder_ai_shortcode

		self.assertIs(the_patch.drop, drop_builder_ai_shortcode.drop)

	def test_a_site_that_has_none_of_them_commits_nothing(self):
		with patch.object(the_patch, "drop", return_value={}), patch("frappe.db.commit") as commit:
			the_patch.execute()
		commit.assert_not_called()


class TestNothingReadsThem(unittest.TestCase):
	"""The reason dropping them is safe. If this fails, someone started reading a table that is gone."""

	def test_no_python_or_doctype_file_of_the_app_names_one_of_them(self):
		offenders = []
		for path in list(APP.rglob("*.py")) + list(APP.rglob("*.json")):
			relative = path.relative_to(APP).parts
			# the patches that dropped them and the tests of those patches say the names; nothing else may
			if (
				"patches" in relative
				or "tests" in relative
				or "node_modules" in relative
				or "locale" in relative
			):
				continue
			if "public" in relative:
				continue
			text = path.read_text(encoding="utf-8", errors="replace")
			offenders += [
				f"{'/'.join(relative)}: {name}" for name in FIVE if f'"{name}"' in text or f"'{name}'" in text
			]
		self.assertEqual(offenders, [])

	def test_no_doctype_is_shipped_for_any_of_them(self):
		for name in FIVE:
			with self.subTest(name):
				folder = APP / "builder/doctype" / frappe.scrub(name)
				self.assertFalse((folder / f"{frappe.scrub(name)}.json").exists())
