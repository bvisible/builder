#//// Neoffice — added file (no upstream equivalent): drops Builder Site Config; the brief now lives on
#//// Builder Chat Session. Neoffice migration, listed in patches.txt; frappe/builder has no equivalent.
#//// First commit 0bf5f370 2026-08-04.
# Builder Site Config held the AI's site plan — site type, colours, provider,
# and a design_brief_json — back when the generator wrote its state into its own
# doctype. That job moved to Builder Chat Session (`saved_brief`), which is what
# the generator writes today and what the "generate the remaining pages" flow
# and the visual loop read back.
#
# Nothing has referenced Builder Site Config since: no python, no vue, no
# fixture, no hook. It is the doctype and its child table sitting on rows
# nobody reads.
#
# The row count is logged before dropping, because a silent delete of a table
# somebody might remember is worse than a noisy one.
import frappe

DOCTYPES = ("Builder Site Config", "Builder Site Config Page")


def execute():
	dropped = []
	for doctype in DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue

		count = None
		try:
			count = frappe.db.count(doctype)
		except Exception:
			# table already gone, doctype record left behind
			pass

		dropped.append(f"{doctype}: {count if count is not None else 'no table'}")
		frappe.delete_doc("DocType", doctype, force=True, ignore_missing=True)

	if dropped:
		frappe.logger().info("dropped legacy AI site config doctypes — " + ", ".join(dropped))
		frappe.db.commit()
