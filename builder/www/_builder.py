import frappe
from frappe.integrations.frappe_providers.frappecloud_billing import is_fc_site
from frappe.pulse.utils import get_app_version
from frappe.translate import get_translations_from_apps, get_user_translations
from frappe.utils.telemetry import capture

from builder.hooks import builder_path

no_cache = 1


def get_context(context):
	# //// Neoffice — the shell is for people who may author pages. Upstream serves it to any
	# //// signed-in user and lets the router alert() "no permission" and send them to /app:
	# //// for a portal customer (no desk) that is a modal dead end ending on "Not permitted".
	# //// Refused here instead, on the same source of truth as require_builder_role (the
	# //// Builder Page write permission): frappe renders its 403 page. A Guest goes straight
	# //// to the login page the router would have sent them to, without loading the app.
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = f"/login?redirect-to=/{builder_path}"
		raise frappe.Redirect
	if not frappe.has_permission("Builder Page", "write"):
		raise frappe.PermissionError(frappe._("You do not have permission to use the site builder"))
	csrf_token = frappe.sessions.get_csrf_token()
	frappe.db.commit()
	context.csrf_token = csrf_token
	context.site_name = frappe.local.site
	context.builder_path = builder_path
	context.builder_version = get_app_version("builder")
	# developer mode
	context.is_developer_mode = frappe.conf.developer_mode
	context.is_fc_site = is_fc_site()
	context.is_read_only_mode = bool(frappe.flags.read_only)
	context.boot = get_boot()
	if frappe.session.user != "Guest":
		capture("active_site", "builder")


def get_boot() -> dict:
	# only Builder's own catalog, the editor never looks up another app's strings
	lang = frappe.local.lang
	messages = get_translations_from_apps(lang, ["builder"])
	messages.update(get_user_translations(lang) or {})
	# //// Neoffice — the assistant's name and what this instance allows (managed models, tools
	# //// kept off, Users tab) ride the boot so a registry condition can read them at module load,
	# //// before any request. See builder/site_ai/capabilities.py and builder/plugins.py.
	from builder.plugins import get_capabilities
	from builder.site_ai.capabilities import ai_capabilities

	return {
		"translated_messages": messages,
		"assistant_name": ai_capabilities()["assistant_name"],
		"capabilities": {**get_capabilities(), "ai": ai_capabilities()},
	}
