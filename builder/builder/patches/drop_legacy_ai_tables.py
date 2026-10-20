# //// Neoffice — added file (no upstream equivalent): drops the five tables the legacy-AI drop patches left behind.
# //// Neoffice migration, listed in patches.txt; frappe/builder has no equivalent. First commit 2026-10-20.
#
# `drop_builder_chat_session`, `drop_builder_site_config` and the `execute:` line that removed Builder Page Library said
# "dropped" and logged their row counts, but `frappe.delete_doc("DocType", ...)` removes the DocType record and not its
# table. Measured on osiris on 2026-10-20: `tabBuilder Chat Session` (50 rows), `tabBuilder Chat Message` (253),
# `tabBuilder Site Config`, `tabBuilder Site Config Page` and `tabBuilder Page Library` (empty) were all still there, with
# no DocType to open them. They are the conversations and the site plans of the pre-1.33 generator; nothing reads them (no
# python, no vue, no fixture, no hook), the chat that replaced them lives in Builder AI Session and Builder AI Message, and
# the brief lives on the site chrome.
#
# Jérémy decided on 2026-10-20 to drop them, after the row count is journaled. drop() (drop_builder_ai_shortcode) says how
# many rows each held, before the drop, in sites/<site>/logs/dropped-tables.log and in the migrate output, then removes the table; a site where an earlier patch already removed a table
# or never had one is left alone.
import frappe

from builder.builder.patches.drop_builder_ai_shortcode import drop

DOCTYPES = (
	"Builder Chat Message",
	"Builder Chat Session",
	"Builder Site Config Page",
	"Builder Site Config",
	"Builder Page Library",
)


def execute():
	if drop(DOCTYPES):
		frappe.db.commit()
