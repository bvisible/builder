# //// Neoffice — added file (no upstream equivalent): row of the plugin registry — an app installed but
# //// switched off. Neoffice DocType, no upstream counterpart. First commit 45e67b23 2026-08-04.
import frappe
from frappe.model.document import Document

from builder import plugins


def _forget_state():
	# the route guard reads this on every request from cache
	plugins.clear_cache()
	frappe.cache().delete_value("unpress_plugin_blocked_routes")


class WebsitePlugin(Document):
	def on_update(self):
		_forget_state()
		# Again once the switch is committed: a request served between this save and its commit
		# read the registry as it still was, and put the old state back in the cache for good.
		# Measured on osiris (2026-10-07): the jobs plugin switched off, /jobs still answered 200.
		frappe.db.after_commit.add(_forget_state)
		# a plugin that just took over (or released) a public route changes what
		# the site serves
		frappe.clear_cache()

	def on_trash(self):
		_forget_state()
		frappe.db.after_commit.add(_forget_state)
