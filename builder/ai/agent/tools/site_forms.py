"""//// Neoffice — added file (no upstream equivalent): the assistant creates and changes the forms of the website.

A form of the site is a record of the theme (`Site Form`, see builder/site_forms.py), not markup: "add a question
about the surface of the premises to my quote form" is a change of that record, not a rewrite of the page. Three
tools, none of which touches a page:

  * `list_site_forms` (read): the forms and their questions, so the assistant picks the right form;
  * `create_site_form` (confirm card): a new form from a preset, with the questions the user asked for;
  * `update_site_form` (confirm card): add or remove questions, or change how the form is shown.

The two writers are `terminal` tools like `connect_form`: the model proposes, the user applies on a card, and the
write runs as the user (the theme checks their right on the doctype). Where the site keeps no forms (Unpress, a
theme that predates them) the registry does not offer them at all (registry.build_default_registry).

To remove: nothing, there is no upstream counterpart."""

import json

import frappe
from frappe import _

from builder.ai.agent import pending
from builder.ai.agent.registry import Tool

# the names a model may use for a question's type; the theme reads more (normalise_type) and refuses the rest
QUESTION_TYPES = ["text", "long_text", "email", "phone", "single_choice", "checkboxes", "date", "consent"]
MAX_QUESTIONS_PER_CALL = 12

QUESTION_SCHEMA = {
	"type": "object",
	"properties": {
		"label": {
			"type": "string",
			"description": "The question as the visitor reads it, in the language of the site.",
		},
		"type": {"type": "string", "enum": QUESTION_TYPES, "description": "Default text."},
		"options": {
			"type": "array",
			"items": {"type": "string"},
			"description": "For single_choice and checkboxes: the choices, at least two.",
		},
		"required": {"type": "boolean"},
		"help": {"type": "string", "description": "A hint shown with the question. Optional."},
		"step": {
			"type": "integer",
			"description": "Only on a form in steps: the step it is asked in. Default: the step of the message.",
		},
	},
	"required": ["label"],
}


def _profile(ctx):
	from builder.site_ai.nora.prompts import page_profile

	return page_profile(getattr(ctx, "page_id", None)) or None


def _questions(args: dict, key: str):
	"""The questions a call carries, or an error sentence."""
	raw = args.get(key) or []
	if not isinstance(raw, list) or any(not isinstance(item, dict) for item in raw):
		return None, f"DECLINED: {key} is a list of {{label, type, options, required}}."
	if len(raw) > MAX_QUESTIONS_PER_CALL:
		return None, f"DECLINED: at most {MAX_QUESTIONS_PER_CALL} questions in one call."
	return raw, None


def run_list_site_forms(ctx, args: dict) -> str:
	from builder import site_forms

	if not site_forms.available():
		return "This site keeps no forms."
	try:
		forms = site_forms.forms_for_assistant(_profile(ctx))
	except frappe.PermissionError:
		return "FAILED: you do not have permission to read the forms of this site."
	if not forms:
		return "No form yet: create_site_form makes one."
	return json.dumps({"forms": forms}, ensure_ascii=False)


def _describe(questions: list[dict]) -> str:
	return "; ".join(str(q.get("label") or "?").strip() for q in questions)


def request_create_site_form(ctx, args: dict) -> str | None:
	"""Validate the proposal and raise the confirm card. Nothing is created until the user applies it."""
	from builder import site_forms

	if not site_forms.available():
		return "DECLINED: this site keeps no forms."
	preset = (args.get("preset") or "steps").strip()
	if preset not in ("simple", "steps", "questions"):
		return 'DECLINED: preset is "simple" (name, e-mail, message), "steps" (the same, one question at a time) or "questions" (what the request is about, the budget and the timing first).'
	questions, error = _questions(args, "questions")
	if error:
		return error
	title = (args.get("title") or "").strip()
	summary = _("Create the form “{0}” ({1})?").format(title or _("New form"), _(preset))
	if questions:
		summary += " " + _("With these questions added: {0}.").format(_describe(questions))
	pending.request_confirmation(
		ctx,
		"create_site_form",
		summary,
		{"preset": preset, "title": title, "questions": questions, "website_profile": _profile(ctx) or ""},
	)
	return None


