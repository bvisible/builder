import frappe

NAVBAR_TEMPLATE = '{{ navbar_html or "" }}'

FOOTER_TEMPLATE = """<footer class="llm-footer">
  <div class="container">
    <div class="footer-content">
      {{ footer_html or "" }}
    </div>
  </div>
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
