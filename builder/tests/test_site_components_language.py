# //// Neoffice — added file (no upstream equivalent). The Site blocks panel shows what
# //// builder.api.get_site_components sends exactly as it arrives. The catalogue is written in
# //// English because the generator reads it as its prompt, so the endpoint translates what a
# //// person reads (name, description, help, the label, meaning and choices of each parameter) and
# //// leaves every identifier (path, tag, parameter names, types, defaults, choice values) as declared.
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
			# the generator's own note is not what a person reads: it is not sent at all
			self.assertNotIn("note", component, where)
			if component["help"]:
				self.assertTrue(component["help"].startswith("fr:"), where)
			for param in component["params"]:
				self.assertTrue(param["label"].startswith("fr:"), f"{where} {param['name']}")
				if param.get("about"):
					self.assertTrue(param["about"].startswith("fr:"), f"{where} {param['name']}")
				for choice in param.get("choices") or []:
					self.assertTrue(
						choice["label"].startswith("fr:"), f"{where} {param['name']} {choice['value']}"
					)

	def test_identifiers_are_left_as_declared(self):
		plain = self.listed(lambda text: text)
		marked = self.listed(mark)
		self.assertEqual(len(plain), len(marked))
		for before, after in zip(plain, marked, strict=True):
			for key in ("path", "app", "pages", "tag", "has_data", "suited"):
				self.assertEqual(before[key], after[key], key)
			self.assertEqual(
				[
					(p["name"], p["type"], p["default"], [c["value"] for c in p.get("choices") or []])
					for p in before["params"]
				],
				[
					(p["name"], p["type"], p["default"], [c["value"] for c in p.get("choices") or []])
					for p in after["params"]
				],
			)
