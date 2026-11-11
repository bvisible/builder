# //// Neoffice — added file (no upstream equivalent): the band at the top of a Builder page goes after a
# //// navigation the page draws itself, so the page title never sits above the site's menu
# //// (builder/page_header.py place_page_band, neoffice-maintenance#2115).
import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.website.serve import get_response_content

from builder import page_header
from builder.utils import Block

BAND = '<div class="site-page-header"><h1 class="site-page-header__title">Shop</h1></div>'
OWN_MENU = (
	'<div class="builder-page-content page-x">'
	'<div class="menu-block"><script>var tpl = "<div>";</script>'
	'<header class="nav"><nav><ul><li><a href="/">Home</a><li><a href="/shop">Shop</a></ul></nav></header>'
	"</div>"
	"<section><h2>Our selection</h2><div><p>Boards</p></div></section>"
	"</div>"
)


class TestPlacePageBand(unittest.TestCase):
	def test_the_band_follows_a_menu_the_page_draws_itself(self):
		html = page_header.place_page_band(OWN_MENU, BAND)
		self.assertLess(html.index("</header>"), html.index(BAND))
		self.assertLess(html.index(BAND), html.index("Our selection"))
		# right after the menu's own block, not inside it: the block closes before the band opens
		self.assertEqual(html[html.index(BAND) - len("</div>") : html.index(BAND)], "</div>")

	def test_a_page_opening_on_its_content_keeps_the_band_first(self):
		content = '<div class="builder-page-content"><section><h2>Our selection</h2></section></div>'
		self.assertEqual(page_header.place_page_band(content, BAND), BAND + content)

	def test_a_first_section_with_its_own_title_is_not_a_menu(self):
		content = (
			'<div class="builder-page-content"><section><nav><a href="/">Home</a></nav>'
			"<h1>Welcome</h1></section></div>"
		)
		self.assertEqual(page_header.place_page_band(content, BAND), BAND + content)

	def test_no_band_leaves_the_page_as_it_is(self):
		self.assertEqual(page_header.place_page_band(OWN_MENU, ""), OWN_MENU)


ROUTE = "test-band-after-own-menu"


def delete_test_pages():
	# frappe names a Builder Page itself (page-<hash>): the route is what the test knows it by
	for name in frappe.get_all("Builder Page", {"route": ROUTE}, pluck="name"):
		frappe.delete_doc("Builder Page", name, force=True)


class TestPageBandOrderOnARealPage(FrappeTestCase):
	"""The order of the elements in the page a visitor gets."""

	def setUp(self):
		delete_test_pages()
		frappe.get_doc(
			{
				"doctype": "Builder Page",
				"page_title": "Band order",
				"published": 1,
				"route": ROUTE,
				"blocks": Block(
					element="div",
					originalElement="body",
					children=[
						Block(
							element="header",
							children=[Block(element="nav", innerHTML="Menu of the page")],
						),
						Block(element="section", children=[Block(element="h2", innerHTML="First section")]),
					],
				).as_json(wrap_in_array=True),
			}
		).insert()

	def tearDown(self):
		delete_test_pages()

	def test_the_title_band_comes_after_the_menu_the_page_draws(self):
		with (
			patch.object(page_header, "_config", return_value=None),
			patch.object(page_header, "settings", return_value=dict(page_header.DEFAULTS)),
		):
			html = get_response_content(f"/{ROUTE}")
		title = html.index('class="site-page-header__title"')
		self.assertLess(html.index("Menu of the page"), title)
		self.assertLess(title, html.index("First section"))
