# //// Neoffice — added file (no upstream equivalent): sends the forms the assistant connected through the site's one door.
# //// Neoffice migration, listed in patches.txt; frappe/builder has no equivalent.
# ////
# //// A booking or sign-up form made by connect_form posted its fields to Frappe's own web_form.accept, open to every
# //// guest at ten requests a minute with no token, no decoy field, no held-back mail: far less protected than the
# //// contact form (neoffice-maintenance#1593, plan of 20.10.2026). New ones are written with the guarded script
# //// (builder.site_forms.guarded_form_script). This rewrites the ones that exist: the same form, the same table,
# //// the same selector and fields, read back from the old script.
# ////
# //// Idempotent: a script already guarded is left alone. Nothing happens where the site keeps no forms (Unpress, a
# //// theme that predates them): the old script is all there is to send them through there.
import json
import re

import frappe


def execute():
	from builder import site_forms
	from builder.site_ai.config import get_assistant_name

	if not site_forms.available() or not frappe.db.table_exists("Builder Client Script"):
		return
	rewired = 0
	for name in frappe.get_all(
		"Builder Client Script", filters={"name": ["like", "Save % submissions"]}, pluck="name"
	):
		doc = frappe.get_doc("Builder Client Script", name)
		script = doc.script or ""
		if "web_form.web_form.accept" not in script:
			continue
		found = re.search(site_forms.SCRIPT_VALUES, script)
		if not found:
			frappe.log_error(
				f"Connected form not rewired: {name}"[:140], "The script has no values to read back."
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
		rewired += 1
	if rewired:
		print(f"rewired {rewired} connected form(s) through the site's one door")
