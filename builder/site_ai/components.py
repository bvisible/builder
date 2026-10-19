"""//// Neoffice — added file (no upstream equivalent): the catalogue of page components.

A page can drop a Jinja include into itself and get a working, live block: the shop's product
carousel, the blog listing, the contact form, the map. Until 2026-09-15 the generator knew about
them through a hard-coded dict of SEVEN frozen tag strings (site_builder.PAGE_INCLUDES), mapped
to four page types. Measured on the instance that day: **13 includes are page-composable and 7
were catalogued**, so `blog_listing.html` — which documents its own six parameters in its header
and calls itself "a reusable block the generator may include" — had never been offered to the
generator that was supposed to include it.

Worse than the missing ones: the parameters. The product carousel takes a limit, a sort, a sort
order, a brand, a "discounted only" switch; the map takes a height, a zoom and a type; the blog
listing takes a category and a layout. The generator got frozen strings, and repair_includes
rewrote anything else back to them — so "the twelve newest", "only this brand", "the ones on
sale", "a taller map" were unreachable, by construction.

This module is the catalogue those two problems were missing. One declaration per component:
what it shows, which pages it suits, what it needs installed, whether it has anything to show,
and its parameters with their meaning and default. Three readers:

  * the generator's prompt, written from here instead of a frozen list;
  * the validator, which accepts a catalogued include with declared parameters instead of
    forcing the string back;
  * the editor, so a person can drop one and fill its parameters in a form (2026-10-19).

A fourth reader came on 2026-10-20: the `Builder Shortcode` registry that desk shows (the Website space of the
theme links to it). Until then THREE registries said the same thing, with three covers and three ways to reach a
site: this catalogue (code, every instance), `Builder Shortcode` (a fixture file nobody read) and `Builder AI
Shortcode` (rows typed on one instance, read by the old generator's prompt). The catalogue is the only definition
now. `Builder Shortcode` is its mirror on each site (sync_registry, run by install and migrate) and holds the
one thing a person owns there: `enabled`, the switch that takes a component out of what is offered. The two
endpoints that read the registry, and the old generator's prompt, read the catalogue.

An app OWNS its components: webshop knows what its carousel takes, not builder. So a component is
declared in its own app's hooks.py, as `website_components`, and this module collects them. The
apps that have not declared theirs yet are carried in BRIDGE below — a bridge, not a home: when
webshop declares its own, its entries come out of here.
"""

from __future__ import annotations

import json
import re

import frappe
from frappe import _

# a tag a page carries: the {% set %} parameters it was given, then the include itself
SET_PARAM = re.compile(r"\{%-?\s*set\s+([a-z_][a-z0-9_]*)\s*=\s*(.+?)\s*-?%\}")
INCLUDE_PATH = re.compile(r"\{%-?\s*include\s+['\"]([^'\"]+)['\"]\s*-?%\}")


