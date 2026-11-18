# //// Neoffice — added file (no upstream equivalent): the forms the assistant connected say their button's words in the page's language.
# //// Neoffice migration, listed in patches.txt; frappe/builder has no equivalent.
# ////
# //// A connected form's script (builder.site_forms.guarded_form_script) showed « Sending… », « Thank you! » and « Try again » in
# //// English on every site (2026-11-18). New scripts choose them by the page's `<html lang>`; this rewrites the guarded ones that
# //// exist, with the same form, selector and fields, read back from the script.
# ////
# //// Idempotent: a script that already carries the words of each language is left alone, and so is one still on the old
# //// web_form.accept (rewire_connected_forms takes those). Nothing happens where the site keeps no forms.
import json
import re

import frappe

GUARDED = "neoffice_theme.website_messages.submit"
ENGLISH_ONLY = "btn.textContent = 'Sending…'"


def execute():
	from builder import site_forms
	from builder.site_ai.config import get_assistant_name

	if not site_forms.available() or not frappe.db.table_exists("Builder Client Script"):
		return
	rewritten = 0
	for name in frappe.get_all(
		"Builder Client Script", filters={"name": ["like", "Save % submissions"]}, pluck="name"
	):
		doc = frappe.get_doc("Builder Client Script", name)
		script = doc.script or ""
		if GUARDED not in script or ENGLISH_ONLY not in script:
			continue
		found = re.search(site_forms.SCRIPT_VALUES, script)
		if not found:
			frappe.log_error(
				f"Connected form words not rewritten: {name}"[:140], "The script has no values to read back."
			)
			continue
		doc.script = site_forms.guarded_form_script(
			json.loads(found["selector"]),
			json.loads(found["web_form"]),
			json.loads(found["fields"]),
			get_assistant_name(),
		)
		# save(), not db.set_value: the document's on_update writes the public .js file the page serves
		doc.save(ignore_permissions=True)
		rewritten += 1
	if rewritten:
		print(f"connected form(s) now speaking the page's language: {rewritten}")
