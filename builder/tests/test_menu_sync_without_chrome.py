# //// Neoffice — added file (no upstream equivalent): the menu of a site that never configured the chrome.
from types import SimpleNamespace

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.hf_utils.menu_integration import sync_from_website_settings

CONFIG = "Website Header Footer Config"


class TestTheMenuOfASiteWithoutTheChrome(FrappeTestCase):
	"""A shop updated from July had an empty header layout: the field came after its record, and a Single's
	default is never written to a record that exists. The layout is mandatory, so every save of Website
	Settings failed to sync the menu and wrote an Error Log row (08.11)."""

	def setUp(self):
		previous = frappe.db.get_single_value(CONFIG, "header_layout")
		self.addCleanup(frappe.db.set_single_value, CONFIG, "header_layout", previous)
		frappe.db.set_single_value(CONFIG, "header_layout", "")
		self.errors_before = frappe.db.count(
			"Error Log", {"method": "Menu sync from Website Settings failed"}
		)

	def settings(self, *labels):
		items = [
			SimpleNamespace(label=label, url=f"/{label.lower()}", get=lambda key, default=None: default)
			for label in labels
		]
		return SimpleNamespace(flags=SimpleNamespace(_syncing=False), top_bar_items=items)

	def test_the_menu_follows_website_settings(self):
		sync_from_website_settings(self.settings("Shop", "Contact"), "on_update")

		config = frappe.get_single(CONFIG)
		self.assertEqual([row.label for row in config.menu_items], ["Shop", "Contact"])
		self.assertEqual(
			frappe.db.count("Error Log", {"method": "Menu sync from Website Settings failed"}),
			self.errors_before,
		)

	def test_the_site_is_not_given_a_layout(self):
		# An empty layout is what keeps frappe's navbar on a site that does not use the chrome
		# (site_chrome._inject_config_chrome): the sync must not choose one for it.
		sync_from_website_settings(self.settings("Shop"), "on_update")

		self.assertFalse(frappe.db.get_single_value(CONFIG, "header_layout"))
