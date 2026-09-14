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


def trail_of(html):
	"""The names in the page's BreadcrumbList JSON-LD, or None when there is none."""
	found = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
	if not found:
		return None
	data = json.loads(found.group(1))
	return [item["name"] for item in data["itemListElement"]]


class TestPageTop(unittest.TestCase):
	def band(self, blocks, title="Services", route="services", **config):
		doc = frappe._dict(route=route, page_title=title, blocks=blocks)
		with (
			patch.object(page_header, "_config", return_value=None),
			patch.object(page_header, "settings", return_value=dict(page_header.DEFAULTS, **config)),
		):
			return page_header.render_builder_page_header(doc)

	def test_a_page_opening_on_its_own_title_gets_no_second_one(self):
		"""A services page drew "Services" in the band, then its own "Our services": two h1."""
		html = self.band(OWN_TOP)
		self.assertNotIn("<h1", html)
		self.assertNotIn("site-page-header", html)
		# the trail stays for the search engines
		self.assertEqual(trail_of(html), [frappe._("Home"), "Services"])

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
