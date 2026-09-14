# //// Neoffice — added file (no upstream equivalent): the band over a Builder page steps aside when
# //// the page opens on its own title, keeps the breadcrumb trail for the search engines, and writes
# //// in the page's own faces (builder/page_header.py, 2026-09-14).
import json
import re
import unittest
from unittest.mock import patch

import frappe

from builder import page_header


def page(*sections):
	return json.dumps([{"element": "div", "originalElement": "body", "children": list(sections)}])


def section(*children, **styles):
	return {"element": "section", "baseStyles": styles, "children": list(children)}


def text(element, html, **styles):
	return {"element": element, "innerHTML": html, "baseStyles": styles, "children": []}


# a services page whose first section is its own page top, in the site's style
OWN_TOP = page(
	section(text("p", "OUR SERVICES"), text("h1", "What we do"), text("p", "From the market to the table.")),
	section(text("h2", "The market")),
)
# an interior page that opens on its content, as the generator is told to write them
CONTENT_FIRST = page(
	section(
		text("h2", "The market", fontFamily="'Lora', serif", fontWeight="500"),
		text("p", "Every Saturday morning.", fontFamily='"DM Sans", sans-serif'),
	)
)
# the same page top with a rule under its title, the title coloured and centred
RULED_TOP = page(
	section(
		text("p", "OUR SERVICES"),
		text("h1", "What we do", color="#a67c00", textAlign="center"),
		{"element": "div", "baseStyles": {"width": "80px", "height": "2px"}, "children": []},
		text("p", "From the market to the table.", fontFamily="'DM Sans', sans-serif"),
	),
)
# how such a top renders: the eyebrow, the title, its rule, the line under it
TOP_MARKUP = (
	'<section><p>OUR SERVICES</p><h1 class="t">What we do</h1><div class="rule"></div>'
	"<p>From the market to the table.</p></section>"
)


def trail_of(html):
	"""The names in the page's BreadcrumbList JSON-LD, or None when there is none."""
	found = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
	if not found:
		return None
	data = json.loads(found.group(1))
	return [item["name"] for item in data["itemListElement"]]


def nav_of(html):
	"""The trail a page draws under its own title, or None."""
	found = re.search(r'<nav class="site-page-crumbs".*?</nav>', html, re.S)
	return found.group(0) if found else None


def component_reader(block_json):
	"""frappe.db.get_value answering the Builder Component's block, and passing every other read on:
	rendering blocks reads DocType rows through the same call."""
	original = frappe.db.get_value

	def read(doctype, *args, **kwargs):
		if doctype == "Builder Component":
			return block_json
		return original(doctype, *args, **kwargs)

	return read


