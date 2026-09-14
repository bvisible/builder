# //// Neoffice — added file (no upstream equivalent): the page repairs of 2026-09-14. Placeholders are
# //// dropped, an opaque layer over a photo becomes a veil, lettering painted with a photo gets its
# //// ink back, grids are balanced, a brands page lists the brands, and the chrome variant is served fresh.
import unittest
from unittest.mock import patch

import frappe

from builder.site_ai.nora.contrast import repair_contrast, repair_opaque_overlays
from builder.site_ai.nora.facts import drop_placeholders
from builder.site_ai.nora.layout import balance_grids, phone_columns
from builder.site_ai.nora.site_builder import brands_page, page_sections

PALETTE = {"xx-background": "#ffffff", "xx-text": "#111111", "xx-primary": "#111111", "xx-secondary": "#eeeeee"}


def text(element, html, **styles):
	return {"element": element, "innerHTML": html, "baseStyles": styles, "children": []}


def box(*children, **styles):
	return {"element": "div", "baseStyles": styles, "children": list(children)}


class TestPlaceholders(unittest.TestCase):
	"""A contact page printed "[email address]" and "[website]" under their labels."""

	def test_a_placeholder_goes_with_its_label_and_its_empty_wrapper(self):
		page = [
			box(
				text("h2", "Get in touch"),
				box(text("p", "EMAIL"), text("p", "[email address]")),
				box(text("p", "PHONE"), text("p", "+41 00 000 00 00")),
			)
		]
		edits = drop_placeholders(page)
		kids = page[0]["children"]
		self.assertEqual([k.get("innerHTML") for k in kids], ["Get in touch", None])
		self.assertEqual([c["innerHTML"] for c in kids[1]["children"]], ["PHONE", "+41 00 000 00 00"])
		self.assertTrue(any("EMAIL" in e for e in edits))

	def test_inside_a_longer_line_only_the_placeholder_is_cut(self):
		line = text("p", "Atelier Nord Sàrl · [website] · Lausanne")
		drop_placeholders([box(line)])
		self.assertEqual(line["innerHTML"], "Atelier Nord Sàrl · Lausanne")

	def test_jinja_and_footnotes_are_left_alone(self):
		include = text("div", "{% include 'builder/templates/includes/contact_form.html' %} [x]")
		note = text("p", "See the terms [1].")
		drop_placeholders([box(include, note)])
		self.assertIn("[x]", include["innerHTML"])
		self.assertEqual(note["innerHTML"], "See the terms [1].")


class TestInventedContacts(unittest.TestCase):
	"""Told to leave out what it did not have, the model wrote an e-mail and a website that do not exist."""

	KNOWN = "BUSINESS DATA: Atelier Nord Sàrl, Lausanne, +41 21 000 00 00, hello@atelier-nord.test"

	def test_a_detail_the_data_does_not_give_goes_with_its_label(self):
		page = [
			box(
				box(text("p", "PHONE"), text("p", "+41 21 000 00 00")),
				box(text("p", "EMAIL"), text("p", "info@made-up.ch")),
				box(text("p", "WEBSITE"), text("p", "made-up.ch")),
			)
		]
		from builder.site_ai.nora.facts import drop_invented_contacts

		edits = drop_invented_contacts(page, self.KNOWN)
		kids = page[0]["children"]
		self.assertEqual(len(kids), 1)
		self.assertEqual([c["innerHTML"] for c in kids[0]["children"]], ["PHONE", "+41 21 000 00 00"])
		self.assertTrue(any("EMAIL" in e for e in edits))

	def test_what_the_data_gives_stays_and_a_detail_is_cut_from_a_line(self):
		from builder.site_ai.nora.facts import drop_invented_contacts, invented_contacts

		self.assertEqual(invented_contacts("Write to hello@atelier-nord.test or call +41 21 000 00 00", self.KNOWN), [])
		line = text("p", 'Atelier Nord Sàrl · <a href="https://made-up.ch">made-up.ch</a> · Lausanne')
		drop_invented_contacts([box(line)], self.KNOWN)
		self.assertNotIn("made-up.ch", line["innerHTML"])
		self.assertIn("Lausanne", line["innerHTML"])


