# //// Neoffice — added file (no upstream equivalent): the brief of a site without a profile opens.
import json

import frappe
from frappe.tests.utils import FrappeTestCase

from builder.brief_view import get_latest_brief

CONFIG = "Website Header Footer Config"


class TestTheBriefOfASiteWithoutAProfile(FrappeTestCase):
	"""It read `modified` through get_single_value, which refuses a field the meta does not
	list: every call failed in a 417 the moment a brief existed."""

	def test_the_brief_comes_back_with_its_date(self):
		previous = frappe.db.get_single_value(CONFIG, "ai_brief")
		self.addCleanup(frappe.db.set_single_value, CONFIG, "ai_brief", previous)
		frappe.db.set_single_value(CONFIG, "ai_brief", json.dumps({"business_name": "A shop"}))

		brief = get_latest_brief()

		self.assertTrue(brief["exists"])
		self.assertIn("generated_on", brief)
