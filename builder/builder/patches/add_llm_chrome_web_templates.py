import frappe

# The .llm-navbar wrapper scopes CSS fixes (e.g. hover underline) on non-Builder pages.
NAVBAR_TEMPLATE = '<div class="llm-navbar">{{ navbar_html or "" }}</div>'

# No bootstrap .container wrapper: the Builder footer component manages its own
# width; the container capped it at ~1200px on webshop pages while Builder pages
# render it full-bleed.
FOOTER_TEMPLATE = """<footer class="llm-footer">
  {{ footer_html or "" }}
</footer>"""


def execute():
	"""Own the LLM Navbar/Footer Web Templates under the Builder module.

	They historically shipped as standard templates of the deprecated
	neoffice_ia_builder app. Re-owning them here (standard=0, template stored
	in the DB) keeps legacy sites rendering after that app is uninstalled —
	builder.overrides.site_chrome points navbar_template/footer_template at
	them when site_config enables builder_legacy_site_chrome.
	"""
	templates = {
		"LLM Navbar": NAVBAR_TEMPLATE,
		"LLM Footer": FOOTER_TEMPLATE,
	}

	for name, template in templates.items():
		if frappe.db.exists("Web Template", name):
			doc = frappe.get_doc("Web Template", name)
			doc.db_set("module", "Builder", update_modified=False)
			doc.db_set("standard", 0, update_modified=False)
			doc.db_set("template", template, update_modified=False)
		else:
			frappe.get_doc(
				{
					"doctype": "Web Template",
					"title": name,
					"type": "Component",
					"module": "Builder",
					"standard": 0,
					"template": template,
				}
			).insert(ignore_permissions=True)
