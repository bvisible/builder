"""Connect a page form to real data — the 'make this form actually save' tool.

A form on a published Builder page is public (a guest fills it), so it can't
insert into a DocType directly. The safe, code-free path is Frappe's built-in
Web Form: its `accept` endpoint is guest-allowed, rate-limited, field-whitelisted,
and inserts with ignore_permissions — the Web Form is the trusted boundary, so
the submission DocType needs NO guest permission.

`connect_form` (confirm-gated) provisions the whole chain on approval:
  1. a private submission DocType (System Manager only — no guest read),
  2. a Web Form bound to it (login_required off, published),
  3. a page client script that POSTs the form's fields to the accept endpoint.
The user then reads submissions in Desk at /app/<doctype>.
"""

import re

import frappe
from frappe.model import child_table_fields, default_fields

from builder.ai.agent import pending
from builder.ai.agent.registry import Tool

# Fieldtypes a public form can safely write. Anything else (Link, Table, Attach…)
# is coerced to Data. Select is deliberately EXCLUDED: an HTML <select> submits its
# option's `value` attr (e.g. "breathwork"), which rarely matches the DocType's
# Select option labels ("Breathwork & Stillness") — Frappe then rejects the insert
# with a validation error. Storing dropdowns as Data accepts whatever was chosen.
SAFE_FIELDTYPES = {"Data", "Small Text", "Text", "Int", "Float", "Check", "Date", "Datetime"}

# Fieldnames Frappe reserves (every doc has `name`, `owner`, `parent`, …). A form
# input called "name" would otherwise crash DocType creation ("Fieldname name is
# restricted"), so the DocType field is renamed (`name` → `name_field`) while the
# input keeps its own name attribute — the wiring script maps between them.
RESERVED_FIELDNAMES = (
	set(default_fields)
	| set(child_table_fields)
	| {
		"name",
		"parent",
		"idx",
		"naming_series",
		"amended_from",
		"workflow_state",
	}
)


def safe_fieldname(fieldname: str) -> str:
	return f"{fieldname}_field" if fieldname in RESERVED_FIELDNAMES else fieldname


def connected_submission_doctype(page_id: str) -> str | None:
	"""The submission DocType a form on this page already saves to, if any — read
	from the attached 'Save <doctype> submissions' client script. Lets a "where do
	my submissions go?" question be answered instead of creating a duplicate."""
	if not page_id or not frappe.db.exists("Builder Page", page_id):
		return None
	names = frappe.get_all(
		"Builder Page Client Script",
		filters={"parent": page_id, "parenttype": "Builder Page"},
		pluck="builder_script",
	)
	for name in names:
		m = re.match(r"^Save (.+) submissions$", name or "")
		if m and frappe.db.exists("DocType", m.group(1)):
			return m.group(1)
	return None


# //// Neoffice — the contact form is ONE include of the site (builder/templates/includes/contact_form.html): it posts
# //// to the site's own entry point, saves the message in the inbox and notifies the owner. Asked to "add a contact
# //// form", a weaker model drew its own <form> and called connect_form for it, which opens a DocType nobody reads and
# //// leaves the site with two contact forms (2026-10-20). A form whose fields are an e-mail and a message is a contact
# //// form: it is declined with the way to the real one.
CONTACT_FORM_DECLINED = (
	"DECLINED: this is a CONTACT form, and the site already has one: the contact_form include, which posts, "
	"saves the message in the site's inbox (Website Messages) and notifies the owner. Do not build or connect "
	"your own: remove the form you drew, call get_site_chrome, and put the include on the page as a block whose "
	"`text` is its tag (the Shortcodes section of your instructions has the exact tags for a quote form, a "
	"window and the plain form). connect_form is for OTHER forms: booking, reservation, signup, waitlist, RSVP."
)


def looks_like_contact_form(fields) -> bool:
	"""Whether the fields are those of a contact form: an e-mail and a message."""
	names = " ".join(
		f"{f.get('fieldname', '')} {f.get('label', '')}".lower() for f in (fields or []) if isinstance(f, dict)
	)
	return "mail" in names and any(w in names for w in ("message", "msg", "comment", "question", "request", "demande", "devis"))