def request_update_site_form(ctx, args: dict) -> str | None:
	"""Validate the proposal and raise the confirm card. Nothing changes until the user applies it."""
	from builder import site_forms

	if not site_forms.available():
		return "DECLINED: this site keeps no forms."
	name = (args.get("form") or "").strip()
	if not name or not frappe.db.exists(site_forms.DOCTYPE, name):
		return "DECLINED: pass `form`, the name of a form exactly as list_site_forms gives it."
	if not frappe.has_permission(site_forms.DOCTYPE, "write", doc=name):
		return "DECLINED: you do not have permission to change this form."
	adds, error = _questions(args, "add_questions")
	if error:
		return error
	removes = [str(item).strip() for item in (args.get("remove_questions") or []) if str(item).strip()]
	settings = {
		key: args[key]
		for key in (
			"title",
			"success_message",
			"button_text",
			"submit_text",
			"dialog",
			"enabled",
			"recipients",
		)
		if key in args and args[key] is not None
	}
	if not (adds or removes or settings):
		return "DECLINED: nothing to change: pass add_questions, remove_questions or a setting."

	title = frappe.db.get_value(site_forms.DOCTYPE, name, "title") or name
	parts = []
	if adds:
		parts.append(_("add: {0}").format(_describe(adds)))
	if removes:
		parts.append(_("remove: {0}").format("; ".join(removes)))
	if settings:
		parts.append(_("change: {0}").format(", ".join(sorted(settings))))
	pending.request_confirmation(
		ctx,
		"update_site_form",
		_("Change the form “{0}”? {1}.").format(title, " — ".join(parts)),
		{"form": name, "add_questions": adds, "remove_questions": removes, "settings": settings},
	)
	return None


list_site_forms_tool = Tool(
	name="list_site_forms",
	side="server",
	description=(
		"List the forms of this site (contact, quote request, call back...) with their questions: the form's `name`, "
		"its title and kind, and each question's label, identifier, type, whether it is required, its choices. Read "
		"it BEFORE changing a form, to pick the right one by its title or kind and to know what it already asks."
	),
	parameters={"type": "object", "properties": {}},
	handler=run_list_site_forms,
)

create_site_form_tool = Tool(
	name="create_site_form",
	side="terminal",
	description=(
		"Create a NEW form for the site from a preset: simple (name, e-mail, message), steps (the same, one "
		"question at a time) or questions (what the request is about, the budget and the timing before the message: "
		"for a business that quotes). Add the questions the user asked for in `questions`. It does not put the form "
		"on a page: afterwards the page carries it as a block whose text is the include of the form with its name. "
		"Use it only when the user wants ANOTHER form (a call-back form, a quote form beside the contact form); to "
		"add a question to a form that exists, call update_site_form. Ends your turn to confirm."
	),
	parameters={
		"type": "object",
		"properties": {
			"preset": {"type": "string", "enum": ["simple", "steps", "questions"]},
			"title": {"type": "string", "description": "The name of the form, e.g. 'Request a call back'."},
			"questions": {
				"type": "array",
				"description": "Questions to add to the preset's own.",
				"items": QUESTION_SCHEMA,
			},
		},
		"required": ["preset"],
	},
	handler=request_create_site_form,
)

update_site_form_tool = Tool(
	name="update_site_form",
	side="terminal",
	description=(
		"Change a form that exists: add questions, take questions out, or change how it is shown (title, the message "
		"once sent, the button, whether it opens in a window, the send button, the addresses told). A new question "
		"goes before the message, in its step. The e-mail question cannot be removed. Call list_site_forms first for "
		"the form's `name` and its questions. This is how 'add a question about X to the quote form' is done: never "
		"by rewriting the page. Ends your turn to confirm."
	),
	parameters={
		"type": "object",
		"properties": {
			"form": {
				"type": "string",
				"description": "The form's name, exactly as list_site_forms gives it.",
			},
			"add_questions": {"type": "array", "items": QUESTION_SCHEMA},
			"remove_questions": {
				"type": "array",
				"items": {"type": "string"},
				"description": "Questions to remove, by identifier or label.",
			},
			"title": {"type": "string"},
			"success_message": {
				"type": "string",
				"description": "What the visitor reads once the message is sent.",
			},
			"button_text": {
				"type": "string",
				"description": "For a form in a window: what the button reads.",
			},
			"submit_text": {"type": "string", "description": "What the send button reads."},
			"dialog": {"type": "boolean", "description": "The form waits in a window a button opens."},
			"enabled": {"type": "boolean"},
			"recipients": {"type": "string", "description": "E-mail addresses told, separated by commas."},
		},
		"required": ["form"],
	},
	handler=request_update_site_form,
)

TOOLS = [list_site_forms_tool, create_site_form_tool, update_site_form_tool]
NAMES = frozenset(tool.name for tool in TOOLS)