class Component:
	"""One component of the catalogue."""

	def __init__(self, path, label, shows, pages=(), app="", params=(), data_check="", required=False, note="", needs_shop=False, help="", category="Content"):
		self.path = path
		self.label = label
		self.shows = shows
		self.pages = tuple(pages)
		self.app = app or path.split("/", 1)[0]
		self.params = tuple(params)
		self.data_check = data_check
		self.required = required
		self.note = note
		# //// Neoffice — a sentence for the PERSON choosing it in the editor (2026-10-19). `note` is
		# //// written for the generator ("never write a <form> of your own beside it"): shown to a
		# //// person it is an instruction to somebody else, in English.
		self.help = help
		# //// Neoffice — the group the desk registry files it under (E-commerce, Navigation, Content, Form, Layout, Other)
		self.category = category or "Content"
		# //// Neoffice — whether this component only makes sense on a site that SELLS. It is the
		# //// component's own answer, not its app's: webshop owns the products carousel, which
		# //// needs a shop, AND the opening hours, which are about the premises and belong on the
		# //// contact page of a plain showcase too (they were lost that way, 2026-09-15).
		self.needs_shop = bool(needs_shop)

	@property
	def file(self) -> str:
		return self.path.rsplit("/", 1)[-1]

	def tag(self, values: dict | None = None) -> str:
		"""The include tag, with the parameters given (and only those)."""
		declared = {p["name"]: p for p in self.params}
		sets = []
		for name, value in (values or {}).items():
			if name not in declared:
				continue
			sets.append(f'{{%- set {name} = {_as_jinja(value)} -%}}')
		return "".join(sets) + f'{{% include "{self.path}" %}}'

	def checked_values(self, values: dict | None) -> dict:
		"""What a person chose in the editor's form, held to what the component declares.

		A name the component does not declare is dropped (the way a generated page's is), an empty
		text is silence (the component's default applies), and a value that cannot be a literal of
		its tag raises ValueError with the sentence to show: a choice not on offer, a number out of
		range, a text with a character that would end the Jinja statement. Nothing here writes
		anything; the tag built from these values still goes through lawful_tag."""
		declared = {p["name"]: p for p in self.params}
		out = {}
		for name, value in (values or {}).items():
			param = declared.get(name)
			if param is None or value is None:
				continue
			checked = _checked_value(param, value)
			if checked is not _SILENT:
				out[name] = checked
		return out

	def describes(self) -> str:
		"""The line the generator reads: what it shows, then what it can be given."""
		line = f'- {{% include "{self.path}" %}} — {self.shows}'
		if self.params:
			line += "\n  parameters (each one a {%- set name = value -%} written before the include, all optional): "
			line += "; ".join(f"{p['name']} ({p['about']}" + (f", default {p['default']}" if p.get("default") not in (None, "") else "") + ")" for p in self.params)
		if self.note:
			line += f"\n  {self.note}"
		return line


# a text a tag can carry as a literal: LITERAL (below) refuses these characters, so a person who types one is
# told so, instead of the editor writing a tag the guard would then refuse
UNSAFE_TEXT = re.compile(r"[{}%\\\r\n]")
UNSAFE_TEXT_SHOWN = "{ } % \\"
MAX_TEXT = 600
_SILENT = object()


def choices_of(param: dict) -> list[dict]:
	"""A parameter's choices as [{value, label}]; a declaration may give bare strings."""
	out = []
	for choice in param.get("choices") or ():
		if isinstance(choice, dict):
			out.append({"value": str(choice["value"]), "label": choice.get("label") or str(choice["value"])})
		else:
			out.append({"value": str(choice), "label": str(choice)})
	return out


def param_label(param: dict) -> str:
	"""What a person reads over a parameter: its declared label, else its name made readable."""
	return param.get("label") or param["name"].replace("_", " ").capitalize()


def _checked_value(param: dict, value):
	"""One value, as the tag will carry it, or _SILENT for "not set"; ValueError with the sentence to show."""
	kind = param.get("type") or "str"
	label = _(param_label(param))
	if kind == "bool":
		if not isinstance(value, bool):
			raise ValueError(_("{0}: expected yes or no.").format(label))
		return value
	if kind == "int":
		if isinstance(value, bool) or not isinstance(value, (int, float, str)):
			raise ValueError(_("{0}: expected a whole number.").format(label))
		if isinstance(value, str) and not value.strip():
			return _SILENT
		try:
			number = float(value)
		except ValueError:
			raise ValueError(_("{0}: expected a whole number.").format(label)) from None
		if number != int(number):
			raise ValueError(_("{0}: expected a whole number.").format(label))
		number = int(number)
		low, high = param.get("min"), param.get("max")
		if (low is not None and number < low) or (high is not None and number > high):
			raise ValueError(_("{0}: expected a number from {1} to {2}.").format(label, low if low is not None else "-", high if high is not None else "-"))
		return number
	text = str(value).strip()
	if not text and not param.get("blank"):
		return _SILENT
	offered = choices_of(param)
	if offered and text not in {c["value"] for c in offered}:
		raise ValueError(_("{0}: pick one of the choices offered.").format(label))
	if UNSAFE_TEXT.search(text):
		raise ValueError(_("{0}: the text cannot contain these characters or a line break: {1}").format(label, UNSAFE_TEXT_SHOWN))
	if len(text) > MAX_TEXT:
		raise ValueError(_("{0}: the text is too long ({1} characters at most).").format(label, MAX_TEXT))
	return text


