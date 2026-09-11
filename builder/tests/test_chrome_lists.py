# //// Neoffice — added file (no upstream equivalent): the site's chrome and a profile's chrome
# //// accept the same values.
import json
import os
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _selects(doctype_folder: str) -> dict[str, list[str]]:
	path = os.path.join(HERE, "builder", "doctype", doctype_folder, f"{doctype_folder}.json")
	with open(path) as f:
		fields = json.load(f)["fields"]
	return {f["fieldname"]: (f.get("options") or "").split("\n") for f in fields if f.get("fieldtype") == "Select"}


class TestTwinLists(unittest.TestCase):
	def test_a_profile_accepts_every_value_the_site_accepts(self):
		"""A brief may pick any value the site's chrome offers; the profile's Variant refused
		"Centered" for its footer, and the whole chrome from the brief was dropped with it."""
		site = _selects("website_header_footer_config")
		variant = _selects("website_header_footer_variant")
		missing = {
			name: sorted(set(options) - set(variant[name]))
			for name, options in site.items()
			if name in variant and set(options) - set(variant[name])
		}
		self.assertEqual(missing, {})
