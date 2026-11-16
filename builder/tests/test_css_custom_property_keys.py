# //// Neoffice — added file (no upstream equivalent): a block's CSS custom property keeps its name from the
# //// legacy rawStyles to the stored page and the render (neoffice-maintenance#2671).
import json
import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.builder.doctype.builder_page.builder_page import get_style
from builder.builder.patches import repair_css_custom_property_keys as repair
from builder.utils import normalize_legacy_raw_styles, repair_custom_property_keys, repaired_custom_property

# what the old site generator wrote on a section: its colours as variables, in rawStyles
SECTION = {
	"element": "section",
	"blockId": "services-001",
	"baseStyles": {"paddingTop": "80px"},
	"rawStyles": {
		"--primary-color": "var(--gf-primary)",
		"--primary-rgb": "37, 99, 235",
		"border-color": "#ddd",
	},
	"children": [],
}


class TestLegacyRawStyles(unittest.TestCase):
	def test_a_custom_property_keeps_its_name_when_rawstyles_are_merged(self):
		blocks = normalize_legacy_raw_styles([json.loads(json.dumps(SECTION))])
		styles = blocks[0]["baseStyles"]

		self.assertEqual(styles.get("--primary-color"), "var(--gf-primary)")
		self.assertEqual(styles.get("--primary-rgb"), "37, 99, 235")
		self.assertNotIn("-PrimaryColor", styles)
		self.assertEqual(styles.get("borderColor"), "#ddd")
		self.assertIn("--primary-color: var(--gf-primary);", get_style(styles))

	def test_a_broken_key_is_recognised_and_put_back(self):
		self.assertEqual(repaired_custom_property("-PrimaryColor"), "--primary-color")
		self.assertEqual(repaired_custom_property("-GfPrimary"), "--gf-primary")
		self.assertEqual(repaired_custom_property("hover:-SecondaryColor"), "hover:--secondary-color")
		for key in ("backgroundColor", "WebkitLineClamp", "--primary-color", "-webkit-box", "hover:color"):
			self.assertIsNone(repaired_custom_property(key), key)

	def test_a_tree_is_repaired_the_correct_key_winning(self):
		tree = [
			{
				"baseStyles": {
					"-PrimaryColor": "red",
					"--secondary-color": "#fff",
					"-SecondaryColor": "#000",
				},
				"children": [{"mobileStyles": {"-PrimaryRgb": "1, 2, 3"}}],
			}
		]
		self.assertEqual(repair_custom_property_keys(tree), 3)
		self.assertEqual(tree[0]["baseStyles"], {"--primary-color": "red", "--secondary-color": "#fff"})
		self.assertEqual(tree[0]["children"][0]["mobileStyles"], {"--primary-rgb": "1, 2, 3"})


class TestRepairStoredPages(FrappeTestCase):
	"""The proposed patch (not in patches.txt): counts, then repairs a draft the old editor saved."""

	def test_a_broken_draft_is_counted_then_repaired_without_touching_its_date(self):
		broken = [
			{"element": "section", "baseStyles": {"-PrimaryColor": "var(--gf-primary)"}, "children": []}
		]
		page = frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Custom property 2671",
				"draft_blocks": json.dumps(broken),
			}
		).insert()
		modified = frappe.db.get_value("Builder Page", page.name, "modified")
		before = repair.count()

		repair.execute()

		draft = json.loads(frappe.db.get_value("Builder Page", page.name, "draft_blocks"))
		self.assertEqual(draft[0]["baseStyles"], {"--primary-color": "var(--gf-primary)"})
		self.assertEqual(frappe.db.get_value("Builder Page", page.name, "modified"), modified)
		self.assertGreaterEqual(before["keys"], 1)
		self.assertEqual(repair.count(), {"trees": 0, "keys": 0})