class TestPageTop(unittest.TestCase):
	def band(self, blocks, title="Services", route="services", **config):
		doc = frappe._dict(route=route, page_title=title, blocks=blocks)
		with (
			patch.object(page_header, "_config", return_value=None),
			patch.object(page_header, "settings", return_value=dict(page_header.DEFAULTS, **config)),
		):
			return page_header.render_builder_page_header(doc)

	def placed(self, blocks, content=TOP_MARKUP, title="Services", route="services", fields=None, **config):
		"""The page's rendered markup once place_page_crumbs has been through it."""
		doc = frappe._dict(route=route, page_title=title, blocks=blocks, **(fields or {}))
		with (
			patch.object(page_header, "_config", return_value=None),
			patch.object(page_header, "settings", return_value=dict(page_header.DEFAULTS, **config)),
		):
			return page_header.place_page_crumbs(content, doc)

	def test_a_page_opening_on_its_own_title_gets_no_second_one(self):
		"""A services page drew "Services" in the band, then its own "Our services": two h1. The band draws
		nothing above such a page: the page shows the trail under its own title (place_page_crumbs), and the
		trail stays in the JSON-LD (2026-09-14)."""
		html = self.band(OWN_TOP)
		self.assertNotIn("<h1", html)
		self.assertNotIn("site-page-header", html)
		self.assertNotIn("<nav", html)
		self.assertEqual(trail_of(html), [frappe._("Home"), "Services"])

	def test_an_own_title_page_without_the_breadcrumb_keeps_only_the_json_ld(self):
		html = self.band(OWN_TOP, show_breadcrumbs=0)
		self.assertNotIn("site-page-header", html)
		self.assertEqual(trail_of(html), [frappe._("Home"), "Services"])

	def test_a_shop_page_follows_the_shop_trail(self):
		"""The band read "Home / Shop by Category / Products / T-Shirt" where the shop's own trail, hidden
		under it, reads "Home / Shop / Products / T-Shirt"."""
		parents = [
			{"route": "shop-by-category", "title": "Shop by Category"},
			{"route": "products", "title": "Products"},
			{"route": "products/t-shirt", "title": "T-Shirt"},
		]
		context = frappe._dict(doc=frappe._dict(doctype="Website Item"), parents=parents)
		trail = page_header._breadcrumbs(context, "products/t-shirt/coastline", "Coastline")
		self.assertEqual([c["label"] for c in trail], [frappe._("Home"), frappe._("Shop"), "Products", "T-Shirt", "Coastline"])
		self.assertEqual(trail[1]["url"], "/all-products")
		listing = page_header._breadcrumbs(frappe._dict(), "all-products", frappe._("All Products"))
		self.assertEqual([c["label"] for c in listing], [frappe._("Home"), frappe._("Shop")])
		self.assertEqual(listing[-1]["url"], "")

	def test_the_band_says_when_it_prints_the_title(self):
		"""The shop's product page hid its h1 under the band's and kept it in the markup."""
		context = frappe._dict(title="Cart", parents=[])
		with patch.object(frappe.local, "page_header_route", "cart", create=True):
			with patch.object(page_header, "settings", return_value=dict(page_header.DEFAULTS)):
				self.assertEqual(page_header.band_draws(context), {"trail": True, "title": True})
			with patch.object(page_header, "settings", return_value=dict(page_header.DEFAULTS, page_header_template="None")):
				self.assertEqual(page_header.band_draws(context), {"trail": False, "title": False})
			# a page that opens on its own title draws its trail itself, under that title
			own = frappe._dict(title="Cart", parents=[], page_opens_itself=True)
			with patch.object(page_header, "settings", return_value=dict(page_header.DEFAULTS)):
				self.assertEqual(page_header.band_draws(own), {"trail": False, "title": False})

	def test_the_band_says_when_it_draws_the_trail(self):
		"""site_chrome keeps the page's own breadcrumb out of the markup when the band draws one."""
		context = frappe._dict(title="Cart", parents=[])
		with patch.object(frappe.local, "page_header_route", "cart", create=True):
			with patch.object(page_header, "settings", return_value=dict(page_header.DEFAULTS)):
				self.assertTrue(page_header.band_draws_trail(context))
			with patch.object(page_header, "settings", return_value=dict(page_header.DEFAULTS, show_breadcrumbs=0)):
				self.assertFalse(page_header.band_draws_trail(context))

	def test_a_page_opening_on_its_content_keeps_the_band(self):
		html = self.band(CONTENT_FIRST)
		self.assertIn('class="site-page-header', html)
		self.assertEqual(html.count("<h1"), 1)
		# the band's own stylesheet names the class: the element is what counts
		self.assertIn('<nav class="site-page-header__crumbs"', html)
		self.assertEqual(trail_of(html), [frappe._("Home"), "Services"])

	def test_a_hidden_trail_stays_in_the_markup(self):
		"""Turning the breadcrumb off took it out of the page, and the search engines with it."""
		html = self.band(CONTENT_FIRST, show_breadcrumbs=0)
		self.assertIn('class="site-page-header', html)
		self.assertNotIn('<nav class="site-page-header__crumbs"', html)
		self.assertEqual(trail_of(html), [frappe._("Home"), "Services"])

	def test_a_band_switched_off_still_leaves_the_trail(self):
		html = self.band(CONTENT_FIRST, page_header_template="None")
		self.assertNotIn("site-page-header", html)
		self.assertEqual(trail_of(html), [frappe._("Home"), "Services"])

	def test_the_band_writes_in_the_page_faces(self):
		"""The band's title was set in the theme's serif above a page set in its own."""
		html = self.band(CONTENT_FIRST)
		self.assertIn("--sph-heading-font:'Lora', serif;", html)
		self.assertIn("--sph-heading-weight:500;", html)
		self.assertIn("--sph-body-font:'DM Sans', sans-serif;", html)

	def test_a_page_without_faces_keeps_the_theme(self):
		self.assertEqual(page_header._page_fonts(page(section(text("h2", "Plain")))), "")

	def test_a_face_cannot_leave_its_declaration(self):
		for family in ("Lora;background:url(//x.test/a.png)", "Lora}</style><script>", "expression(alert(1))"):
			self.assertEqual(page_header._page_fonts(page(section(text("h2", "T", fontFamily=family)))), "", family)
		self.assertEqual(
			page_header._page_fonts(page(section(text("h2", "T", fontFamily="var(--nt-font-heading)")))),
			"--sph-heading-font:var(--nt-font-heading);",
		)

	def test_the_trail_cannot_close_its_script(self):
		html = self.band(CONTENT_FIRST, title="Tips </script><script>alert(1)</script>", route="tips")
		self.assertEqual(html.count("</script>"), 1)
		self.assertEqual(trail_of(html)[-1], "Tips </script><script>alert(1)</script>")

	def test_a_home_gets_nothing(self):
		self.assertEqual(self.band(OWN_TOP, title="Home", route="home"), "")

	def test_the_editor_preview_draws_the_band_whatever_the_first_section(self):
		"""The editor hides the band itself while its live page opens on an h1: it asks for it anyway."""
		doc = frappe._dict(route="services", page_title="Services", blocks=OWN_TOP)
		with (
			patch.object(page_header, "_config", return_value=None),
			patch.object(page_header, "settings", return_value=dict(page_header.DEFAULTS)),
		):
			self.assertIn('class="site-page-header', page_header.render_builder_page_header(doc, own_top=False))
			# on its own, the page gets no band and no second title: its trail goes under its own title
			auto = page_header.render_builder_page_header(doc)
			self.assertNotIn("site-page-header", auto)
			self.assertNotIn("<h1", auto)

	def test_a_page_set_to_go_without_the_band_keeps_its_trail(self):
		doc = frappe._dict(route="services", page_title="Services", blocks=CONTENT_FIRST, hide_page_header=1)
		with (
			patch.object(page_header, "_config", return_value=None),
			patch.object(page_header, "settings", return_value=dict(page_header.DEFAULTS)),
		):
			html = page_header.render_builder_page_header(doc)
		# no band drawn: only the quiet title and the trail stay
		self.assertNotIn('<section class="site-page-header', html)
		self.assertEqual(trail_of(html), [frappe._("Home"), "Services"])

	def test_a_page_without_the_band_keeps_its_title_quietly(self):
		"""Hidden by the page setting, the band took the page's only h1 with it."""
		doc = frappe._dict(route="services", page_title="Services", blocks=CONTENT_FIRST, hide_page_header=1)
		with (
			patch.object(page_header, "_config", return_value=None),
			patch.object(page_header, "settings", return_value=dict(page_header.DEFAULTS)),
		):
			html = page_header.render_builder_page_header(doc)
			own = page_header.render_builder_page_header(frappe._dict(route="services", page_title="Services", blocks=OWN_TOP, hide_page_header=1))
		self.assertEqual(html.count("<h1"), 1)
		self.assertIn('class="site-page-header__quiet"', html)
		self.assertIn("clip:rect(0,0,0,0)", html)
		# a page with an h1 of its own needs no second one
		self.assertNotIn("<h1", own)

	def test_a_designed_top_page_draws_its_component_with_the_page_data(self):
		"""The band as a component designed in the Builder: its title block is bound to page_title."""
		component = json.dumps({
			"blockId": "band", "element": "section", "baseStyles": {"padding": "48px 24px"},
			"children": [{
				"blockId": "title", "element": "h1", "innerHTML": "Designed title", "baseStyles": {},
				"dynamicValues": [{"key": "page_title", "property": "innerHTML", "type": "key", "comesFrom": "dataScript"}],
				"children": [],
			}],
		})
		doc = frappe._dict(route="services", page_title="Services <b>", blocks=CONTENT_FIRST)
		settings = dict(page_header.DEFAULTS, page_header_template="Builder", page_header_component="Top Band")
		with (
			patch.object(page_header, "_config", return_value=None),
			patch.object(page_header, "settings", return_value=settings),
			patch.object(frappe.db, "get_value", side_effect=component_reader(component)),
		):
			html = page_header.render_builder_page_header(doc)
		self.assertIn("site-page-header--builder", html)
		self.assertIn("Services &lt;b&gt;", html)
		self.assertNotIn("Designed title", html)
		self.assertEqual(trail_of(html), [frappe._("Home"), "Services <b>"])

	def test_a_designed_top_page_without_its_component_falls_back_to_the_preset(self):
		settings = dict(page_header.DEFAULTS, page_header_template="Builder", page_header_component="")
		html = self.band(CONTENT_FIRST, **{k: v for k, v in settings.items() if k != "show_breadcrumbs"})
		self.assertIn("site-page-header--standard", html)

	def test_the_starting_top_page_binds_the_page_and_speaks_the_site_tokens(self):
		block = page_header.default_band_block("xx")
		flat = json.dumps(block)
		self.assertIn("var(--xx-font-heading)", flat)
		self.assertIn('"key": "page_title"', flat)
		self.assertIn('"key": "page_subtitle"', flat)
		self.assertIn("{% for crumb in breadcrumbs %}", flat)
		# drawn with the band's data, the starting component shows the page, not its design text
		with patch.object(frappe.db, "get_value", side_effect=component_reader(flat)):
			html = page_header.render_component_band(
				"Top Band",
				{"page_title": "Services", "page_subtitle": "", "breadcrumbs": [{"label": "Home", "url": "/"}, {"label": "Services", "url": ""}], "page_image": ""},
			)
		self.assertIn("Services", html)
		self.assertIn('<a href="/">Home</a>', html)
		self.assertNotIn("Page title", html)
		self.assertNotIn("One line under the title.", html)

	def test_the_first_section_decides(self):
		"""An h1 further down the page is not the page's top."""
		later = page(section(text("h2", "Intro")), section(text("h1", "Late title")))
		self.assertFalse(page_header._opens_with_own_title(later))
		hidden_first = page(section(text("h1", "Hidden"), display="none"), section(text("h2", "Shown")))
		self.assertFalse(page_header._opens_with_own_title(hidden_first))
		inline = page(section(text("div", "<h1 class='big'>Inline title</h1>")))
		self.assertTrue(page_header._opens_with_own_title(inline))
		for unreadable in ("not json", None, "{}"):
			self.assertFalse(page_header._opens_with_own_title(unreadable))

	def test_a_frappe_page_band_carries_no_script(self):
		"""frappe hoists a web template's <script> tags without their type: the trail's JSON-LD
		ran as JavaScript on every page that went through the Site Header template."""
		previous = (getattr(frappe.local, "page_header_route", None), getattr(frappe.local, "page_header_context", None))
		frappe.local.page_header_route = "shop/boards"
		frappe.local.page_header_context = frappe._dict(title="Boards")
		try:
			with patch.object(page_header, "settings", return_value=dict(page_header.DEFAULTS)):
				band = page_header.render_page_header()
				head = page_header.breadcrumb_ld(frappe.local.page_header_context)
		finally:
			frappe.local.page_header_route, frappe.local.page_header_context = previous
		self.assertIn('class="site-page-header', band)
		self.assertNotIn("<script", band)
		self.assertEqual(trail_of(head), [frappe._("Home"), "Shop", "Boards"])

	def test_the_head_of_a_frappe_page_gets_the_trail(self):
		from builder.overrides import site_chrome

		previous = (getattr(frappe.local, "page_header_route", None), getattr(frappe.local, "page_header_context", None))
		frappe.local.page_header_route = "shop/boards"
		try:
			with (
				patch("builder.hf_utils.header_footer.get_header_footer_config", return_value=frappe._dict(header_layout="Logo | Menu Center | Icons")),
				patch.object(page_header, "settings", return_value=dict(page_header.DEFAULTS)),
			):
				listing = frappe._dict(title="Boards", head_include="<meta name='x'>")
				site_chrome._inject_config_chrome(listing)
				builder_page = frappe._dict(title="About", doc=frappe._dict(doctype="Builder Page"))
				site_chrome._inject_config_chrome(builder_page)
		finally:
			frappe.local.page_header_route, frappe.local.page_header_context = previous
		self.assertTrue(listing.head_include.startswith("<meta name='x'>"))
		self.assertEqual(trail_of(listing.head_include), [frappe._("Home"), "Shop", "Boards"])
		# a Builder page carries its trail in its own band
		self.assertNotIn("ld+json", builder_page.get("head_include") or "")

	def test_a_frappe_page_carries_the_trail_too(self):
		"""A listing frappe renders gets the same trail, walked from its route."""
		previous = getattr(frappe.local, "page_header_route", None)
		frappe.local.page_header_route = "shop/boards"
		try:
			with patch.object(page_header, "settings", return_value=dict(page_header.DEFAULTS)):
				html = page_header.render(frappe._dict(title="Boards"))
		finally:
			frappe.local.page_header_route = previous
		self.assertIn('class="site-page-header', html)
		self.assertEqual(trail_of(html), [frappe._("Home"), "Shop", "Boards"])

	def test_the_trail_sits_in_the_page_top_under_its_title(self):
		"""The trail of a page opening on its own title sat in a strip of its own above that top, on the
		band's ground, and read as a separate bar (2026-09-14). It now sits under the title."""
		html = self.placed(OWN_TOP)
		nav = nav_of(html)
		self.assertIsNotNone(nav)
		self.assertIn('<h1 class="t">What we do</h1><style>', html)
		self.assertEqual(html.count('class="site-page-crumbs"'), 1)
		self.assertIn(f'<a href="/">{frappe._("Home")}</a>', nav)
		self.assertIn('<span aria-current="page">Services</span>', nav)
		self.assertLess(html.index("</nav>"), html.index("From the market"))

	def test_the_rule_under_the_title_stays_with_it(self):
		html = self.placed(RULED_TOP)
		self.assertIn('<div class="rule"></div><style>', html)
		nav = nav_of(html)
		self.assertIn("color:#a67c00;", nav)
		self.assertIn("justify-content:center;", nav)
		self.assertIn("--sph-body-font:'DM Sans', sans-serif;", nav)

	def test_no_trail_under_the_title_where_the_band_draws_it_or_nothing_should(self):
		self.assertEqual(self.placed(CONTENT_FIRST), TOP_MARKUP)
		self.assertEqual(self.placed(OWN_TOP, show_breadcrumbs=0), TOP_MARKUP)
		self.assertEqual(self.placed(OWN_TOP, page_header_template="None"), TOP_MARKUP)
		self.assertEqual(self.placed(OWN_TOP, fields={"hide_page_header": 1}), TOP_MARKUP)
		self.assertEqual(self.placed(OWN_TOP, fields={"is_template": 1}), TOP_MARKUP)
		self.assertEqual(self.placed(OWN_TOP, title="Home", route="home"), TOP_MARKUP)
		self.assertEqual(self.placed(OWN_TOP, content="<p>No title</p>"), "<p>No title</p>")

	def test_the_trail_under_the_title_cannot_open_markup(self):
		nav = nav_of(self.placed(OWN_TOP, title="Tips <script>alert(1)</script>", route="tips"))
		self.assertNotIn("<script", nav)
		self.assertIn("&lt;script&gt;", nav)
		leaking = page(section(text("h1", "T", color="red;background:url(//x.test/a.png)")))
		self.assertNotIn("url(", nav_of(self.placed(leaking, content="<h1>T</h1>", title="T", route="t")))

	def test_the_404_draws_no_trail(self):
		"""A wrong address read "Home > Shop > Page not found": frappe's web.html drew the shop's breadcrumb
		under the 404's own statement."""
		import importlib

		not_found = importlib.import_module("builder.www.404")
		context = frappe._dict()
		with patch("builder.hf_utils.header_footer.get_header_footer_config", return_value=None):
			not_found.get_context(context)
		self.assertEqual(context.no_breadcrumbs, 1)
		self.assertIs(context.show_page_header, False)