def _as_jinja(value) -> str:
	if isinstance(value, bool):
		return "true" if value else "false"
	if isinstance(value, (int, float)):
		return str(value)
	return '"' + str(value).replace('"', "'") + '"'


# //// Neoffice — the bridge: components of apps that do not declare their own yet. Each entry
# //// moves into its app's hooks.py the day that app declares `website_components`.
BRIDGE: list[Component] = [
	Component(
		path="webshop/templates/includes/product_carousel.html",
		label="Products carousel",
		shows="a scrollable row of the shop's REAL products, with their pictures, prices and links — never a product drawn by hand",
		pages=("accueil", "shop", "one_page"),
		app="webshop",
		data_check="builder.empty_includes.has_pictured_products",
		params=[
			{"name": "carousel_title", "label": "Title", "type": "str", "default": "", "about": "the heading over the row, in the site's language"},
			{"name": "carousel_limit", "label": "How many products", "min": 1, "type": "int", "default": 8, "about": "how many products"},
			{"name": "carousel_sort_by", "label": "Sorted by", "choices": [{"value": "creation", "label": "Newest first"}, {"value": "modified", "label": "Last updated"}, {"value": "item_name", "label": "Name"}, {"value": "standard_rate", "label": "Price"}], "type": "str", "default": "creation", "about": "creation, modified, item_name or standard_rate"},
			{"name": "carousel_sort_order", "label": "Order", "choices": [{"value": "desc", "label": "Descending"}, {"value": "asc", "label": "Ascending"}], "type": "str", "default": "desc", "about": "desc or asc"},
			{"name": "carousel_brand", "label": "Only this brand", "type": "str", "default": "", "about": "only the products of that brand, by its exact name"},
			{"name": "carousel_item_group", "label": "Only this category", "type": "str", "default": "", "about": "only the products of that category, by its exact name"},
			{"name": "show_discounted_only", "label": "Discounted products only", "type": "bool", "default": False, "about": "only the products on sale"},
			{"name": "hide_without_image", "label": "Hide products without a photo", "type": "bool", "default": True, "about": "leave out a product with no photograph"},
			{"name": "view_more_link", "label": "'View more' link", "type": "str", "default": "", "about": "where the 'View more' button goes, e.g. /all-products"},
			{"name": "view_more_text", "label": "'View more' text", "type": "str", "default": "View More", "about": "what that button reads, in the site's language"},
		],
		needs_shop=True,
		category="E-commerce",
		help="Two of them on one page show the same products twice: give the second one another order, or only the discounted products.",
		note="Two of them on one page is two rows of the same shop: give the second a different sort or show_discounted_only.",
	),
	Component(
		path="webshop/templates/includes/brand_carousel.html",
		label="Brands carousel",
		shows="the brands the shop carries, with their logos",
		pages=("accueil", "brands", "shop", "one_page"),
		app="webshop",
		data_check="builder.empty_includes.has_pictured_brands",
		params=[
			{"name": "carousel_title", "label": "Title", "type": "str", "default": "", "about": "the heading over the row"},
			# //// Neoffice — 0 is NOT "all" (2026-09-16). The template slices `sorted_brands[:carousel_limit|default(20)]`
			# //// and Jinja's default() only fires on an UNDEFINED variable, never on 0 — so 0 draws an empty strip.
			# //// The catalogue said "0 for all", the generator passed 0, and a home page announced "Nos univers
			# //// produits" over "Aucune marque disponible". Describe what the template does, not what would be nice.
			{"name": "carousel_limit", "label": "How many brands", "min": 1, "type": "int", "default": 20, "about": "how many brands at most; leave it out for the default, never 0 — 0 draws none"},
			{"name": "carousel_sort_by", "label": "Sorted by", "choices": [{"value": "brand_name", "label": "Name"}, {"value": "product_count", "label": "Number of products"}], "type": "str", "default": "brand_name", "about": "brand_name or product_count"},
			{"name": "show_product_count", "label": "Show the number of products", "type": "bool", "default": False, "about": "show how many products each brand has"},
			{"name": "hide_without_image", "label": "Hide brands without a logo", "type": "bool", "default": True, "about": "leave out a brand with no logo"},
			{"name": "view_more_link", "label": "'View more' link", "type": "str", "default": "", "about": "where the 'View more' button goes"},
			{"name": "view_more_text", "label": "'View more' text", "type": "str", "default": "View More", "about": "what that button reads, in the site's language"},
		],
		needs_shop=True,
		category="E-commerce",
	),
	Component(
		path="webshop/templates/includes/opening_hours.html",
		label="Opening hours",
		shows="the shop's opening hours, live, holidays included",
		pages=("contact", "about", "one_page"),
		app="webshop",
		data_check="builder.empty_includes.opening_hours_configured",
		params=[{"name": "display", "label": "Show", "choices": [{"value": "full", "label": "The whole week"}, {"value": "compact", "label": "Today only"}], "type": "str", "default": "full", "about": "full for the whole week, compact for the state and today only"}],
	),
]


