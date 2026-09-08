# //// Neoffice — added file (no upstream equivalent): the footer newsletter strings were
# //// English defaults copied into every Website Header Footer Config and Variant, so the
# //// footer of a French site read "Subscribe to our newsletter" although footer.html
# //// translates an empty field in the visitor's language (B2C run, 2026-09-08). Blank
# //// them where they still are the default; a client's own wording is left alone.
import frappe

from builder.hf_utils.header_footer import NEWSLETTER_DEFAULTS


def execute():
	for field, default in NEWSLETTER_DEFAULTS.items():
		if frappe.db.exists("DocType", "Website Header Footer Variant") and frappe.db.has_column("Website Header Footer Variant", field):
			frappe.db.set_value("Website Header Footer Variant", {field: default}, field, "", update_modified=False)
		if frappe.db.exists("DocType", "Website Header Footer Config") and frappe.db.get_single_value("Website Header Footer Config", field) == default:
			frappe.db.set_single_value("Website Header Footer Config", field, "")