class TestCopyOnPhotos(unittest.TestCase):
	"""Photo cards put white titles straight on light photographs, with no veil."""

	def card(self, *extra, classes=None):
		return {
			"element": "a",
			"classes": classes or ["u-media"],
			"baseStyles": {"position": "relative"},
			"children": [
				{"element": "img", "attributes": {"src": "/files/a.jpg"}, "baseStyles": {"position": "absolute", "inset": "0", "objectFit": "cover"}, "children": []},
				*extra,
				text("h2", "Street", color="#ffffff"),
			],
		}

	def test_copy_on_a_photo_gets_the_scrim(self):
		from builder.site_ai.nora.contrast import veil_copy_on_photos

		card = self.card()
		self.assertEqual(len(veil_copy_on_photos([card])), 1)
		self.assertIn("u-over-image", card["classes"])
		self.assertIn("u-over-image--bottom", card["classes"])

	def test_a_card_with_a_veil_or_the_class_is_left_alone(self):
		from builder.site_ai.nora.contrast import veil_copy_on_photos

		veiled = self.card({"element": "div", "baseStyles": {"position": "absolute", "inset": "0", "background": "linear-gradient(to top, rgba(0,0,0,.6), transparent)"}, "children": []})
		self.assertEqual(veil_copy_on_photos([veiled]), [])
		self.assertEqual(veil_copy_on_photos([self.card(classes=["u-over-image"])]), [])


class TestSiteTypeWords(unittest.TestCase):
	def test_the_brief_names_the_site_type_in_words(self):
		from builder.site_ai.generators.brief_generator import SITE_TYPE_WORDS

		self.assertEqual(SITE_TYPE_WORDS["vitrine"], "a showcase website")
		self.assertNotIn("vitrine", " ".join(SITE_TYPE_WORDS.values()))


class TestVeils(unittest.TestCase):
	"""A contact page covered its photograph with an opaque black layer."""

	def photo(self, **veil):
		return box(
			{"element": "img", "attributes": {"src": "/files/a.jpg"}, "baseStyles": {"position": "absolute", "objectFit": "cover"}, "children": []},
			{"element": "div", "baseStyles": {"position": "absolute", "inset": "0", **veil}, "children": []},
			position="relative",
		)

	def test_an_opaque_layer_over_a_photo_becomes_a_scrim(self):
		section = self.photo(backgroundColor="var(--xx-text)")
		self.assertEqual(len(repair_opaque_overlays([section], PALETTE)), 1)
		veil = section["children"][1]["baseStyles"]
		self.assertNotIn("backgroundColor", veil)
		self.assertIn("linear-gradient(to top, rgba(17,17,17,0.62)", veil["background"])

	def test_a_veil_a_blend_or_a_caption_is_left_alone(self):
		for veil in (
			{"backgroundColor": "rgba(0,0,0,0.4)"},
			{"backgroundColor": "#000", "opacity": "0.5"},
			{"backgroundColor": "#000", "mixBlendMode": "multiply"},
		):
			self.assertEqual(repair_opaque_overlays([self.photo(**veil)], PALETTE), [], veil)
		caption = self.photo(backgroundColor="#000")
		caption["children"][1]["children"] = [text("p", "Snow")]
		self.assertEqual(repair_opaque_overlays([caption], PALETTE), [])


class TestPhotoLettering(unittest.TestCase):
	"""Brand tiles on a black site painted their names with the photograph: near-black on black."""

	def test_letters_painted_with_a_photo_take_the_band_ink(self):
		name = text("h2", "Outdoor", color="transparent", background="url(/files/a.jpg)", backgroundClip="text", WebkitBackgroundClip="text")
		fixes = repair_contrast([box(name, backgroundColor="#000000")], PALETTE)
		styles = name["baseStyles"]
		self.assertTrue(any("photo lettering" in f for f in fixes))
		self.assertNotIn("background", styles)
		self.assertNotIn("backgroundClip", styles)
		self.assertEqual(styles["color"], "var(--xx-background)")

	def test_plain_text_is_not_lettering(self):
		title = text("h2", "Snow", color="var(--xx-text)")
		repair_contrast([box(title)], PALETTE)
		self.assertEqual(title["baseStyles"]["color"], "var(--xx-text)")


