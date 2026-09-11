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

	def test_keep_them_keeps_the_hand_made_pages_only(self):
		"""Answered with 'none', a question about one hand-made page kept the whole
		previous site beside the new one."""
		classes = {"untouched": [{"name": "old-home"}, {"name": "old-contact"}], "protected": [{"name": "promo"}]}
		self.assertEqual(pages_to_replace(classes, "keep_edited"), ["old-home", "old-contact"])
		self.assertEqual(pages_to_replace(classes, "auto"), ["old-home", "old-contact"])
		self.assertEqual(pages_to_replace(classes, "force"), ["old-home", "old-contact", "promo"])
		self.assertEqual(pages_to_replace(classes, "none"), [])