def _from_hooks() -> list[Component]:
	"""The components each installed app declares in its hooks.py as `website_components`."""
	out = []
	try:
		declared = frappe.get_hooks("website_components") or []
	except Exception:
		return out
	for entry in declared:
		if not isinstance(entry, dict) or not entry.get("path"):
			continue
		out.append(
			Component(
				path=entry["path"],
				label=entry.get("label") or entry["path"].rsplit("/", 1)[-1],
				shows=entry.get("shows") or "",
				pages=entry.get("pages") or (),
				app=entry.get("app") or "",
				params=entry.get("params") or (),
				data_check=entry.get("data_check") or "",
				required=bool(entry.get("required")),
				note=entry.get("note") or "",
				needs_shop=bool(entry.get("needs_shop")),
				help=entry.get("help") or "",
				category=entry.get("category") or "Content",
			)
		)
	return out


def catalogue() -> list[Component]:
	"""Every component of every INSTALLED app: the declared ones, then the bridge for the apps
	that have not declared theirs. A declaration always wins over the bridge."""
	try:
		installed = set(frappe.get_installed_apps())
	except Exception:
		installed = {"builder"}
	declared = _from_hooks()
	known = {c.path for c in declared}
	out = list(declared) + [c for c in BRIDGE if c.path not in known]
	return [c for c in out if c.app in installed]


def has_data(component: Component, profile: str | None) -> bool | None:
	"""Whether the component has anything to show on this site: True, False, or None when it
	declares no check. A check that raises counts as nothing to show — the include would fail
	the same way at render time."""
	if not component.data_check:
		return None
	try:
		return bool(frappe.get_attr(component.data_check)(profile))
	except TypeError:
		try:
			return bool(frappe.get_attr(component.data_check)())
		except Exception:
			return False
	except Exception:
		return False


def for_page(page_type: str, profile: str | None = None, allow=None) -> list[Component]:
	"""The components this page may carry: catalogued, suited to the page, whose app is
	installed, that have something to show, and that `allow` does not refuse.

	`allow` is the caller's own rule — on a multi-site instance a site built for ANOTHER
	business must not show this instance's shop — and it is asked about each component."""
	out = []
	off = disabled_paths()
	for component in catalogue():
		if page_type not in component.pages:
			continue
		# //// Neoffice — what the site turned off in the registry is not offered (a page that already carries it keeps it)
		if component.path in off:
			continue
		if callable(allow) and not allow(component):
			continue
		if has_data(component, profile) is False:
			continue
		out.append(component)
	return out


