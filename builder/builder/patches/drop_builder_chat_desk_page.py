import frappe


def execute():
	"""The AI chat now lives in the builder SPA, not in a desk page.

	Removing the files leaves the Page record behind on sites that already
	have it, which would show an empty desk page in the awesome bar.
	"""
	if frappe.db.exists("Page", "builder-chat"):
		frappe.delete_doc("Page", "builder-chat", force=True, ignore_missing=True)
