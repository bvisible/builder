# Homepage handler — dynamic home page resolution
import frappe

no_cache = 1


def get_home_page(user=None):
	"""Called by Frappe's get_home_page hook.
	Returns the route of the Builder homepage if it exists,
	otherwise returns 'index' to show the under-construction page."""
	builder_home = frappe.db.get_value(
		"Builder Page",
		{"route": "home", "published": 1},
		"name"
	)
	if builder_home:
		return "home"
	return "index"


def get_context(context):
	context.no_cache = 1
