# //// Neoffice — added file (no upstream equivalent): row of the plugin registry — an app installed but
# //// switched off. Neoffice DocType, no upstream counterpart. First commit 45e67b23 2026-08-04.
import frappe
from frappe.model.document import Document

from builder import plugins


class WebsitePlugin(Document):
	def on_update(self):
		# the route guard reads this on every request from cache
		plugins.clear_cache()
		frappe.cache().delete_value("unpress_plugin_blocked_routes")
		# a plugin that just took over (or released) a public route changes what
		# the site serves
		frappe.clear_cache()

	def on_trash(self):
		plugins.clear_cache()
		frappe.cache().delete_value("unpress_plugin_blocked_routes")
