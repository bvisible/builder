#//// Neoffice — added file (no upstream equivalent): removes the old builder-chat desk Page now that
#//// the chat lives in the SPA. Neoffice migration, listed in patches.txt; frappe/builder has no
#//// equivalent. First commit 6e7b3c81 2026-07-31.
import frappe


def execute():
	"""The AI chat now lives in the builder SPA, not in a desk page.

	Removing the files leaves the Page record behind on sites that already
	have it, which would show an empty desk page in the awesome bar.
	"""
	if frappe.db.exists("Page", "builder-chat"):
		frappe.delete_doc("Page", "builder-chat", force=True, ignore_missing=True)
