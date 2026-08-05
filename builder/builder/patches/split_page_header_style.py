# The band's single enum becomes a preset and a fill.
#
# `page_header_style` mixed a composition with a background: "Centered" is an
# alignment, "Tinted" is what the band sits on. A site could therefore never ask
# for a centred title over a photograph — half the combinations had no way of
# being said. The field is split, and what each site already chose is carried
# across rather than reset to the default.
#
# Read before writing: the old column is dropped by `bench migrate` once the
# doctype no longer declares it, so this has to run while it is still there.
import frappe

DOCTYPES = ("Website Header Footer Config", "Website Header Footer Variant")

# old value -> (template, background)
TRANSLATION = {
	"None": ("None", "None"),
	"Simple": ("Standard", "None"),
	"Centered": ("Centered", "None"),
	"Tinted": ("Standard", "Tinted"),
}


def execute():
	for doctype in DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue
		meta = frappe.get_meta(doctype)
		if not meta.get_field("page_header_template"):
			continue

		if meta.issingle:
			# A Single has no table of its own — its values live as rows in
			# `tabSingles`, so has_column() would raise TableMissingError. And
			# get_value() on that table appends an ORDER BY `creation`, a column
			# it does not have either; the read has to be direct.
			row = frappe.db.sql(
				"select `value` from `tabSingles` where `doctype`=%s and `field`=%s",
				(doctype, "page_header_style"),
			)
			old = row[0][0] if row else None
			template, background = TRANSLATION.get(old or "Simple", ("Standard", "None"))
			frappe.db.set_single_value(doctype, "page_header_template", template)
			frappe.db.set_single_value(doctype, "page_header_background", background)
			continue

		if not frappe.db.has_column(f"tab{doctype}", "page_header_style"):
			continue

		for name, old in frappe.db.get_all(
			doctype, fields=["name", "page_header_style"], as_list=True
		):
			template, background = TRANSLATION.get(old or "Simple", ("Standard", "None"))
			frappe.db.set_value(
				doctype,
				name,
				{"page_header_template": template, "page_header_background": background},
				update_modified=False,
			)

	frappe.db.commit()
