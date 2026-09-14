# //// Neoffice — added file (no upstream equivalent): the per-page settings of the top page band
# //// (builder/page_header.py). A page may go without the band, or give it a subtitle of its own,
# //// from its page settings in the editor (2026-09-14). Custom fields: the upstream doctype stays as it is.
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"Builder Page": [
				{
					"fieldname": "hide_page_header",
					"fieldtype": "Check",
					"label": "No top page on this page",
					"insert_after": "meta_description",
					"default": "0",
				},
				{
					"fieldname": "page_header_subtitle",
					"fieldtype": "Data",
					"label": "Top page subtitle",
					"insert_after": "hide_page_header",
				},
			]
		},
		update=True,
	)
