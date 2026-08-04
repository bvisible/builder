"""The header and footer Web Templates frappe's base.html renders.

Kept out of install.py so it syncs from unpress_core unchanged: the chrome is
the same subsystem in both editions.
"""

import frappe


# The two Web Templates frappe's base.html renders in place of its own navbar
# and footer. They hold one call each: the chrome itself is built by
# hf_utils, so a page that goes through base.html and a Builder page render
# exactly the same header — there is no second implementation to drift.
WEB_CHROME_TEMPLATES = (
	{
		"name": "Site Header",
		"template": "{%- if render_site_header is defined -%}{{ render_site_header(standalone=True) }}{%- endif -%}",
	},
	{
		"name": "Site Footer",
		"template": "{%- if render_site_footer is defined -%}{{ render_site_footer() }}{%- endif -%}",
	},
)


def ensure_web_chrome_templates():
	"""Create (or refresh) the header/footer Web Templates."""
	if not frappe.db.exists("DocType", "Web Template"):
		return

	for spec in WEB_CHROME_TEMPLATES:
		if frappe.db.exists("Web Template", spec["name"]):
			doc = frappe.get_doc("Web Template", spec["name"])
			if doc.template != spec["template"]:
				doc.template = spec["template"]
				doc.save(ignore_permissions=True)
			continue

		doc = frappe.new_doc("Web Template")
		doc.name = spec["name"]
		doc.template = spec["template"]
		doc.type = "Section"
		# standard=0 keeps the body in the database; a standard template would
		# have to live in a fixed file path and we want it versioned with the app
		doc.standard = 0
		doc.insert(ignore_permissions=True)

	frappe.db.commit()
