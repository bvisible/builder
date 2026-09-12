# //// Neoffice — added file (no upstream equivalent): a site built beside pages it keeps.
import unittest

from builder.site_ai.nora.buttons import remap_routes
from builder.site_ai.nora.site_builder import moved_routes, pages_by_name, pages_to_replace

PLAN = [
	{"title": "Home", "route": "home", "type": "accueil"},
	{"title": "Brands", "route": "brands", "type": "generic"},
	{"title": "About", "route": "about", "type": "about"},
	{"title": "Contact", "route": "contact", "type": "contact"},
]
# what a build beside kept pages wrote: three routes were taken and got a suffix
CREATED = [
	{"name": "p-home", "title": "Home", "route": "/home-4a0a", "planned": "home"},
	{"name": "p-brands", "title": "Brands", "route": "/brands", "planned": "brands"},
	{"name": "p-about", "title": "About", "route": "/about-d0ec", "planned": "about"},
	{"name": "p-contact", "title": "Contact", "route": "/contact-ade5", "planned": "contact"},
]


class TestBesideKeptPages(unittest.TestCase):
	def test_every_written_page_is_found_for_its_revision(self):
		"""Matched on the suffixed routes, three pages of four skipped the visual check's
		revision pass."""
		self.assertEqual([p["name"] for p in pages_by_name(PLAN, CREATED)], ["p-home", "p-brands", "p-about", "p-contact"])

	def test_the_suffixed_pages_are_the_moved_ones(self):
		self.assertEqual(
			moved_routes(CREATED),
			{"/home": "/home-4a0a", "/": "/home-4a0a", "/about": "/about-d0ec", "/contact": "/contact-ade5"},
		)
		self.assertEqual(moved_routes([{"name": "h", "title": "Home", "route": "/home", "planned": "home"}]), {})

	def test_links_follow_their_pages(self):
		blocks = [
			{
				"attributes": {"href": "/contact"},
				"children": [
					{"attributes": {"href": "/contact#form"}},
					{"attributes": {"href": "/contact-us"}},
					{"attributes": {"href": "/brands"}},
					{"attributes": {"href": "https://example.test/contact"}},
					{"innerHTML": '<p>Write to <a href="/contact?topic=b2b">us</a> or see <a href="/about">who we are</a></p>'},
				],
			}
		]
		edits = remap_routes(blocks, moved_routes(CREATED))
		kids = blocks[0]["children"]
		self.assertEqual(blocks[0]["attributes"]["href"], "/contact-ade5")
		self.assertEqual(kids[0]["attributes"]["href"], "/contact-ade5#form")
		self.assertEqual(kids[1]["attributes"]["href"], "/contact-us")
		self.assertEqual(kids[2]["attributes"]["href"], "/brands")
		self.assertEqual(kids[3]["attributes"]["href"], "https://example.test/contact")
		self.assertIn('href="/contact-ade5?topic=b2b"', kids[4]["innerHTML"])
		self.assertIn('href="/about-d0ec"', kids[4]["innerHTML"])
		self.assertEqual(len(edits), 4)

	def test_a_category_link_goes_to_the_page_that_lists(self):
		"""The five category tiles of a new site linked to pages it does not have, and the
		repair sent all of them to the contact form."""
		from builder.site_ai.nora.buttons import repair_foreign_links

		routes = ["/", "/brands", "/about", "/contact"]
		blocks = [
			{"attributes": {"href": "/snow"}, "children": []},
			{"attributes": {"href": "/outdoor"}, "children": [{"innerHTML": "Outdoor"}]},
			{"attributes": {"href": "/pricing"}, "children": [{"innerHTML": "Get a quote"}]},
		]
		repair_foreign_links(blocks, routes, "/contact", categories=["Snow", "Street", "Outdoor"], listing="/brands")
		self.assertEqual([b["attributes"]["href"] for b in blocks[:2]], ["/brands", "/brands"])
		self.assertEqual(blocks[2]["attributes"]["href"], "/contact")
		# without a page that lists, the call to action stays the fallback
		lone = [{"attributes": {"href": "/snow"}, "children": []}]
		repair_foreign_links(lone, routes, "/contact", categories=["Snow"], listing=None)
		self.assertEqual(lone[0]["attributes"]["href"], "/contact")

	def test_a_bind_written_inside_attrs_binds(self):
		"""A repeated tile's image and link carried their bind inside `attrs`, bound nothing,
		and rendered as an empty frame and a dead link."""
		from builder.ai.page_writer import convert_yaml_block

		block = convert_yaml_block({"el": "img", "attrs": {"bind": {"src": "image", "alt": "alt"}, "loading": "lazy"}})
		self.assertEqual(block["attributes"], {"loading": "lazy"})
		bound = {(d["property"], d["key"], d["type"]) for d in block["dynamicValues"]}
		self.assertEqual(bound, {("src", "image", "attribute"), ("alt", "alt", "attribute")})

	def test_the_data_script_s_routes_are_checked_too(self):
		from builder.site_ai.nora.buttons import repair_data_routes

		script = 'data.categories = [{"name": "Snow", "route": "/snow"}, {"name": "About us", "route": "/about"}, {"name": "Quote", "href": "/pricing"}]'
		fixed, edits = repair_data_routes(script, ["/", "/brands", "/about", "/contact"], "/contact", categories=["Snow"], listing="/brands")
		self.assertIn('"route": "/brands"', fixed)
		self.assertIn('"route": "/about"', fixed)
		self.assertIn('"href": "/contact"', fixed)
		self.assertEqual(len(edits), 2)

	def test_a_link_bound_under_any_key_is_checked(self):
		"""One build's category tiles linked through a key named `slug`, which the usual link
		names did not cover: /snow and /home-burrow stayed dead links."""
		from builder.site_ai.nora.buttons import repair_data_routes

		blocks = [{"element": "a", "dynamicValues": [{"key": "slug", "property": "href", "type": "attribute"}], "children": []}]
		script = 'data.categories = [{"name": "Snow", "slug": "/snow"}, {"name": "Home", "slug": "/home-burrow"}]'
		fixed, edits = repair_data_routes(script, ["/", "/brands", "/contact"], "/contact", categories=["Snow", "Home"], listing="/brands", blocks=blocks)
		self.assertEqual(fixed.count('"slug": "/brands"'), 2)
		self.assertEqual(len(edits), 2)

	def test_keep_them_keeps_the_hand_made_pages_only(self):
		"""Answered with 'none', a question about one hand-made page kept the whole
		previous site beside the new one."""
		classes = {"untouched": [{"name": "old-home"}, {"name": "old-contact"}], "protected": [{"name": "promo"}]}
		self.assertEqual(pages_to_replace(classes, "keep_edited"), ["old-home", "old-contact"])
		self.assertEqual(pages_to_replace(classes, "auto"), ["old-home", "old-contact"])
		self.assertEqual(pages_to_replace(classes, "force"), ["old-home", "old-contact", "promo"])
		self.assertEqual(pages_to_replace(classes, "none"), [])

	def test_a_page_description_leaves_jinja_out(self):
		"""A contact page whose first text was its form's include printed the include tag under
		its title."""
		from builder.api import _describe_page

		blocks = [
			{"element": "div", "innerHTML": "{% include 'builder/templates/includes/contact_form.html' %}", "children": []},
			{"element": "p", "innerHTML": "Write to us about a collaboration, a shoot or a drop.", "children": []},
		]
		self.assertEqual(_describe_page(blocks), "Write to us about a collaboration, a shoot or a drop.")

	def test_the_site_remembers_its_language(self):
		"""An English site built on a French instance showed "Accueil" and a French contact
		form: the profile keeps the language the site was written in, for the theme."""
		from unittest.mock import patch

		from builder.site_ai.nora import site_builder

		db = site_builder.frappe.db
		with patch.object(db, "has_column", return_value=True), patch.object(db, "exists", return_value=True), patch.object(db, "set_value") as set_value:
			self.assertTrue(site_builder.remember_site_language("Test Profile", "en"))
			set_value.assert_called_once_with("Website Profile", "Test Profile", "language", "en")
		with patch.object(db, "has_column", return_value=False), patch.object(db, "set_value") as set_value:
			self.assertFalse(site_builder.remember_site_language("Test Profile", "en"))
			set_value.assert_not_called()
		self.assertFalse(site_builder.remember_site_language(None, "en"))
