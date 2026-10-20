# //// Neoffice — added file (no upstream equivalent): drops Builder AI Shortcode, a child table with no parent.
# //// Neoffice migration, listed in patches.txt; frappe/builder has no equivalent. First commit 2026-10-20.
#
# Builder AI Shortcode was the child table of Builder AI Settings, where an administrator described, for the
# generator, the includes a page could carry. `drop_ai_settings_doctype` (2026-04-18) removed the parents (AI Settings and
# Builder AI Settings) and left the child behind: a table nothing could open, because a child row is edited through its
# parent, and no DocType has had a Table field to it since. Measured on osiris on 2026-10-20: ten rows, nine under
# "Builder AI Settings" and one under "AI Settings", all of them includes the component catalogue now describes, or
# header pieces of the old by-blocks construction (cart icon, search box, menus). The only reader, the old generator's
# prompt (system_prompts.get_shortcodes_context), reads the catalogue instead (neoffice-maintenance#1593, 2026-10-20).
#
# What a page can carry is defined once, in code (site_ai/components.py); the Builder Shortcode registry is its mirror.
#
# The row count is logged before the drop, as for the legacy AI doctypes before it: a silent delete of a table somebody
# might remember is worse than a noisy one. A site that never had the table is left alone.
import frappe

DOCTYPES = ("Builder AI Shortcode",)


def drop(doctypes) -> dict[str, int | None]:
	"""Drop each DocType that exists, with its table, and say how many rows it held (None: the table was already gone)."""
	dropped: dict[str, int | None] = {}
	for doctype in doctypes:
		if not frappe.db.exists("DocType", doctype):
			continue
		count = None
		try:
			count = frappe.db.count(doctype)
		except Exception:
			# the table is already gone, the doctype record was left behind
			pass
		dropped[doctype] = count
		frappe.delete_doc("DocType", doctype, force=True, ignore_missing=True, ignore_permissions=True)
	return dropped


def execute():
	dropped = drop(DOCTYPES)
	if dropped:
		frappe.logger().info(
			"dropped the orphan AI shortcode table — "
			+ ", ".join(
				f"{doctype}: {count if count is not None else 'no table'}"
				for doctype, count in dropped.items()
			)
		)
		frappe.db.commit()
