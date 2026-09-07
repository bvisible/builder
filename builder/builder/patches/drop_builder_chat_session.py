# //// Neoffice — added file (no upstream equivalent): drops Builder Chat Session and
# //// Builder Chat Message, the conversation doctypes of the pre-1.33 site generator.
# The chat that collected the brief now runs in upstream's Builder AI Session /
# Builder AI Message (page-scoped, one per page of the editor); the brief the
# generator writes lives on the site chrome (`ai_brief`), the generation status
# in the cache under its job id, and the client documents keep their
# `session_id` on Builder Content Asset (a Data field, now the AI session name).
#
# Nothing reads these two tables any more: no python, no vue, no fixture, no
# hook (the stuck-generation watchdog went with them). The row counts are
# logged before the drop, as for Builder Site Config before them.
import frappe

DOCTYPES = ("Builder Chat Message", "Builder Chat Session")


def execute():
	dropped = []
	for doctype in DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue
		count = None
		try:
			count = frappe.db.count(doctype)
		except Exception:
			pass
		dropped.append(f"{doctype}: {count if count is not None else 'no table'}")
		frappe.delete_doc("DocType", doctype, force=True, ignore_missing=True)
	if dropped:
		frappe.logger().info("dropped legacy AI chat doctypes — " + ", ".join(dropped))
		frappe.db.commit()
