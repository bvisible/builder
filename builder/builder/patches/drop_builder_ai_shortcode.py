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
# might remember is worse than a noisy one. A site that never had the table is left alone. Unlike them, this one drops the
# table: see drop().
import frappe

DOCTYPES = ("Builder AI Shortcode",)


def drop(doctypes) -> dict[str, int | None]:
	"""Drop each DocType that exists, with its rows and its table, and say how many rows it held (None: no table).

	`frappe.delete_doc("DocType", ...)` removes the DocType record and NOT its table: the patches that dropped the legacy chat,
	site config and page library doctypes left `tabBuilder Chat Session`, `tabBuilder Chat Message`, `tabBuilder Site Config`,
	`tabBuilder Site Config Page` and `tabBuilder Page Library` on osiris, full, with no DocType to open them. This one drops
	the table too, because dropping the rows is the point. A table whose DocType record is already gone is dropped as well."""
	dropped: dict[str, int | None] = {}
	for doctype in doctypes:
		record = frappe.db.exists("DocType", doctype)
		table = frappe.db.table_exists(doctype)
		if not record and not table:
			continue
		count = None
		if table:
			# the names are this module's constants, never data
			count = frappe.db.sql(f"select count(*) from `tab{doctype}`")[0][0]
		dropped[doctype] = count
		if record:
			frappe.delete_doc("DocType", doctype, force=True, ignore_missing=True, ignore_permissions=True)
		frappe.db.sql_ddl(f"drop table if exists `tab{doctype}`")
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