def request_connect_form(ctx, args: dict) -> str | None:
	"""Validate the proposal and raise the confirm card. Nothing is created until
	the user approves (see pending.apply_connect_form)."""
	if not getattr(ctx, "page_id", None):
		return "DECLINED: no page is open — build the form's page first."
	# //// Neoffice — a contact form is the site's include, never a connected DocType (2026-10-20)
	if looks_like_contact_form(args.get("fields")):
		return CONTACT_FORM_DECLINED
	# A form here is already wired — very likely a "where do submissions go?" ask.
	# Answer with the existing DocType; don't create a duplicate (unless forced).
	if not args.get("force_new") and (connected := connected_submission_doctype(ctx.page_id)):
		return (
			f"ALREADY CONNECTED: a form on this page saves to the '{connected}' DocType — its "
			f"submissions are in Desk at /app/{desk_slug(connected)}. Do NOT create a new doctype; "
			f"just tell the user where to find the entries (give that link). Only pass force_new=true "
			f"if they explicitly want a SEPARATE, additional form."
		)
	doctype = (args.get("doctype_name") or "").strip()
	fields = [f for f in (args.get("fields") or []) if isinstance(f, dict) and f.get("fieldname")]
	selector = (args.get("form_selector") or "").strip()
	if not doctype or not fields or not selector:
		return (
			"DECLINED: connect_form needs doctype_name, at least one field, and form_selector "
			'(the CSS selector of the <form> or its container — set name="<fieldname>" on each input first).'
		)
	if frappe.db.exists("DocType", doctype) and not is_builder_submission_doctype(doctype):
		return (
			f"DECLINED: '{doctype}' already exists and isn't a Builder submission doctype — pick a new "
			f"name (e.g. '{doctype} Submission') so real data isn't touched."
		)
	summary = (
		f"Create the DocType '{doctype}' ({len(fields)} field(s)) and wire this form to save "
		f"submissions to it? You'll see entries in Desk at /app/{desk_slug(doctype)}."
	)
	payload = {
		"doctype_name": doctype,
		"fields": [normalize_field(f) for f in fields],
		"page_id": ctx.page_id,
		"form_selector": selector,
	}
	pending.request_confirmation(ctx, "connect_form", summary, payload)
	return None


def normalize_field(f: dict) -> dict:
	fieldtype = f.get("fieldtype") if f.get("fieldtype") in SAFE_FIELDTYPES else "Data"
	input_name = frappe.scrub(f["fieldname"])  # the form input's `name` attribute
	out = {
		"input_name": input_name,
		"fieldname": safe_fieldname(input_name),  # DocType fieldname (reserved names remapped)
		"label": f.get("label") or f["fieldname"].replace("_", " ").title(),
		"fieldtype": fieldtype,
	}
	if fieldtype == "Select" and f.get("options"):
		out["options"] = f["options"]
	return out


def is_builder_submission_doctype(name: str) -> bool:
	row = frappe.db.get_value("DocType", name, ["custom", "module"], as_dict=True)
	return bool(row and row.custom and row.module == "Builder")


def desk_slug(doctype: str) -> str:
	return frappe.scrub(doctype).replace("_", "-")


connect_form_tool = Tool(
	name="connect_form",
	side="terminal",
	description=(
		"Make a form on the page actually SAVE its submissions to the database. Use this whenever "
		"you build a real form that collects user input (contact, booking, signup, waitlist, RSVP). "
		"Under the hood it creates a private DocType for the submissions, a guest-safe Web Form, and a "
		"script that sends the form's fields to it — the owner reads entries in Desk at /app/<doctype>. "
		"List `fields` in the SAME ORDER the inputs appear in the form (they map positionally); one field "
		"per input/select. `form_selector` is a best-effort hint — the tool auto-finds the form if it "
		"misses, so you need not pre-set name attributes or a class. Ends your turn to confirm."
	),
	parameters={
		"type": "object",
		"properties": {
			"doctype_name": {
				"type": "string",
				"description": "Human name for the submissions DocType, e.g. 'Stillpoint Reservation'.",
			},
			"fields": {
				"type": "array",
				"description": "One entry per form input. fieldname must equal the input's name attribute.",
				"items": {
					"type": "object",
					"properties": {
						"fieldname": {
							"type": "string",
							"description": "snake_case; equals the input's name attr.",
						},
						"label": {"type": "string"},
						"fieldtype": {
							"type": "string",
							"description": "Data (default), Small Text, Text, Int, Float, Check, Select, Date, Datetime.",
						},
						"options": {
							"type": "string",
							"description": "For Select: newline-separated choices.",
						},
					},
					"required": ["fieldname"],
				},
			},
			"form_selector": {
				"type": "string",
				"description": "CSS selector of the <form> or its container block, e.g. '.reservation-form'.",
			},
			"force_new": {
				"type": "boolean",
				"description": "Only set true to add a SEPARATE form when the page already has a connected one.",
			},
		},
		"required": ["doctype_name", "fields", "form_selector"],
	},
	handler=request_connect_form,
)

TOOLS = [connect_form_tool]
