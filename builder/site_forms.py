# //// Neoffice — added file (no upstream equivalent): the forms of the website, as the Builder reaches them.
# ////
# //// A `Site Form` is a record of the neoffice_theme app: the questions of a form, how it is shown, who is told
# //// (neoffice-maintenance#1593, plan of 20.10.2026). The theme owns the doctype and every rule about it
# //// (neoffice_theme/site_forms.py); the Builder draws a form in its include, lists, creates and changes forms
# //// in its editor, and lets its assistant and its site generator do the same, all through the functions the
# //// theme exports.
# ////
# //// Unpress (frappe 16) shares this code base WITHOUT the theme, so the capability is an answer of the server,
# //// never a fork: `available()` is False there, the editor's panel says nothing about forms, the include falls
# //// back on the plain contact form, and no endpoint of this module fails for want of the theme.
# ////
# //// To remove: nothing, there is no upstream counterpart.

import importlib

import frappe
from frappe import _

THEME = "neoffice_theme"
DOCTYPE = "Site Form"


def theme_module():
	"""neoffice_theme.site_forms when the theme that keeps forms is installed on this site, else None."""
	if THEME not in frappe.get_installed_apps():
		return None
	try:
		return importlib.import_module(f"{THEME}.site_forms")
	except ImportError:
		# a theme that predates the forms
		return None


def available() -> bool:
	"""Whether this site keeps forms: the theme is installed, is recent enough, and has migrated. Asked once per
	request."""
	cached = getattr(frappe.local, "builder_site_forms_available", None)
	if cached is None:
		cached = bool(theme_module() and frappe.db.table_exists(DOCTYPE))
		frappe.local.builder_site_forms_available = cached
	return cached


def site_form_definition(name: str | None = None) -> dict | None:
	"""What the include `site_form.html` draws for form `name`: the questions and how they are shown, or None when
	there is nothing to draw (no theme, not migrated yet, no form): the include then draws the plain contact form.

	Called by Jinja at EVERY display of a page, so an improvement of the forms reaches the sites already online.
	Never raises: a page must not lose its content over a form."""
	if not available():
		return None
	try:
		return theme_module().public_definition(name)
	except Exception:
		frappe.log_error("Site form: the definition could not be read", frappe.get_traceback())
		return None


def form_choices() -> list[dict]:
	"""The forms of this site as the choices of the `site_form` option of the include: [{value, label}].
	A form of a website says which one in its label when the instance serves several."""
	if not available():
		return []
	try:
		rows = theme_module().list_forms()
	except Exception:
		return []
	several = len({row.get("profile") or "" for row in rows}) > 1
	return [
		{
			"value": row["name"],
			"label": f"{row['title']} ({row['profile']})" if several and row.get("profile") else row["title"],
		}
		for row in rows
		if row.get("enabled")
	]


# -- what the editor of the Builder calls (builder/api.py wraps each one in the builder-role gate) ----------------


def _require():
	module = theme_module()
	if module is None or not frappe.db.table_exists(DOCTYPE):
		frappe.throw(_("Forms are not available on this site."))
	return module


def editor_state(page: str | None = None, website_profile: str | None = None) -> dict:
	"""The forms for the open page, and the presets a new one can start from. {"available": False} where the
	site keeps no forms (Unpress, a theme that predates them): the editor then shows nothing about forms."""
	if not available():
		return {"available": False}
	from builder.site_ai.nora.prompts import page_profile

	module = theme_module()
	profile = website_profile or page_profile(page)
	try:
		forms = module.list_forms(profile)
	except frappe.PermissionError:
		forms = []
	return {
		"available": True,
		"website_profile": profile or "",
		"forms": forms,
		"presets": module.presets(module.language_of(profile)),
		"kinds": list(module.KINDS),
		"field_types": list(module.FIELD_TYPES),
		"limits": {
			"fields": module.MAX_FIELDS,
			"steps": module.MAX_STEPS,
			"choices": module.MAX_CHOICES,
		},
	}


def get_form(name: str) -> dict:
	return _require().get_form(name)


def create_form(
	preset: str = "steps",
	title: str | None = None,
	website_profile: str | None = None,
	kind: str | None = None,
) -> dict:
	return _require().create_form(title=title, preset=preset, profile=website_profile or None, kind=kind)


def save_form(name: str, data: dict) -> dict:
	return _require().save_form(name, data)


def change_form(name: str, changes: dict) -> dict:
	"""Changes form `name` by operations (add_questions, remove_questions, title, success_message...). The theme
	holds the result to every rule of a form at save; a refusal is a sentence."""
	return _require().change_form(name, changes)


def forms_for_assistant(profile: str | None = None) -> list[dict]:
	"""The forms of the site as the assistant reads them: name, title, kind, whether it is on, and its questions
	(label, type, required, choices). No recipient: the assistant has no use for who is told."""
	module = _require()
	out = []
	for row in module.list_forms(profile):
		definition = module.get_form(row["name"])
		out.append(
			{
				"name": definition["name"],
				"title": definition["title"],
				"kind": definition["kind"],
				"enabled": bool(definition["enabled"]),
				"steps": definition["steps"],
				"window": bool(definition["dialog"]),
				"questions": [
					{
						key: value
						for key, value in {
							"label": field["label"],
							"identifier": field["fieldname"],
							"type": field["type"],
							"required": bool(field["required"]),
							"step": field["step"],
							"choices": field["options"] or None,
						}.items()
						if value not in (None, [])
					}
					for field in definition["fields"]
				],
			}
		)
	return out
