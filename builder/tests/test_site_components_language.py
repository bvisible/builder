# //// Neoffice — added file (no upstream equivalent). The Site blocks panel shows what
# //// builder.api.get_site_components sends exactly as it arrives. The catalogue is written in
# //// English because the generator reads it as its prompt, so the endpoint translates what a
# //// person reads (name, description, note, the meaning of each parameter) and leaves every
# //// identifier (path, tag, parameter names, types and defaults) as declared.
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from builder import api


def mark(text):
	return f"fr:{text}"


class TestSiteComponentsLanguage(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def listed(self, translate):
		with patch("builder.api._", side_effect=translate):
			return api.get_site_components()

	def test_what_a_person_reads_goes_through_translation(self):
		listed = self.listed(mark)
		self.assertTrue(listed)
		for component in listed:
			where = component["path"]
			self.assertTrue(component["label"].startswith("fr:"), where)
			if component["shows"]:
				self.assertTrue(component["shows"].startswith("fr:"), where)
			if component["note"]:
				self.assertTrue(component["note"].startswith("fr:"), where)
			for param in component["params"]:
				if param.get("about"):
					self.assertTrue(param["about"].startswith("fr:"), f"{where} {param['name']}")

	def test_identifiers_are_left_as_declared(self):
		plain = self.listed(lambda text: text)
		marked = self.listed(mark)
		self.assertEqual(len(plain), len(marked))
		for before, after in zip(plain, marked, strict=True):
			for key in ("path", "app", "pages", "tag", "has_data"):
				self.assertEqual(before[key], after[key], key)
			self.assertEqual(
				[(p["name"], p["type"], p["default"]) for p in before["params"]],
				[(p["name"], p["type"], p["default"]) for p in after["params"]],
			)
