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
  * (next) the editor, so a person can drop one and fill its parameters in a form.

An app OWNS its components: webshop knows what its carousel takes, not builder. So a component is
declared in its own app's hooks.py, as `website_components`, and this module collects them. The
apps that have not declared theirs yet are carried in BRIDGE below — a bridge, not a home: when
webshop declares its own, its entries come out of here.
"""

from __future__ import annotations

import re

import frappe

# a tag a page carries: the {% set %} parameters it was given, then the include itself
SET_PARAM = re.compile(r"\{%-?\s*set\s+([a-z_][a-z0-9_]*)\s*=\s*(.+?)\s*-?%\}")
INCLUDE_PATH = re.compile(r"\{%-?\s*include\s+['\"]([^'\"]+)['\"]\s*-?%\}")


class Component:
	"""One component of the catalogue."""

	def __init__(self, path, label, shows, pages=(), app="", params=(), data_check="", required=False, note=""):
		self.path = path
		self.label = label
		self.shows = shows
		self.pages = tuple(pages)
		self.app = app or path.split("/", 1)[0]
		self.params = tuple(params)
		self.data_check = data_check
		self.required = required
		self.note = note

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

	def describes(self) -> str:
		"""The line the generator reads: what it shows, then what it can be given."""
		line = f'- {{% include "{self.path}" %}} — {self.shows}'
		if self.params:
			line += "\n  parameters (each one a {%- set name = value -%} written before the include, all optional): "
			line += "; ".join(f"{p['name']} ({p['about']}" + (f", default {p['default']}" if p.get("default") not in (None, "") else "") + ")" for p in self.params)
		if self.note:
			line += f"\n  {self.note}"
		return line


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
			{"name": "carousel_title", "type": "str", "default": "", "about": "the heading over the row, in the site's language"},
			{"name": "carousel_limit", "type": "int", "default": 8, "about": "how many products"},
			{"name": "carousel_sort_by", "type": "str", "default": "creation", "about": "creation, modified, item_name or standard_rate"},
			{"name": "carousel_sort_order", "type": "str", "default": "desc", "about": "desc or asc"},
			{"name": "show_discounted_only", "type": "bool", "default": False, "about": "only the products on sale"},
			{"name": "hide_without_image", "type": "bool", "default": True, "about": "leave out a product with no photograph"},
			{"name": "view_more_link", "type": "str", "default": "", "about": "where the 'View more' button goes, e.g. /all-products"},
		],
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
			{"name": "carousel_title", "type": "str", "default": "", "about": "the heading over the row"},
			{"name": "carousel_limit", "type": "int", "default": 0, "about": "how many brands, 0 for all"},
			{"name": "show_product_count", "type": "bool", "default": False, "about": "show how many products each brand has"},
			{"name": "hide_without_image", "type": "bool", "default": True, "about": "leave out a brand with no logo"},
		],
	),
	Component(
		path="webshop/templates/includes/opening_hours.html",
		label="Opening hours",
		shows="the shop's opening hours, live, holidays included",
		pages=("contact", "about", "one_page"),
		app="webshop",
		data_check="builder.empty_includes.opening_hours_configured",
		params=[{"name": "display", "type": "str", "default": "compact", "about": "compact or full for the whole week"}],
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
	for component in catalogue():
		if page_type not in component.pages:
			continue
		if callable(allow) and not allow(component):
			continue
		if has_data(component, profile) is False:
			continue
		out.append(component)
	return out


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
	kept = [
		f"{{%- set {name} = {value} -%}}"
		for name, value in SET_PARAM.findall(text)
		if name in declared
	]
	return "".join(kept) + f'{{% include "{component.path}" %}}'


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