# ---- the registry desk shows -------------------------------------------------------------------------------------
REGISTRY = "Builder Shortcode"
REGISTRY_FIELDS = ("category", "source_app", "template_path", "description", "usage_syntax", "parameters", "example_code")
_TYPE_NAMES = {"str": "string", "int": "integer", "bool": "boolean"}


def disabled_paths() -> set[str]:
	"""The include paths this site turned off in the registry, the one thing a person owns there. A site where
	the registry cannot be read (before its migrate) turns nothing off."""
	try:
		return {path for path in frappe.get_all(REGISTRY, filters={"enabled": 0}, pluck="template_path") if path}
	except Exception:
		return set()


def enabled_catalogue() -> list[Component]:
	"""The catalogue without what this site turned off. A tag already on a page is still read through the whole
	catalogue (lawful_tag, clean_tag, by_file): turning a component off stops offering it, it does not break a page."""
	off = disabled_paths()
	return [c for c in catalogue() if c.path not in off]


def _example_value(param: dict):
	"""A value that shows what the option does: the other choice, the opposite switch, else the default."""
	default = param.get("default")
	if param.get("type") == "bool":
		return not bool(default)
	for choice in choices_of(param):
		if choice["value"] != str(default):
			return choice["value"]
	return default


def example_tag(component: Component) -> str:
	"""A tag with its first options filled in, for the registry's Example field."""
	values = {}
	for param in component.params:
		value = _example_value(param)
		if value not in (None, "") and len(values) < 3:
			values[param["name"]] = value
	return component.tag(values)


def registry_row(component: Component) -> dict:
	"""The component as the `Builder Shortcode` registry documents it, written FROM the catalogue and never typed:
	the description, usage and example a person reads in desk, and the endpoints that serve them."""
	parameters = []
	for param in component.params:
		item = {
			"name": param["name"],
			"label": param_label(param),
			"type": _TYPE_NAMES.get(param.get("type"), param.get("type") or "string"),
			"default": param.get("default"),
			"description": param.get("about") or "",
		}
		if choices_of(param):
			item["choices"] = [c["value"] for c in choices_of(param)]
		parameters.append(item)
	return {
		"shortcode_name": component.label,
		"category": component.category,
		"source_app": component.app,
		"template_path": component.path,
		"description": component.shows,
		"usage_syntax": component.tag(),
		"parameters": json.dumps(parameters, ensure_ascii=False, indent=2) if parameters else "[]",
		"example_code": example_tag(component),
	}


