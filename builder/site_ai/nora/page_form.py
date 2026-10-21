# //// Neoffice — added file (no upstream equivalent): a page made to be written to always carries the site's form.
"""A page whose title says "book", "reserve", "quote" or "contact" exists so that a visitor writes to the business. Built with the
local model (2026-10-21) the booking page of a restaurant came out with no form in two builds of two: its title was not one the
generator knew, so it typed the page "generic", the contact form was not offered to it, the plan wrote the page without one, and the
writer drew none. (Without recipes the same plan left it out once in two plans, so this is the plan's weakness, not the recipes'.)

Two things, so that the form is there whatever the plan and the writer do:
  - `wants_form(title)`: the titles of such pages, in the languages of the generator. `normalise_pages` types them "contact", which
    offers them the contact form and lets the plan plan it;
  - `ensure_form(blocks, ...)`: after the writer, a page that wants a form and carries none gets the site's contact form include in a
    section of its own, right after the opening section. The include is the form itself (it is adopted as a Site Form by the build,
    like any contact form), the section carries no copy of its own: the title band above it already says what the page is for.

No model is called."""

import re

# the bare title (lower case, no accent, see site_builder._bare): book, reserve, quote, appointment, contact, in French, English, German
FORM_TITLE = re.compile(
	r"\b(?:reserv\w*|book(?:ing|ings)?|devis|quotes?|quotation|offerte\w*|anfrage\w*|termin(?:vereinbarung| buchen)"
	r"|rendez-?vous|rdv|appointments?|contact\w*|kontakt\w*|nous ecrire|ecrivez-nous|write to us)\b"
)
# the forms that ask for a quote ("questions": what the request is about, the budget, the timing) and the one that only takes a message
QUOTE_TITLE = re.compile(r"\b(?:devis|quotes?|quotation|offerte\w*|anfrage\w*)\b")
CONTACT_INCLUDE = "builder/templates/includes/contact_form.html"
FORM_MARKERS = ("contact_form.html", "site_form.html")


def wants_form(title: str) -> bool:
	"""Whether a page with this bare title (lower case, no accent) is made to be written to."""
	return bool(FORM_TITLE.search(title or ""))


def form_model(title: str) -> str:
	"""The model of the contact form for this bare title: "questions" for a quote, "simple" for a booking or a message."""
	return "questions" if QUOTE_TITLE.search(title or "") else "simple"


def tag(model: str = "simple") -> str:
	"""The contact form include, written the way the generator writes it (a catalogued tag: components.parse_tag reads it)."""
	return '{%- set contact_model = "' + model + '" -%}{% include "' + CONTACT_INCLUDE + '" %}'


def has_form(blocks: list) -> bool:
	"""Whether the page carries a form of the site (the contact form or a Site Form include) or a form of its own."""
	from builder.site_ai.nora.layout import _walk

	for block in _walk(blocks):
		if str(block.get("element") or "").lower() == "form":
			return True
		html = block.get("innerHTML")
		if isinstance(html, str) and "include" in html and any(m in html for m in FORM_MARKERS):
			return True
	return False


def form_node(handles: dict, palette: dict | None, model: str = "simple") -> dict:
	"""The section that carries the form, in the writer's own format (recipes.py): a card on a tinted ground, the include inside."""
	from builder.site_ai.nora import recipes as R

	look = R.Look(handles, palette)
	ctx = R.Ctx(look, R.ground_of(look, "tint"), [], "", CONTACT_INCLUDE)
	card = R.el(
		"div",
		name="form-card",
		classes=["u-card"],
		style=R.flow(padding="2.5rem", maxWidth="44rem", width="100%", margin="0 auto"),
		m_style=R.flow(padding="1.5rem"),
		c=[R.el("div", name="form", text=tag(model))],
	)
	return R.section(ctx, "form-section", [R.container(ctx, [card])], pad="4.5rem 0", m_pad="3rem 0")


def ensure_form(blocks: list, page: dict, bare_title: str, handles: dict, palette: dict | None) -> bool:
	"""Gives a page that wants a form and has none the site's contact form, in a section right after its opening one (the last of the
	page when it has only one). Returns whether it did. Never on a legal page, never twice."""
	if page.get("type") == "legal" or not (page.get("type") == "contact" or wants_form(bare_title)):
		return False
	if not blocks or not isinstance(blocks[0], dict) or has_form(blocks):
		return False
	from builder.ai.page_writer import convert_yaml_block

	section = convert_yaml_block(form_node(handles, palette, form_model(bare_title)))
	if not section:
		return False
	root = blocks[0]
	children = root.setdefault("children", [])
	children.insert(1 if len(children) > 1 else len(children), section)
	return True
