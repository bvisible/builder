import frappe


def execute():
	"""Add google_map shortcode to AI Settings if not exists"""
	if not frappe.db.exists("DocType", "AI Settings"):
		return

	settings = frappe.get_single("AI Settings")

	# Check if google_map shortcode already exists
	existing_shortcodes = [s.shortcode for s in settings.shortcodes]
	if "{{ google_map address=\"...\" }}" in existing_shortcodes:
		return

	settings.append("shortcodes", {
		"shortcode": '{{ google_map address="..." }}',
		"name1": "Google Map",
		"category": "Media",
		"description": "Displays an interactive Google Map with the specified address. No API key required.",
		"use_when": "On contact pages, about pages, or whenever showing a physical location",
		"jinja_code": "{% include 'builder/templates/includes/google_map.html' %}"
	})

	settings.flags.ignore_mandatory = True
	settings.save(ignore_permissions=True)
	frappe.db.commit()