class TestBalancedGrids(unittest.TestCase):
	"""Five photo tiles on three columns left the sixth cell of a home empty."""

	def grid(self, columns):
		return {
			"element": "div",
			"isRepeaterBlock": True,
			"dataKey": {"key": "categories"},
			"baseStyles": {"display": "grid", "gridTemplateColumns": f"repeat({columns}, 1fr)"},
			"children": [box(text("h3", "x"))],
		}

	def test_five_rows_on_three_columns_take_one_row(self):
		grid = self.grid(3)
		self.assertEqual(balance_grids([grid], {"categories": 5}), 1)
		self.assertEqual(grid["baseStyles"]["gridTemplateColumns"], "repeat(5, minmax(0, 1fr))")

	def test_the_row_of_five_gets_two_columns_on_the_phone(self):
		"""The row of five kept its five columns on a 390 px phone: 50 px tiles, labels cut."""
		grid = self.grid(3)
		balance_grids([grid], {"categories": 5})
		self.assertEqual(grid["mobileStyles"]["gridTemplateColumns"], "repeat(2, minmax(0, 1fr))")
		self.assertNotIn("gridTemplateColumns", grid.get("tabletStyles") or {})

	def test_six_on_four_columns_get_three_on_the_tablet(self):
		grid = self.grid(4)
		balance_grids([grid], {"categories": 6})
		self.assertEqual(grid["baseStyles"]["gridTemplateColumns"], "repeat(6, minmax(0, 1fr))")
		self.assertEqual(grid["tabletStyles"]["gridTemplateColumns"], "repeat(3, minmax(0, 1fr))")
		self.assertEqual(grid["mobileStyles"]["gridTemplateColumns"], "repeat(2, minmax(0, 1fr))")

	def test_the_columns_a_page_wrote_for_the_phone_stay(self):
		grid = self.grid(3)
		grid["mobileStyles"] = {"gridTemplateColumns": "1fr"}
		balance_grids([grid], {"categories": 5})
		self.assertEqual(grid["mobileStyles"]["gridTemplateColumns"], "1fr")

	def test_a_grid_that_fills_its_rows_or_is_long_stays(self):
		for count in (6, 7, 9):
			self.assertEqual(balance_grids([self.grid(3)], {"categories": count}), 0, count)

	def test_the_children_count_when_there_is_no_data(self):
		grid = box(box(), box(), display="grid", gridTemplateColumns="repeat(3, minmax(0, 1fr))")
		self.assertEqual(balance_grids([grid]), 1)
		self.assertEqual(grid["baseStyles"]["gridTemplateColumns"], "repeat(2, minmax(0, 1fr))")


	def test_a_class_drawn_grid_fills_its_last_row(self):
		"""A brands page's category tiles, drawn by u-grid u-grid--3, kept their sixth cell empty."""
		grid = {"element": "div", "isRepeaterBlock": True, "dataKey": {"key": "categories"}, "classes": ["u-grid", "u-grid--3"], "baseStyles": {}, "children": [box()]}
		self.assertEqual(balance_grids([grid], {"categories": 5}), 1)
		self.assertIn("u-grid--fill", grid["classes"])
		full = {"element": "div", "isRepeaterBlock": True, "dataKey": {"key": "categories"}, "classes": ["u-grid", "u-grid--3"], "baseStyles": {}, "children": [box()]}
		self.assertEqual(balance_grids([full], {"categories": 6}), 0)


