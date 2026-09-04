#//// Neoffice — added file (no upstream equivalent): writes the design-token defaults down on configs
#//// that predate the fields. Neoffice migration, listed in patches.txt; frappe/builder has no
#//// equivalent. First commit 3084b026 2026-08-03.
# Give existing sites the design tokens they already look like.
#
# Corners, elevation, hover and motion arrived after these configs were
# created. The CSS falls back to Subtle/Soft/Darken/Calm, which is what these
# sites render today — this only writes it down so the Theme tab shows a value
# instead of an empty select.
import frappe

DEFAULTS = {
	"radius_style": "Subtle",
	"shadow_style": "Soft",
	"button_hover": "Darken",
	"motion_style": "Calm",
}
DOCTYPES = ("Website Header Footer Config", "Website Header Footer Variant")


def execute():
	for doctype in DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue
		meta = frappe.get_meta(doctype)
		fields = [field for field in DEFAULTS if meta.get_field(field)]
		if not fields:
			continue

		if meta.issingle:
			for field in fields:
				if not frappe.db.get_single_value(doctype, field):
					frappe.db.set_single_value(doctype, field, DEFAULTS[field])
			continue

		for name in frappe.get_all(doctype, pluck="name"):
			current = frappe.db.get_value(doctype, name, fields, as_dict=True) or {}
			for field in fields:
				if not current.get(field):
					frappe.db.set_value(doctype, name, field, DEFAULTS[field], update_modified=False)

	frappe.db.commit()
