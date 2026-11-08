# //// Neoffice — added file (no upstream equivalent): the site's chrome and a profile's chrome
# //// accept the same values.
import json
import os
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _fields(doctype_folder: str) -> list[dict]:
	path = os.path.join(HERE, "builder", "doctype", doctype_folder, f"{doctype_folder}.json")
	with open(path) as f:
		return json.load(f)["fields"]


def _selects(doctype_folder: str) -> dict[str, list[str]]:
	fields = _fields(doctype_folder)
	return {
		f["fieldname"]: (f.get("options") or "").split("\n") for f in fields if f.get("fieldtype") == "Select"
	}


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

	def test_a_profile_has_every_field_the_site_has(self):
		"""A field the Variant lacks is a setting every secondary site loses in silence: the
		bootstrap copies only the Variant's own fields, and a save sets the value without a column
		to keep it. The header style and its scroll behaviour were missing for three months, and
		the style a brief chose for a secondary site ("Transparent", "Floating") never reached it
		(2026-11-08)."""
		site = {f["fieldname"] for f in _fields("website_header_footer_config")}
		variant = {f["fieldname"] for f in _fields("website_header_footer_variant")}
		self.assertEqual(sorted(site - variant), [])

	def test_a_profile_field_says_what_the_site_field_says(self):
		"""Same type, same default: a Variant bootstrapped from the Single, or a value written on
		both by a brief, means the same thing on either side."""
		site = {f["fieldname"]: f for f in _fields("website_header_footer_config")}
		variant = {f["fieldname"]: f for f in _fields("website_header_footer_variant")}
		differing = {
			name: [key for key in ("fieldtype", "default") if site[name].get(key) != variant[name].get(key)]
			for name in site.keys() & variant.keys()
		}
		self.assertEqual({name: keys for name, keys in differing.items() if keys}, {})