def sync_registry() -> dict:
	"""Make the registry of this site say what the catalogue says: a row for each component of an installed app,
	its documentation following the code, `enabled` left alone (that switch belongs to the site, and a migrate must
	not turn a component back on after its owner turned it off), and no row for what the catalogue does not hold
	(a retired component, an app that is not installed here, a row typed by hand: nothing reads it).

	One row must never fail a migrate: this runs inside `bench migrate` on every instance of the fleet. The savepoint
	keeps one bad row from poisoning the transaction the rest of the migrate needs; it costs a line in the Error Log."""
	wanted = {c.path: registry_row(c) for c in catalogue()}
	existing = frappe.get_all(REGISTRY, fields=["name", "template_path"], order_by="creation")
	kept: dict[str, str] = {}
	stale: list[str] = []
	for row in existing:
		if row.template_path in wanted and row.template_path not in kept:
			kept[row.template_path] = row.name
		else:
			stale.append(row.name)

	done = {"added": 0, "updated": 0, "removed": 0, "failed": 0}
	for index, (path, row) in enumerate(wanted.items()):
		name = row["shortcode_name"]
		# a fixed identifier: a savepoint named after the label broke on "The company's timeline" (an apostrophe), and the
		# guard that was meant to survive a bad row failed with it
		savepoint = f"registry_row_{index}"
		frappe.db.savepoint(savepoint)
		try:
			current = kept.get(path)
			if current is None:
				frappe.get_doc(dict(row, doctype=REGISTRY)).insert(ignore_permissions=True)
				done["added"] += 1
				continue
			if current != name:
				frappe.rename_doc(REGISTRY, current, name, force=True, ignore_permissions=True, show_alert=False, rebuild_search=False)
			doc = frappe.get_doc(REGISTRY, name)
			changed = False
			for field in REGISTRY_FIELDS:
				if (doc.get(field) or "") != (row[field] or ""):
					doc.set(field, row[field])
					changed = True
			if changed:
				doc.save(ignore_permissions=True)
				done["updated"] += 1
		except Exception:
			try:
				frappe.db.rollback(save_point=savepoint)
			except Exception:
				pass
			done["failed"] += 1
			frappe.log_error(f"Builder Shortcode: {name[:100]}", f"sync_registry could not write this row:\n\n{frappe.get_traceback()}")
	for name in stale:
		try:
			frappe.delete_doc(REGISTRY, name, ignore_permissions=True, force=True)
			done["removed"] += 1
		except Exception:
			done["failed"] += 1
			frappe.log_error(f"Builder Shortcode: {name[:100]}", f"sync_registry could not remove this row:\n\n{frappe.get_traceback()}")
	return done


def shortcodes_markdown() -> str:
	"""The components this site offers, as markdown for a prompt: what `get_shortcodes_for_ai` has always returned
	(category, name, description, usage, example), written from the catalogue."""
	rows = sorted((registry_row(c) for c in enabled_catalogue()), key=lambda r: (r["category"], r["shortcode_name"]))
	if not rows:
		return ""
	lines = ["## Available Shortcodes\n", "You can use these Jinja includes in Builder pages:\n"]
	category = None
	for row in rows:
		if row["category"] != category:
			category = row["category"]
			lines.append(f"\n### {category}\n")
		lines.append(f"#### {row['shortcode_name']}")
		if row["description"]:
			lines.append(f"{row['description']}\n")
		lines.append(f"**Usage:**\n```jinja\n{row['usage_syntax']}\n```\n")
		lines.append(f"**Example:**\n```jinja\n{row['example_code']}\n```\n")
	return "\n".join(lines)


def by_file(name: str) -> Component | None:
	"""The catalogued component whose file is `name` (product_carousel.html), or None."""
	return next((c for c in catalogue() if c.file == name), None)


def clean_tag(text: str) -> str | None:
	"""A page's tag, kept if it is catalogued and carries only declared parameters, rewritten
	without the ones that are not, or None when the include is not in the catalogue.

	This is what replaced "copied exactly": a generator told what a component takes should be
	able to ask for twelve products sorted by price, and have that survive."""
	found = INCLUDE_PATH.search(text or "")
	if not found:
		return None
	component = by_file(found.group(1).rsplit("/", 1)[-1])
	if not component:
		return None
	declared = {p["name"] for p in component.params}
	given = SET_PARAM.findall(text)
	kept = [f"{{%- set {name} = {value} -%}}" for name, value in given if name in declared]
	# //// Neoffice — a tag that already means what it should is left exactly as it is: rewriting
	# //// it to change a quote style is churn, and it inflates the count the build reports.
	nothing_changed = len(kept) == len(given) and found.group(1) == component.path
	return text.strip() if nothing_changed else "".join(kept) + f'{{% include "{component.path}" %}}'


