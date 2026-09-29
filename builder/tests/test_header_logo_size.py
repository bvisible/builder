# //// Neoffice — added file (no upstream equivalent): the header logo has a size of its own
# //// (2026-09-29). A client asked for a bigger logo and the header offered no setting for it.
import json
import os
import unittest
from unittest.mock import patch

import frappe

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def render_header(**context):
	base = {"layout": "A", "menu_position": "center", "icons": frappe._dict(), "logo": None, "cta": None,
	        "colors": {}, "menu_items": [], "sticky": 0, "header_style": "Classic", "header_scroll": "Always visible"}
	base.update(context)
	return frappe.render_template("builder/templates/includes/header_footer/header.html", base)


class TestHeaderLogoSize(unittest.TestCase):
	def test_the_header_carries_the_chosen_size(self):
		self.assertIn("site-header--logo-large", render_header(logo_height="Large"))
		self.assertIn("site-header--logo-small", render_header(logo_height="Small"))

	def test_a_site_that_chose_nothing_keeps_the_size_it_had(self):
		html = render_header()
		self.assertIn("site-header--logo-medium", html)
		self.assertNotIn("site-header--logo-large", html)

	def test_the_setting_reaches_the_header(self):
		"""render_header() hands the chrome config's choice to the template."""
		from builder.hf_utils import header_footer

		config = frappe.new_doc("Website Header Footer Config")
		config.header_logo_height = "Large"
		seen = {}

		def capture(path, context):
			if path.endswith("header.html"):
				seen.update(context)
			return ""

		with patch.object(header_footer, "get_theme_css", return_value=""), patch.object(frappe, "render_template", side_effect=capture):
			header_footer.render_header(config)
		self.assertEqual("Large", seen.get("logo_height"))

	def test_the_two_chrome_doctypes_offer_the_same_sizes(self):
		"""Read from the doctype files, not the instance: a test that reads a site's cached meta is
		green where the site was migrated and red anywhere else."""
		for folder in ("website_header_footer_config", "website_header_footer_variant"):
			path = os.path.join(HERE, "builder", "doctype", folder, f"{folder}.json")
			with open(path, encoding="utf-8") as f:
				doc = json.load(f)
			field = next((x for x in doc["fields"] if x["fieldname"] == "header_logo_height"), None)
			self.assertIsNotNone(field, folder)
			self.assertEqual(["Small", "Medium", "Large"], field["options"].split("\n"), folder)
			self.assertEqual("Medium", field["default"], folder)
			self.assertIn("header_logo_height", doc["field_order"], folder)
