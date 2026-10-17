# //// Neoffice — added file (no upstream equivalent): drops the three upstream form block templates.
# //// Neoffice migration, listed in patches.txt; frappe/builder has no equivalent.
# ////
# //// Form 1, Form 2 and Form 3 are markup and nothing else: their <form> carries no action and no
# //// method, so a visitor fills one in, presses the button, and the page reloads having sent
# //// nothing. They sat in categories our editor panel no longer draws, which hid the trap instead
# //// of removing it: one category fix would have put a dead contact form one click away, and within
# //// the site generator's reach.
# //// What replaces them: contact_form_simple, contact_form_steps and contact_form_questions, which
# //// post to neoffice_theme.website_messages.submit (neoffice-maintenance#1593, Jérémy 17.10:
# //// « enlever ce qui est légacy [...] de plus avoir des anciens formulaires de contact »).
# //// A block template is COPIED into a page when it is dropped: removing it changes no page that
# //// already carries one.
import frappe

LEGACY = ("Form 1", "Form 2", "Form 3")


def execute():
	for name in LEGACY:
		if frappe.db.exists("Block Template", name):
			frappe.delete_doc("Block Template", name, force=True, ignore_permissions=True)
			print(f"dropped the legacy block template {name}")