class TestPhoneColumns(unittest.TestCase):
	"""A grid of equal items written with four columns and nothing for the phone kept four there."""

	def test_four_cards_get_two_columns_on_the_phone(self):
		grid = box(box(), box(), box(), box(), display="grid", gridTemplateColumns="repeat(4, 1fr)")
		self.assertEqual(phone_columns([grid]), 1)
		self.assertEqual(grid["mobileStyles"]["gridTemplateColumns"], "repeat(2, minmax(0, 1fr))")

	def test_three_cards_stack_on_the_phone(self):
		grid = box(box(), box(), box(), display="grid", gridTemplateColumns="1fr 1fr 1fr")
		self.assertEqual(phone_columns([grid]), 1)
		self.assertEqual(grid["mobileStyles"]["gridTemplateColumns"], "minmax(0, 1fr)")

	def test_an_odd_last_card_takes_the_phone_row(self):
		grid = box(box(), box(), box(), box(), box(), display="grid", gridTemplateColumns="repeat(5, minmax(0, 1fr))")
		phone_columns([grid])
		self.assertEqual(grid["children"][-1]["mobileStyles"]["gridColumn"], "1 / -1")
		self.assertNotIn("mobileStyles", grid["children"][0])

	def test_what_the_phone_already_has_stays(self):
		own = box(box(), box(), box(), box(), display="grid", gridTemplateColumns="repeat(4, 1fr)")
		own["mobileStyles"] = {"gridTemplateColumns": "1fr"}
		tablet = box(box(), box(), box(), box(), display="grid", gridTemplateColumns="repeat(4, 1fr)")
		tablet["tabletStyles"] = {"gridTemplateColumns": "repeat(2, 1fr)"}
		self.assertEqual(phone_columns([own, tablet]), 0)
		self.assertEqual(own["mobileStyles"]["gridTemplateColumns"], "1fr")
		self.assertNotIn("mobileStyles", tablet)

	def test_layout_grids_and_placed_children_are_left_alone(self):
		twelve = box(box(gridColumn="1 / span 6"), box(gridColumn="7 / span 6"), display="grid", gridTemplateColumns="repeat(12, 1fr)")
		placed = box(box(gridColumn="1 / 3"), box(), display="grid", gridTemplateColumns="repeat(3, 1fr)")
		fluid = box(box(), box(), box(), display="grid", gridTemplateColumns="repeat(auto-fit, minmax(220px, 1fr))")
		self.assertEqual(phone_columns([twelve, placed, fluid]), 0)

	def test_a_repeater_counts_its_rows(self):
		grid = {"element": "div", "isRepeaterBlock": True, "dataKey": {"key": "brands"}, "baseStyles": {"display": "grid", "gridTemplateColumns": "repeat(4, 1fr)"}, "children": [box()]}
		self.assertEqual(phone_columns([grid], {"brands": 3}), 1)
		self.assertEqual(grid["mobileStyles"]["gridTemplateColumns"], "minmax(0, 1fr)")


class TestBrandsPage(unittest.TestCase):
	"""An image-led brands page laid out the site's segments and named no brand."""

	def test_a_brands_page_lists_the_brands_the_brief_names(self):
		page = {"title": "Brands", "route": "brands", "type": "generic"}
		self.assertTrue(brands_page(page))
		self.assertTrue(page_sections(page, True, brands=("North Boards", "Tide Co"))[0].startswith("the brands the brief names"))
		self.assertIn("the brands the brief names", " ".join(page_sections(page, False, brands=("North Boards",))))

	def test_without_brands_the_page_keeps_its_plan(self):
		page = {"title": "Nos marques", "route": "marques", "type": "generic"}
		self.assertTrue(brands_page(page))
		self.assertNotIn("the brands the brief names", " ".join(page_sections(page, True)))
		self.assertFalse(brands_page({"title": "About", "route": "about", "type": "about"}))


class TestFreshVariant(unittest.TestCase):
	"""After a build rewrote a site's menu, its pages kept the menu of the cached variant."""

	def serve(self, cached_docs, row_modified):
		from builder.hf_utils import header_footer

		with (
			patch.object(frappe, "get_cached_doc", side_effect=cached_docs) as cached,
			patch.object(frappe.db, "get_value", return_value=row_modified),
			patch.object(frappe, "clear_document_cache") as cleared,
		):
			doc = header_footer._fresh_variant("Site B")
		return doc, cached.call_count, cleared

	def test_a_cached_variant_older_than_its_row_is_reloaded(self):
		stale, fresh = frappe._dict(modified="2026-09-14 10:00:00"), frappe._dict(modified="2026-09-14 10:21:00")
		doc, reads, cleared = self.serve([stale, fresh], "2026-09-14 10:21:00")
		self.assertIs(doc, fresh)
		self.assertEqual(reads, 2)
		cleared.assert_called_once_with("Website Header Footer Variant", "Site B")

	def test_a_current_cache_is_served_as_is(self):
		current = frappe._dict(modified="2026-09-14 10:21:00")
		doc, reads, cleared = self.serve([current], "2026-09-14 10:21:00")
		self.assertIs(doc, current)
		self.assertEqual(reads, 1)
		cleared.assert_not_called()