# a parameter value written as a LITERAL: a quoted string with no Jinja in it, a number, true or false
LITERAL = r"""(?:"[^"{}%\\\n]*"|'[^'{}%\\\n]*'|-?\d+(?:\.\d+)?|true|false|True|False)"""
LAWFUL_SET = rf"\{{%-?\s*set\s+[a-z_][a-z0-9_]*\s*=\s*{LITERAL}\s*-?%\}}"
LAWFUL_TAG = re.compile(rf"^\s*(?:{LAWFUL_SET}\s*)*\{{%-?\s*include\s+['\"][^'\"{{}}%]+['\"]\s*-?%\}}\s*$")
LAWFUL_VALUE = re.compile(rf"\{{%-?\s*set\s+([a-z_][a-z0-9_]*)\s*=\s*({LITERAL})\s*-?%\}}")


def component_of(text: str) -> Component | None:
	"""The catalogued component whose include `text` carries, lawful or not (a tag edited by hand still
	names its component); None when there is no include, or its path is not in the catalogue."""
	found = INCLUDE_PATH.search(text or "")
	component = by_file(found.group(1).rsplit("/", 1)[-1]) if found else None
	return component if component is not None and found.group(1) == component.path else None


def parse_tag(text: str) -> tuple[Component, dict] | None:
	"""(component, values) when `text` is NOTHING BUT a catalogued component's tag: `set` statements of
	parameters the component declares, each with a literal value, then its include. None for anything
	else, a stray Jinja expression, a second statement, a path the catalogue does not hold, a
	parameter it does not declare."""
	if not text or "{%" not in text or not LAWFUL_TAG.match(text):
		return None
	component = component_of(text)
	if component is None:
		return None
	declared = {p["name"] for p in component.params}
	values: dict = {}
	for name, raw in LAWFUL_VALUE.findall(text):
		if name not in declared:
			return None
		if raw.lower() in ("true", "false"):  # the generator writes True, the assistant true: both are Jinja
			values[name] = raw.lower() == "true"
		elif raw[0] in "\"'":
			values[name] = raw[1:-1]
		else:
			values[name] = float(raw) if "." in raw else int(raw)
	return component, values


def lawful_tag(text: str) -> str | None:
	"""The canonical tag when `text` is NOTHING BUT a catalogued component's tag (parse_tag), else None.

	The editor's assistant writes block text through tools that refuse Jinja, because Jinja in a page
	that is not a component's tag crashes the published route. A component's tag is the one Jinja a
	page is meant to carry (the generator writes them, repair_includes keeps them): this is what lets
	the assistant place one and change its options, and nothing else. The tag is rebuilt from the
	values, never passed through as written. It is also the gate of the editor's own picker
	(api.render_component_tag): a person's form values become a tag only if this accepts it."""
	parsed = parse_tag(text)
	return parsed[0].tag(parsed[1]) if parsed else None


def page_type_for_route(route: str | None) -> str | None:
	"""The page type a route stands for ("contact", "home" -> "accueil"), None for a route the
	generator does not know: the picker then offers everything and recommends nothing."""
	from builder.site_ai.nora.site_builder import KNOWN_PAGES

	route = (route or "").strip().strip("/")
	return next((kind for known, kind in KNOWN_PAGES.values() if known == route), None)


def prompt_block(components: list[Component]) -> str:
	"""The INCLUDES section of a page brief, written from the catalogue."""
	if not components:
		return ""
	required = [c for c in components if c.required]
	optional = [c for c in components if not c.required]
	lines = []
	if required:
		lines.append(
			"COMPONENTS REQUIRED on this page (each one as the `text` of its own plain div block, never inside a "
			"grid or flex row; do NOT write your own version of it, the include IS the working block):"
		)
		lines += [c.describes() for c in required]
	if optional:
		lines.append(
			("COMPONENTS available (optional, same rule: " if required else "COMPONENTS available (optional, ")
			+ "each one as the `text` of its own plain div block, never inside a grid or flex row). They draw the "
			"site's REAL data — products, brands, hours, posts — so never draw by hand what one of them shows:"
		)
		lines += [c.describes() for c in optional]
	return "\n".join(lines)
