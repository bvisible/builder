# Homepage handler — redirects to Builder homepage or shows under construction
import frappe

no_cache = 1


def get_context(context):
	context.no_cache = 1

	# If a published Builder Page with route "home" exists, redirect to it
	builder_home = frappe.db.get_value(
		"Builder Page",
		{"route": "home", "published": 1},
		"name"
	)
	if builder_home:
		frappe.flags.redirect_location = "/home"
		raise frappe.Redirect
