# //// Neoffice — added file (no upstream equivalent): renders the generator's design brief readably
# //// instead of leaving it a JSON blob. Neoffice-only, part of the AI generator surface. First commit
# //// 0bf5f370 2026-08-04.
"""The design brief, readable.

The site pipeline writes its brief to the site chrome (`Website Header Footer Config.ai_brief`, or the profile's Variant) and reads
it back to generate the remaining pages and to run the visual loop. Until now
nobody could *see* it: a client asked "why is my site like this?" and the
answer sat in a JSON blob in a doctype the Studio hides.

Sixty-one fields dumped raw is not an answer either. This groups them the way
the decisions were actually made — the stance first, then colour, type, the
design system, the chrome, the rhythm — and drops anything the brief left
empty, so a short brief reads short.
"""

import json

import frappe
from frappe import _

ROLES = ("System Manager", "Website Manager")

# field -> label, in the order a person would want to read them. Anything not
# listed is deliberately not shown: the brief carries pixel values for every
# heading level, and a wall of "h3_line_height: 1.3" teaches nobody anything.
GROUPS = (
	(
		"The stance",
		(
			("design_concept", "Concept"),
			("signature_element", "Signature element"),
			("site_tone", "Tone"),
			("inspiration_context", "Inspiration"),
		),
	),
	(
		"Colour",
		(
			("primary_color", "Primary"),
			("primary_usage", "Primary is for"),
			("secondary_color", "Secondary"),
			("secondary_usage", "Secondary is for"),
			("heading_color", "Headings"),
			("body_color", "Body text"),
			("link_color", "Links"),
			("section_backgrounds", "Section backgrounds"),
			("colors_to_avoid", "Avoided"),
		),
	),
	(
		"Type",
		(
			("heading_font", "Headings"),
			("body_font", "Body"),
			("h1_size", "H1"),
			("h2_size", "H2"),
			("body_size", "Body size"),
		),
	),
	(
		"The design system",
		(
			("border_radius_style", "Corners"),
			("use_shadows", "Shadows"),
			("button_hover", "Button hover"),
			("motion_style", "Motion"),
			("use_gradients", "Gradients"),
		),
	),
	(
		"Header and footer",
		(
			("header_style", "Header"),
			("header_bg_color", "Header background"),
			("header_text_color", "Header text"),
			("cta_style", "CTA style"),
			("cta_shape", "CTA shape"),
			("footer_template", "Footer"),
			("footer_bg_color", "Footer background"),
		),
	),
	(
		"Rhythm",
		(
			("hero_background", "Hero background"),
			("hero_min_height", "Hero height"),
			("section_padding", "Section padding"),
			("content_max_width", "Content width"),
		),
	),
)


def _translatable_labels():
	"""Extraction markers — never called.

	The group and field labels above are wrapped at the use site (`_(v)`);
	gettext cannot see through a variable. Keep in sync with GROUPS.
	"""
	_("The stance")
	_("Concept")
	_("Signature element")
	_("Tone")
	_("Inspiration")
	_("Colour")
	_("Primary")
	_("Primary is for")
	_("Secondary")
	_("Secondary is for")
	_("Headings")
	_("Body text")
	_("Links")
	_("Section backgrounds")
	_("Avoided")
	_("Type")
	_("Body")
	_("H1")
	_("H2")
	_("Body size")
	_("The design system")
	_("Corners")
	_("Shadows")
	_("Button hover")
	_("Motion")
	_("Gradients")
	_("Header and footer")
	_("Header")
	_("Header background")
	_("Header text")
	_("CTA style")
	_("CTA shape")
	_("Footer")
	_("Footer background")
	_("Rhythm")
	_("Hero background")
	_("Hero height")
	_("Section padding")
	_("Content width")


def _render(value):
	"""A brief value as one line of text, or None to drop the row."""
	if value is None or value == "" or value == [] or value == {}:
		return None
	if isinstance(value, bool):
		return _("Yes") if value else _("No")
	if isinstance(value, list):
		parts = [str(v) for v in value if v not in (None, "")]
		return ", ".join(parts) if parts else None
	if isinstance(value, dict):
		parts = [f"{k}: {v}" for k, v in value.items() if v not in (None, "")]
		return " · ".join(parts) if parts else None
	return str(value)


# values that are colours get a swatch in the UI
COLOUR_FIELDS = frozenset(
	{
		"primary_color",
		"secondary_color",
		"heading_color",
		"body_color",
		"link_color",
		"header_bg_color",
		"header_text_color",
		"footer_bg_color",
		"footer_text_color",
	}
)


def _grouped(raw) -> dict:
	if not raw:
		return {"exists": False}

	try:
		brief = json.loads(raw)
	except (TypeError, ValueError):
		return {"exists": False}

	groups = []
	for title, fields in GROUPS:
		rows = []
		for field, label in fields:
			text = _render(brief.get(field))
			if text is None:
				continue
			rows.append(
				{
					"label": _(label),
					"value": text,
					"is_color": field in COLOUR_FIELDS and str(text).startswith("#"),
				}
			)
		if rows:
			groups.append({"title": _(title), "rows": rows})

	return {"exists": True, "groups": groups, "raw": brief}


@frappe.whitelist()
def get_latest_brief(website_profile: str | None = None) -> dict:
	"""The brief behind the site as it stands: the last generation is what produced
	the current site, and the Theme is where its decisions ended up, so that is
	where the reasoning belongs. Per site profile when the instance serves several."""
	frappe.only_for(ROLES)

	raw, generated_on = None, None
	if website_profile and frappe.db.exists("Website Header Footer Variant", website_profile):
		raw, generated_on = frappe.db.get_value("Website Header Footer Variant", website_profile, ["ai_brief", "modified"])
	else:
		raw = frappe.db.get_single_value("Website Header Footer Config", "ai_brief")
		generated_on = frappe.db.get_single_value("Website Header Footer Config", "modified")
	if not raw:
		return {"exists": False}
	data = _grouped(raw)
	data["generated_on"] = generated_on
	return data
