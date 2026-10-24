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
from builder.ai.agent.selectors import walk_blocks  # //// Neoffice — see page_has_no_form

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
# //// leaves the site with two contact forms (2026-10-19). A form whose fields are an e-mail and a message is a contact
# //// form: it is declined with the way to the real one.
CONTACT_FORM_DECLINED = (
	"DECLINED: this is a CONTACT form, and the site already has one: the contact_form include, which posts, "
	"saves the message in the site's inbox (Website Messages) and notifies the owner. Do not build or connect "
	"your own: remove the form you drew, call get_site_chrome, and put the include on the page as a block whose "
	"`text` is its tag (the Shortcodes section of your instructions has the exact tags for a quote form, a "
	"window and the plain form). connect_form is for OTHER forms: booking, reservation, signup, waitlist, RSVP."
)


# //// Neoffice — words that make a form a booking or a registration, not a contact form: a date, a time, a number of
# //// people. A booking form carries a free "message" field as well; read as a contact form it was declined thirty-seven times
# //// in a row (2026-10-19) and the model never got its form connected. Whole words, except for the stems that cannot
# //// be taken for anything else: a quote form's "timeline" or a consent "checkbox" must not count.
BOOKING_WORDS = {
	"time",
	"hour",
	"heure",
	"heures",
	"day",
	"jour",
	"horaire",
	"slot",
	"slots",
	"seat",
	"seats",
	"party",
	"table",
	"tables",
	"nuit",
	"nuits",
	"night",
	"nights",
	"people",
	"depart",
	"d\u00e9part",
	"departure",
}
BOOKING_STEMS = ("date", "guest", "person", "cr\u00e9neau", "creneau", "invit", "arriv")


def looks_like_contact_form(fields) -> bool:
	"""Whether the fields are those of a contact form: an e-mail and a message, and nothing that books a time or
	a number of places."""
	# //// Neoffice — see BOOKING_WORDS
	names = " ".join(
		f"{f.get('fieldname', '')} {f.get('label', '')}".lower()
		for f in (fields or [])
		if isinstance(f, dict)
	)
	tokens = [t for t in re.split(r"[^a-z\u00e0-\u00ff]+", names) if t]
	if any(t in BOOKING_WORDS or t.startswith(BOOKING_STEMS) for t in tokens):
		return False
	return "mail" in names and any(
		w in names for w in ("message", "msg", "comment", "question", "request", "demande", "devis")
	)


# //// Neoffice — connect_form on a page that holds no form (2026-10-19). Asked for a booking form, the local
# //// model called connect_form straight away: the card offered to create a DocType and wire a form that was
# //// never drawn. The tree of the turn is checked, and a page with no input is sent back to draw the form first.
FORM_ELEMENTS = {"form", "input", "textarea", "select"}
NO_FORM_ON_PAGE = (
	"DECLINED: this page has no form to connect: no form, input, textarea or select block. Draw the form FIRST "
	'with add_block (the whole section in ONE call, every input carrying name="<fieldname>"), then call '
	"connect_form for it."
)


def page_has_no_form(ctx) -> bool:
	"""True when the working tree of the turn is known and holds nothing a visitor could type in. A block that
	is an instance of a component is not looked into: the form may live inside it."""
	root = ctx.page_root() if hasattr(ctx, "page_root") else None
	if not isinstance(root, dict):
		return False
	for block, _ in walk_blocks(root):
		if block.get("element") in FORM_ELEMENTS or block.get("extendedFromComponent"):
			return False
	return True


def missing_create_permission(doctype: str) -> str | None:
	"""What connecting a form to `doctype` would create that this user can't. Only
	Website Manager holds Web Form create, but whoever can create DocTypes can grant
	themselves any role, so either one may create the form."""
	can_create_doctype = frappe.has_permission("DocType", "create")
	if not frappe.db.exists("DocType", doctype) and not can_create_doctype:
		return "create the DocType a form saves to"
	if not frappe.db.exists("Web Form", desk_slug(doctype)) and not (
		can_create_doctype or frappe.has_permission("Web Form", "create")
	):
		return "create the Web Form a form submits through"
	return None


def request_connect_form(ctx, args: dict) -> str | None:
	"""Validate the proposal and raise the confirm card. Nothing is created until
	the user approves (see pending.apply_connect_form)."""
	if not getattr(ctx, "page_id", None):
		return "DECLINED: no page is open — build the form's page first."
	# //// Neoffice — a contact form is the site's include, never a connected DocType (2026-10-19)
	if looks_like_contact_form(args.get("fields")):
		return CONTACT_FORM_DECLINED
	# //// Neoffice — nothing to connect on a page without a form (see NO_FORM_ON_PAGE)
	if page_has_no_form(ctx):
		return NO_FORM_ON_PAGE
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
	if action := missing_create_permission(doctype):
		return pending.not_permitted(action)
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
