# Give existing sites a header style.
#
# The field arrived after these configs were created, so they carry no value
# and the Theme tab shows an empty "Select option". The renderer already falls
# back to Classic, which is exactly what these sites look like today — this
# only writes down what is already true.
import frappe

DOCTYPES = ("Website Header Footer Config", "Website Header Footer Variant")


def execute():
	for doctype in DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue
		if not frappe.get_meta(doctype).get_field("header_style"):
			continue
		frappe.db.sql(
			f"""update `tab{doctype}`
			   set header_style = 'Classic'
			   where header_style is null or header_style = ''"""
		)
	frappe.db.commit()
