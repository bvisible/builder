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

	def test_a_category_link_under_a_section_path_goes_to_the_listing(self):
		"""The seventh build linked its home tiles to /culture/snow and the like, and the repair
		sent all five to the contact form."""
		from builder.site_ai.nora.buttons import repair_data_routes, repair_foreign_links

		routes = ["/", "/brands", "/about", "/contact"]
		blocks = [{"attributes": {"href": "/culture/snow"}, "children": []}, {"attributes": {"href": "/pricing/plans"}, "children": []}]
		repair_foreign_links(blocks, routes, "/contact", categories=["Snow"], listing="/brands")
		self.assertEqual([b["attributes"]["href"] for b in blocks], ["/brands", "/contact"])
		script = 'data.tiles = [{"name": "Street", "route": "/culture/street"}]'
		fixed, edits = repair_data_routes(script, routes, "/contact", categories=["Street"], listing="/brands")
		self.assertIn('"route": "/brands"', fixed)
		self.assertEqual(len(edits), 1)

	def test_a_bind_to_a_css_property_binds_a_style(self):
		"""A tile's photograph bound as backgroundImage went out as an HTML attribute and the
		tile rendered empty."""
		from builder.ai.page_writer import convert_yaml_block

		block = convert_yaml_block({"el": "a", "bind": {"backgroundImage": "image", "href": "href", "text": "label"}})
		bound = {(d["property"], d["type"]) for d in block["dynamicValues"]}
		self.assertEqual(bound, {("backgroundImage", "style"), ("href", "attribute"), ("innerHTML", "key")})

	def test_an_unverified_business_gets_no_made_up_contact_details(self):
		"""Asked for "clearly generic placeholders", the model wrote a real street and a plausible
		phone number, different at each build, on a contact page published at once."""
		from builder.site_ai.nora.site_builder import UNVERIFIED_CONTACT, page_sections

		self.assertIn("not even a placeholder", UNVERIFIED_CONTACT)
		self.assertNotIn("+41", UNVERIFIED_CONTACT)
		contact = {"title": "Contact", "route": "contact", "type": "contact"}
		self.assertTrue(any("contact details" in s for s in page_sections(contact, minimal=False, contact_verified=True)))
		self.assertFalse(any("contact details" in s for s in page_sections(contact, minimal=False, contact_verified=False)))
		self.assertFalse(any("contact details" in s for s in page_sections(contact, minimal=True, contact_verified=False)))

	def test_a_contact_page_is_offered_no_include_with_nothing_to_show(self):
		"""A contact page carried a map with no address ("Map placeholder - configure address"
		for every visitor) and an hours block with no hours."""
		from unittest.mock import patch

		from builder.site_ai.nora import site_builder

		def offered(address, hours):
			with (
				patch.object(site_builder.frappe, "get_installed_apps", return_value=["frappe", "builder", "webshop"]),
				patch("builder.empty_includes.site_has_address", return_value=address),
				patch("builder.empty_includes.opening_hours_configured", return_value=hours),
			):
				return " ".join(tag for tag, _ in site_builder.available_includes("contact"))

		self.assertNotIn("google_map", offered(address=False, hours=True))
		self.assertNotIn("opening_hours", offered(address=True, hours=False))
		both = offered(address=True, hours=True)
		self.assertIn("google_map", both)
		self.assertIn("opening_hours", both)
		self.assertIn("contact_form", offered(address=False, hours=False))

	def test_an_about_page_is_offered_no_empty_team_or_timeline(self):
		"""The about pages of a reseller site carried a team heading over no one and a "key
		figures" heading over no milestone: About Us Settings was empty."""
		from unittest.mock import patch

		from builder.site_ai.nora import site_builder

		def offered(rows):
			with (
				patch.object(site_builder.frappe, "get_installed_apps", return_value=["frappe", "builder"]),
				patch("builder.empty_includes.about_us_rows", side_effect=lambda field: field in rows),
			):
				return " ".join(tag for tag, _ in site_builder.available_includes("about"))

		self.assertEqual(offered(set()), "")
		self.assertIn("team_grid", offered({"team_members"}))
		self.assertNotIn("company_timeline", offered({"team_members"}))
		both = offered({"team_members", "company_history"})
		self.assertIn("team_grid", both)
		self.assertIn("company_timeline", both)

	def test_the_build_progress_never_goes_back(self):
		"""The panel read "Reading the inspirations" through the design brief's minutes of
		thinking: the brief was announced before the inspirations and the photos were read,
		and the bar went 8, 6, 7 (2026-09-11)."""
		import inspect
		import re

		from builder.site_ai.nora import site_builder

		pattern = r'_progress\(ctx, job_id, _\("[^"]+"\)(?:\.format\([^)]*\))?, (\d+)'
		steps = [int(n) for n in re.findall(pattern, inspect.getsource(site_builder))]
		self.assertGreaterEqual(len(steps), 4)
		self.assertEqual(steps, sorted(steps))

	def test_a_page_is_told_the_headlines_the_others_used(self):
		"""The pages are written one at a time, and "Five cultures, one collective." opened the
		home, then Brands, then About (2026-09-13)."""
		from types import SimpleNamespace

		from builder.site_ai.nora.site_builder import page_brief_text, page_headlines

		home = [
			{
				"element": "div",
				"children": [
					{"element": "h1", "innerHTML": "Five cultures, one collective."},
					{"element": "h2", "innerHTML": "Snow"},
					{"element": "h2", "innerHTML": "Join the collective today"},
				],
			}
		]
		used = page_headlines(home, ["Snow"])
		self.assertEqual(used, ["Five cultures, one collective.", "Join the collective today"])
		site = {"site_name": "X", "activity": "Y", "headlines_by_route": {"home": used, "brands": ["Bring your brand in"]}}
		handles = {k: "var(--x)" for k in ("primary", "secondary", "background", "text", "font-heading", "font-body")}
		page = {"title": "Brands", "route": "brands", "type": "about"}
		text = page_brief_text(site, SimpleNamespace(), page, handles, "", "bento", "English", [], ("Contact us", "/contact"))
		self.assertIn("'Five cultures, one collective.'", text)
		# its own headlines are not held against it (a revision keeps them)
		self.assertNotIn("Bring your brand in", text)

	def test_the_page_the_call_to_action_leads_to_carries_none(self):
		"""The Contact page closed on a "Contact us" button to itself, under its own form
		(2026-09-13)."""
		from types import SimpleNamespace

		from builder.site_ai.nora.site_builder import page_brief_text

		handles = {k: "var(--x)" for k in ("primary", "secondary", "background", "text", "font-heading", "font-body")}
		site = {"site_name": "X", "activity": "Y"}
		cta = ("Contact us", "/contact")
		contact = page_brief_text(site, SimpleNamespace(), {"title": "Contact", "route": "contact", "type": "contact"}, handles, "", "bento", "English", [], cta)
		about = page_brief_text(site, SimpleNamespace(), {"title": "About", "route": "about", "type": "about"}, handles, "", "bento", "English", [], cta)
		self.assertIn("no button to it", contact)
		self.assertIn("links to '/contact'", about)

	def test_every_page_knows_the_categories_by_name(self):
		"""About and Contact invented sets of five of their own ("Gather, Studio, Trail…"),
		beside five categories that were Snow, Street, Water, Outdoor and Home (2026-09-13)."""
		from types import SimpleNamespace

		from builder.site_ai.nora.site_builder import page_brief_text

		handles = {k: "var(--x)" for k in ("primary", "secondary", "background", "text", "font-heading", "font-body")}
		site = {"site_name": "X", "activity": "Y", "categories": ["Snow", "Street", "Water"], "listing_route": "brands"}
		about = page_brief_text(site, SimpleNamespace(), {"title": "About", "route": "about", "type": "about"}, handles, "", "bento", "English", [], ("Contact us", "/contact"))
		self.assertIn("Snow, Street, Water", about)
		self.assertIn("never a set of its own", about)
		# the home keeps its tile order
		home = page_brief_text(site, SimpleNamespace(), {"title": "Home", "route": "home", "type": "accueil"}, handles, "", "bento", "English", [], ("Contact us", "/contact"))
		self.assertIn("give each its own photograph tile", home)

	def test_the_brief_forbids_made_up_facts_and_dates_the_page(self):
		"""A practice opening "in October" came out with prices, a testimonial and an opening in
		October 2024 (2026-09-13)."""
		from types import SimpleNamespace

		import frappe

		from builder.site_ai.nora.facts import FACTS_RULE
		from builder.site_ai.nora.site_builder import page_brief_text

		handles = {k: "var(--x)" for k in ("primary", "secondary", "background", "text", "font-heading", "font-body")}
		site = {"site_name": "X", "activity": "Y", "page_types": ["accueil", "services", "pricing"]}
		services = page_brief_text(site, SimpleNamespace(), {"title": "Services", "route": "services", "type": "services"}, handles, "", "bento", "English", [], ("Contact us", "/contact"))
		self.assertIn(FACTS_RULE, services)
		self.assertIn(f"TODAY: {frappe.utils.today()}", services)
		# the pricing page answers the questions and gives the prices, not the services page
		self.assertNotIn("FAQ", services)

	def test_one_page_answers_the_questions_and_one_gives_the_prices(self):
		"""The FAQs of two pages answered the same question two ways, and the services page listed
		packages the pricing page did not have (2026-09-13)."""
		from builder.site_ai.nora.site_builder import page_sections

		services = {"title": "Prestations", "route": "prestations", "type": "services"}
		pricing = {"title": "Tarifs", "route": "tarifs", "type": "pricing"}
		self.assertTrue(any("FAQ" in s for s in page_sections(services, minimal=False)))
		beside_prices = page_sections(services, minimal=False, others=["pricing"])
		self.assertFalse(any("FAQ" in s for s in beside_prices))
		self.assertFalse(any("/ packages" in s for s in beside_prices))
		self.assertIn("FAQ", page_sections(pricing, minimal=False, others=["services"]))
		self.assertNotIn("FAQ", page_sections(pricing, minimal=False, others=["faq"]))

	def test_proof_prices_and_directions_come_from_the_brief(self):
		"""A practice about to open got a patient's testimonial, three prices and a drawn access map
		showing a street address nobody gave (2026-09-13)."""
		from builder.site_ai.nora.site_builder import SECTION_PLANS, page_sections, placeholder_photos

		self.assertTrue(any("only what the brief gives" in s for s in SECTION_PLANS["accueil"]))
		self.assertTrue(any("no amount" in s for s in SECTION_PLANS["pricing"]))
		contact = {"title": "Contact", "route": "contact", "type": "contact"}
		self.assertFalse(any("map" in s for s in page_sections(contact, minimal=False)))
		self.assertFalse(any("find the place" in s for s in page_sections(contact, minimal=False, contact_verified=False)))
		self.assertFalse(any("map" in url for url in placeholder_photos(contact, "Physiothérapie")))

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
