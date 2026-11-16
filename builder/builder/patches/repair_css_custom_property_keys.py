# //// Neoffice — added file (no upstream equivalent): puts back the CSS custom properties an older editor broke
# //// in the stored pages (neoffice-maintenance#2671). NOT listed in patches.txt: written to be decided, not run.
# ////
# //// The editor camel-cased the keys of a block's legacy rawStyles, and `--primary-color` was saved as
# //// `-PrimaryColor` in the page's draft. Nothing a visitor sees depends on it: the render writes such a key
# //// back as `--primary-color` (camel_case_to_kebab_case), and since the fix the editor puts it back when the
# //// page is opened (frontend/src/utils/cssCustomProperty.ts). What this adds is the stored data itself, for
# //// the tools that read a page's keys. Measured on the test instance (2026-11-16): 2 drafts of 495 pages,
# //// no published page.
# ////
# //// To count first, on one instance:  bench --site <site> execute builder.builder.patches.repair_css_custom_property_keys.count
import json

import frappe

from builder.utils import repair_custom_property_keys

STORED = {"Builder Page": ("blocks", "draft_blocks"), "Builder Component": ("block",)}


def _rows():
	for doctype, fields in STORED.items():
		for field in fields:
			# a broken key is a `"-` followed by a capital: a cheap filter before the JSON is read
			for row in frappe.get_all(
				doctype, filters={field: ("like", '%"-%')}, fields=["name", field], limit_page_length=0
			):
				yield doctype, field, row


def _repaired(raw):
	try:
		tree = json.loads(raw or "null")
	except ValueError:
		return None, 0
	if not tree:
		return None, 0
	count = repair_custom_property_keys(tree)
	return tree, count


def count() -> dict:
	"""How many stored trees carry a broken key, and how many keys, without writing anything."""
	found = {"trees": 0, "keys": 0}
	for _doctype, field, row in _rows():
		_tree, keys = _repaired(row[field])
		if keys:
			found["trees"] += 1
			found["keys"] += keys
	return found


def execute():
	repaired = 0
	for doctype, field, row in _rows():
		tree, keys = _repaired(row[field])
		if not keys:
			continue
		# the page is not edited: its modified date and its version history stay as they were
		frappe.db.set_value(
			doctype,
			row.name,
			field,
			json.dumps(tree, separators=(",", ":"), ensure_ascii=False),
			update_modified=False,
		)
		repaired += keys
	if repaired:
		print(f"put back {repaired} CSS custom properties saved under a broken name")
