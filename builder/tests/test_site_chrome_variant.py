# //// Neoffice — added file (no upstream equivalent): a profile's chrome is bootstrapped from the
# //// site's own chrome, and that copy must carry the MENU.
#
# The bootstrap copied every scalar field of the Single — colours, fonts, layouts, logos — and
# skipped the child tables, so the new variant came out with an empty header and an empty footer.
# It runs on a plain READ (a page rendered under a profile that has no variant yet), so a live
# site lost its navigation with nobody editing anything: found on the dev instance on 2026-09-18,
# whose variant had been created by Guest two days earlier with zero rows.
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import frappe


class _Row(dict):
	def as_dict(self):
		return dict(self)


class _Doc:
	"""Enough of a Document for the bootstrap: fields, get/set, append, insert."""

	def __init__(self, fields, values=None):
		self.meta = SimpleNamespace(fields=fields)
		self._values = dict(values or {})
		self.inserted = False

	def get(self, fieldname, default=None):
		return self._values.get(fieldname, default)

	def set(self, fieldname, value):
		self._values[fieldname] = value

	def append(self, fieldname, values):
		self._values.setdefault(fieldname, []).append(_Row(values))

	def insert(self, **kwargs):
		self.inserted = True

	def __setattr__(self, name, value):
		# "insert" is here so a test can replace the method: without it the assignment would land
		# in _values, the real method would still run, and the test would prove nothing
		if name in ("meta", "_values", "inserted", "insert"):
			object.__setattr__(self, name, value)
		else:
			self._values[name] = value

	def __getattr__(self, name):
		try:
			return object.__getattribute__(self, "_values")[name]
		except KeyError as e:
			raise AttributeError(name) from e


FIELDS = [
	SimpleNamespace(fieldname="header_layout", fieldtype="Select"),
	SimpleNamespace(fieldname="primary_color", fieldtype="Color"),
	SimpleNamespace(fieldname="menu_items", fieldtype="Table", options="Website Menu Item"),
	SimpleNamespace(fieldname="footer_links", fieldtype="Table", options="Website Footer Link"),
	SimpleNamespace(fieldname="access_section", fieldtype="Section Break"),
	SimpleNamespace(fieldname="website_profile", fieldtype="Link"),
]

SINGLE_VALUES = {
	"header_layout": "Logo | Menu Center | Icons",
	"primary_color": "#E85D2B",
	"menu_items": [
		_Row({"name": "row-1", "parent": "Website Header Footer Config", "parentfield": "menu_items", "idx": 1, "label": "Accueil", "url": "/"}),
		_Row({"name": "row-2", "parent": "Website Header Footer Config", "parentfield": "menu_items", "idx": 2, "label": "Contact", "url": "/contact"}),
	],
	"footer_links": [
		_Row({"name": "row-3", "parent": "Website Header Footer Config", "parentfield": "footer_links", "idx": 1, "label": "Conditions", "url": "/terms"}),
	],
}


class TestChromeVariantBootstrap(unittest.TestCase):
	def _bootstrap(self, insert_raises=False):
		from builder import api

		single = _Doc(FIELDS, SINGLE_VALUES)
		created = _Doc(FIELDS)
		if insert_raises:
			def boom(**kwargs):
				raise frappe.ValidationError("no write access")

			created.insert = boom

		existing = {"DocType": True}

		def exists(doctype, name=None):
			if doctype == "DocType":
				return True
			return existing.get("variant", False)

		with (
			patch.object(frappe.db, "exists", side_effect=exists),
			patch.object(frappe, "get_single", return_value=single),
			patch.object(frappe, "new_doc", return_value=created),
			patch.object(frappe.db, "commit"),
			patch.object(frappe, "get_doc", return_value=created),
			patch.object(frappe, "log_error"),
		):
			returned = api._get_site_chrome_config("A Storefront")
		return created, single, returned

	def test_the_menu_is_carried_into_the_new_variant(self):
		"""The defect itself: a bootstrapped profile had a header with nothing in it."""
		created, _, _ = self._bootstrap()
		self.assertEqual([row["label"] for row in created.get("menu_items") or []], ["Accueil", "Contact"])
		self.assertEqual([row["url"] for row in created.get("menu_items") or []], ["/", "/contact"])

	def test_the_footer_links_are_carried_too(self):
		created, _, _ = self._bootstrap()
		self.assertEqual([row["label"] for row in created.get("footer_links") or []], ["Conditions"])

	def test_a_copied_row_does_not_carry_the_identity_of_the_row_it_came_from(self):
		"""name/parent/idx belong to the Single's rows: copied over, they make the new rows fight
		the originals for their primary key."""
		created, _, _ = self._bootstrap()
		for row in created.get("menu_items") or []:
			for stolen in ("name", "parent", "parentfield", "idx"):
				self.assertNotIn(stolen, row, f"{stolen} was copied from the source row")

	def test_the_scalar_fields_are_still_copied(self):
		created, _, _ = self._bootstrap()
		self.assertEqual(created.get("header_layout"), "Logo | Menu Center | Icons")
		self.assertEqual(created.get("primary_color"), "#E85D2B")
		self.assertEqual(created.get("website_profile"), "A Storefront")

	def test_a_bootstrap_that_cannot_be_written_falls_back_to_the_site_chrome(self):
		"""This runs on a READ: a page render must not 500 because the copy could not be saved."""
		created, single, returned = self._bootstrap(insert_raises=True)
		self.assertIs(returned, single)
