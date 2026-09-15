# //// Neoffice — added file (no upstream equivalent): the page repairs of 2026-09-14. Placeholders are
# //// dropped, an opaque layer over a photo becomes a veil, lettering painted with a photo gets its
# //// ink back, grids are balanced, a brands page lists the brands, and the chrome variant is served fresh.
import unittest
from unittest.mock import patch

import frappe

from builder.site_ai.nora.contrast import repair_contrast, repair_opaque_overlays
from builder.site_ai.nora.facts import drop_placeholders
from builder.site_ai.nora.layout import (
	balance_grids,
	category_wheel,
	complete_tile_photos,
	fill_last_phone_row,
	phone_columns,
	repeater_rows,
)
from builder.site_ai.nora.site_builder import brands_page, category_photo_map, page_sections

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


TILE_PHOTOS = {"Snow": "/files/snow.jpg", "Street": "/files/street.jpg", "Water": "/files/water.jpg"}


class TestTilePhotos(unittest.TestCase):
	"""An About page showed the five categories as tiles: one on its photograph, four in flat grey."""

	PHOTOS = TILE_PHOTOS

	def tile(self, name, photo=None):
		styles = {"backgroundImage": f"url('{photo}')", "backgroundSize": "cover"} if photo else {"background": "#444444"}
		heading = text("h3", name, color="#ffffff" if photo else "#111111")
		return {"element": "div", "blockId": name, "baseStyles": {**styles, "minHeight": "300px"}, "children": [heading]}

	def grid(self, *tiles):
		return box(*tiles, display="grid", gridTemplateColumns="repeat(5, 1fr)")

	def test_a_flat_tile_takes_its_photograph_and_the_photographed_tile_dress(self):
		grid = self.grid(self.tile("Snow"), self.tile("Street", "/files/street.jpg"), self.tile("Water"))
		self.assertEqual(complete_tile_photos([grid], self.PHOTOS), ["snow", "water"])
		snow = grid["children"][0]
		self.assertEqual(snow["baseStyles"]["backgroundImage"], "url('/files/snow.jpg')")
		self.assertNotIn("background", snow["baseStyles"])
		self.assertEqual(snow["children"][0]["baseStyles"]["color"], "#ffffff")
		self.assertEqual((snow["children"][0]["innerHTML"], snow["blockId"]), ("Snow", "Snow"))

	def test_a_tile_built_differently_becomes_a_relabelled_copy(self):
		photo = self.tile("Street", "/files/street.jpg")
		photo["children"].insert(0, box(backgroundImage="linear-gradient(180deg, transparent, rgba(0,0,0,0.55))"))
		grid = self.grid(self.tile("Snow"), photo, self.tile("Water"))
		self.assertEqual(complete_tile_photos([grid], self.PHOTOS), ["snow", "water"])
		snow = grid["children"][0]
		self.assertEqual(snow["baseStyles"]["backgroundImage"], "url('/files/snow.jpg')")
		self.assertEqual([b["innerHTML"] for b in snow["children"] if b.get("innerHTML")], ["Snow"])
		self.assertEqual(len(snow["children"]), 2)
		self.assertNotEqual(snow["blockId"], photo["blockId"])

	def test_alike_grids_and_tiles_of_no_category_stay(self):
		photos = self.grid(self.tile("Snow", "/files/a.jpg"), self.tile("Street", "/files/b.jpg"), self.tile("Water", "/files/c.jpg"))
		flat = self.grid(self.tile("Snow"), self.tile("Street"), self.tile("Water"))
		other = self.grid(self.tile("Gather"), self.tile("Street", "/files/street.jpg"), self.tile("Camp"))
		self.assertEqual(complete_tile_photos([photos, flat, other], self.PHOTOS), [])
		self.assertEqual(other["children"][0]["baseStyles"]["background"], "#444444")

	def test_the_name_may_sit_in_a_longer_label(self):
		grid = self.grid(self.tile("Snow gear"), self.tile("Street", "/files/street.jpg"), self.tile("Water"))
		self.assertEqual(complete_tile_photos([grid], self.PHOTOS), ["snow", "water"])


class TestLastPhoneRow(unittest.TestCase):
	"""Five framed tiles on the two phone columns their page wrote left a white cell beside the fifth."""

	def grid(self, count, phone="repeat(2, 1fr)", **kid_styles):
		grid = box(*[box(**kid_styles) for _ in range(count)], display="grid", gridTemplateColumns=f"repeat({count}, 1fr)")
		grid["mobileStyles"] = {"gridTemplateColumns": phone}
		return grid

	def test_the_fifth_tile_takes_the_phone_row(self):
		grid = self.grid(5)
		self.assertEqual(fill_last_phone_row([grid]), 1)
		self.assertEqual(grid["children"][-1]["mobileStyles"]["gridColumn"], "1 / -1")
		self.assertNotIn("mobileStyles", grid["children"][0])

	def test_full_rows_repeaters_and_placed_items_stay(self):
		full = self.grid(4)
		two_left = self.grid(5, phone="repeat(3, 1fr)")
		placed = self.grid(5, gridColumn="span 1")
		repeater = self.grid(5)
		repeater["isRepeaterBlock"] = True
		self.assertEqual(fill_last_phone_row([full, two_left, placed, repeater]), 0)

	def test_seven_on_three_leave_the_seventh_the_row(self):
		grid = self.grid(7, phone="repeat(3, minmax(0, 1fr))")
		self.assertEqual(fill_last_phone_row([grid]), 1)
		self.assertEqual(grid["children"][6]["mobileStyles"]["gridColumn"], "1 / -1")


class TestCategoryPhotoMap(unittest.TestCase):
	def photo(self, url, *words):
		return {"url": url, "has_text": False, "landscape": True, "words": set(words), "text": " ".join(words), "quality": "high", "shows": ""}

	def test_each_category_gets_its_own_photograph(self):
		library = [self.photo("/files/water.jpg", "water", "surf"), self.photo("/files/snow.jpg", "snow"), self.photo("/files/street.jpg", "street")]
		self.assertEqual(
			category_photo_map(library, ["Snow", "Street", "Water"]),
			{"Snow": "/files/snow.jpg", "Street": "/files/street.jpg", "Water": "/files/water.jpg"},
		)
		self.assertEqual(category_photo_map([], ["Snow"]), {})


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


class TestCategoryWheel(unittest.TestCase):
	"""A brand whose mark is a circle of segments shows its categories in that shape: one circle, one
	part per category, each on its own photograph (2026-09-15)."""

	NAMES = ["Snow", "Street", "Water", "Outdoor", "Home"]

	def tiles(self, count=5, photos=True):
		return box(
			*[
				box(
					{"element": "a", "attributes": {"href": f"/{name.lower()}"}, "baseStyles": {}, "children": [
						text("h3", name, fontFamily="'Archivo', sans-serif"),
					]},
					backgroundImage=f"url(/files/{name.lower()}.jpg)" if photos else "",
				)
				for name in self.NAMES[:count]
			],
			display="grid",
			gridTemplateColumns="repeat(5, 1fr)",
		)

	def test_the_tiles_become_one_circle_cut_into_parts(self):
		page = [self.tiles()]
		self.assertEqual(1, category_wheel(page, {}))
		wheel = page[0]
		self.assertEqual("50%", wheel["baseStyles"]["borderRadius"])
		self.assertEqual("1", wheel["baseStyles"]["aspectRatio"])
		self.assertNotIn("display", wheel["baseStyles"])
		self.assertNotIn("gridTemplateColumns", wheel["baseStyles"])
		parts = wheel["children"]
		self.assertEqual(5, len(parts))
		self.assertEqual(self.NAMES, [p["children"][0]["innerHTML"] for p in parts])
		self.assertTrue(all(p["baseStyles"]["clipPath"].startswith("polygon(50% 50%") for p in parts))
		# each part keeps its own photograph, its link and the face of its words
		self.assertIn("snow.jpg", parts[0]["baseStyles"]["backgroundImage"])
		self.assertEqual("/snow", parts[0]["attributes"]["href"])
		self.assertEqual("'Archivo', sans-serif", parts[0]["children"][0]["baseStyles"]["fontFamily"])
		# the Builder lets a text block paint its children with its own picture: the words say no
		self.assertEqual("none", parts[0]["children"][0]["baseStyles"]["backgroundImage"])

	def test_the_first_part_opens_at_the_top_and_they_share_the_circle(self):
		page = [self.tiles()]
		category_wheel(page, {})
		firsts = []
		for part in page[0]["children"]:
			point = part["baseStyles"]["clipPath"].split(", ")[1]
			x, y = (float(v.rstrip("%")) for v in point.split())
			firsts.append((x, y))
		# the first part starts just past twelve o'clock, and the five starts are evenly spread
		self.assertAlmostEqual(50.0, firsts[0][0], delta=3)
		self.assertLess(firsts[0][1], 50)
		self.assertEqual(5, len({(round(x), round(y)) for x, y in firsts}))

	def test_each_photograph_is_pushed_towards_the_middle_of_the_circle(self):
		"""Framed towards its own part, the top one showed the sky of its photograph: the picture is
		pushed the other way, so its middle lands inside the part (2026-09-15)."""
		page = [self.tiles()]
		category_wheel(page, {})
		first = page[0]["children"][0]["baseStyles"]["backgroundPosition"]
		x, y = (float(v.rstrip("%")) for v in first.split())
		# the first part points up and to the right, so its picture is pushed down and to the left
		self.assertLess(x, 50)
		self.assertGreater(y, 50)

	def test_what_the_circle_says_is_not_said_twice_beside_it(self):
		"""A page that composes the categories itself draws a large empty circle and a ring of the
		names around it; the tiles become the circle, and those two go (2026-09-15)."""
		section = {
			"element": "section",
			"baseStyles": {},
			"children": [
				box(baseStyles=None, width="640px", height="640px") if False else {"element": "div", "baseStyles": {"width": "640px", "height": "640px"}, "children": []},
				box(
					box(*[text("span", name) for name in self.NAMES]),
					self.tiles(),
				),
			],
		}
		page = [section]
		self.assertEqual(1, category_wheel(page, {}))
		kept = section["children"]
		# the decoration is gone, the inner box stays because the circle is inside it
		self.assertEqual(1, len(kept))
		inner = kept[0]
		self.assertEqual(1, len(inner["children"]))
		wheel = inner["children"][0]
		self.assertEqual("50%", wheel["baseStyles"]["borderRadius"])
		self.assertEqual("min(720px, 100%)", wheel["baseStyles"]["width"])
		self.assertEqual(self.NAMES, [p["children"][0]["innerHTML"] for p in wheel["children"]])

	def test_a_grid_it_cannot_draw_is_left_alone(self):
		flat = [self.tiles(photos=False)]
		self.assertEqual(0, category_wheel(flat, {}))
		self.assertEqual("grid", flat[0]["baseStyles"]["display"])
		pair = [self.tiles(count=2)]
		self.assertEqual(0, category_wheel(pair, {}))
		self.assertEqual("grid", pair[0]["baseStyles"]["display"])

	def test_the_mark_goes_in_the_middle_when_the_site_has_one(self):
		page = [self.tiles()]
		category_wheel(page, {}, hub_image="/files/mark.png")
		hub = page[0]["children"][-1]
		self.assertEqual("wheel-hub", hub["blockName"])
		self.assertEqual("/files/mark.png", hub["children"][0]["attributes"]["src"])
		self.assertEqual(6, len(page[0]["children"]))

	def test_a_repeater_over_the_page_rows_becomes_the_circle(self):
		"""A generated home clones one template over its categories: the rows are the parts."""
		template = box(text("h3", "Category", fontFamily="'Archivo', sans-serif"), position="relative")
		template["isRepeaterBlock"] = 1
		template["dataKey"] = {"key": "categories", "property": "innerHTML", "type": "key"}
		page = [box(template, display="grid", gridTemplateColumns="repeat(5, minmax(0, 1fr))")]
		script = 'data.categories = [' + ", ".join(
			'{"title": "%s", "url": "/brands#%s", "photo": "/files/%s.jpg"}' % (n, n.lower(), n.lower())
			for n in self.NAMES
		) + ']'
		rows = repeater_rows(script)
		self.assertEqual(5, len(rows["categories"]))
		self.assertEqual(1, category_wheel(page, {}, data_rows=rows))
		parts = page[0]["children"]
		self.assertEqual(5, len(parts))
		self.assertEqual(self.NAMES, [p["children"][0]["innerHTML"] for p in parts])
		self.assertIn("street.jpg", parts[1]["baseStyles"]["backgroundImage"])
		self.assertEqual("/brands#street", parts[1]["attributes"]["href"])
		# the words keep the face the template gave them
		self.assertEqual("'Archivo', sans-serif", parts[0]["children"][0]["baseStyles"]["fontFamily"])

	def test_the_repeater_may_be_the_grid_itself(self):
		"""unwrap_grid_wrappers hands the columns to the repeater, so its clones are the grid items:
		the page the wheel was written for is built that way."""
		grid = box(
			box(text("h3", "Category"), position="relative"),
			display="grid",
			gridTemplateColumns="repeat(5, minmax(0, 1fr))",
		)
		grid["isRepeaterBlock"] = 1
		grid["dataKey"] = {"key": "categories", "property": "innerHTML", "type": "key"}
		page = [grid]
		rows = repeater_rows('data.categories = [' + ", ".join(
			'{"title": "%s", "url": "/brands#%s", "photo": "/files/%s.jpg"}' % (n, n.lower(), n.lower())
			for n in self.NAMES
		) + ']')
		self.assertEqual(1, category_wheel(page, {}, data_rows=rows))
		self.assertEqual(self.NAMES, [p["children"][0]["innerHTML"] for p in page[0]["children"]])
		# the circle is drawn part by part, so the binding goes with the rows
		self.assertNotIn("dataKey", page[0])
		self.assertNotIn("isRepeaterBlock", page[0])

	def test_a_repeater_of_the_wrong_size_is_left_alone(self):
		template = box(text("h3", "Category"), position="relative")
		template["isRepeaterBlock"] = 1
		template["dataKey"] = {"key": "logos", "property": "innerHTML", "type": "key"}
		page = [box(template, display="grid")]
		rows = repeater_rows('data.logos = [' + ", ".join('{"title": "L%d", "photo": "/files/l%d.png"}' % (i, i) for i in range(9)) + ']')
		self.assertEqual(0, category_wheel(page, {}, data_rows=rows))
		self.assertEqual("grid", page[0]["baseStyles"]["display"])

	def test_a_tile_without_a_photograph_takes_its_category_one(self):
		page = [self.tiles(photos=False)]
		photos = {name: f"/files/{name.lower()}.jpg" for name in self.NAMES}
		self.assertEqual(1, category_wheel(page, photos))
		self.assertIn("water.jpg", page[0]["children"][2]["baseStyles"]["backgroundImage"])


# //// Neoffice — added tests (2026-09-15): one photograph, one place on a page.
class TestOnePhotoOnce(unittest.TestCase):
	def page(self, *urls):
		return [{
			"element": "div",
			"children": [
				{"element": "section", "children": [{"element": "img", "attributes": {"src": url}}]}
				for url in urls
			],
		}]

	def shown(self, blocks):
		found = []

		def walk(b):
			if b.get("element") == "img":
				found.append((b.get("attributes") or {}).get("src"))
			for c in b.get("children") or []:
				walk(c)

		for b in blocks:
			walk(b)
		return found

	def test_a_photograph_shown_twice_takes_an_unused_one(self):
		from builder.site_ai.nora.layout import one_photo_once

		blocks = self.page("/files/a.jpg", "/files/b.jpg", "/files/a.jpg")
		swaps = one_photo_once(blocks, ["/files/a.jpg", "/files/b.jpg", "/files/c.jpg"])
		self.assertEqual(1, len(swaps))
		self.assertEqual(["/files/a.jpg", "/files/b.jpg", "/files/c.jpg"], self.shown(blocks))

	def test_with_nothing_left_the_repeat_stays(self):
		from builder.site_ai.nora.layout import one_photo_once

		blocks = self.page("/files/a.jpg", "/files/a.jpg")
		self.assertEqual([], one_photo_once(blocks, ["/files/a.jpg"]))
		self.assertEqual(["/files/a.jpg", "/files/a.jpg"], self.shown(blocks))

	def test_a_background_photograph_counts_too(self):
		from builder.site_ai.nora.layout import one_photo_once

		blocks = [{
			"element": "div",
			"children": [
				{"element": "section", "baseStyles": {"backgroundImage": "url('/files/a.jpg')"}},
				{"element": "section", "baseStyles": {"backgroundImage": "url('/files/a.jpg')"}},
			],
		}]
		one_photo_once(blocks, ["/files/a.jpg", "/files/b.jpg"])
		backgrounds = [c["baseStyles"]["backgroundImage"] for c in blocks[0]["children"]]
		self.assertEqual(["url('/files/a.jpg')", "url('/files/b.jpg')"], backgrounds)

	def test_a_page_that_repeats_nothing_is_left_alone(self):
		from builder.site_ai.nora.layout import one_photo_once

		blocks = self.page("/files/a.jpg", "/files/b.jpg")
		self.assertEqual([], one_photo_once(blocks, ["/files/a.jpg", "/files/b.jpg", "/files/c.jpg"]))
		self.assertEqual(["/files/a.jpg", "/files/b.jpg"], self.shown(blocks))


# //// Neoffice — added tests (2026-09-15): the emblem is an ornament or it is nothing.
class TestDropSmallMarks(unittest.TestCase):
	def page(self, *sizes):
		return [{
			"element": "div",
			"children": [
				{"element": "div", "children": [
					{"element": "img", "attributes": {"src": "/files/emblem.png"}, "baseStyles": ({"width": s} if s else {})},
					{"element": "h2", "innerHTML": "Dealer lineup"},
				]}
				for s in sizes
			],
		}]

	def marks(self, blocks):
		found = []

		def walk(b):
			if b.get("element") == "img":
				found.append((b.get("attributes") or {}).get("src"))
			for c in b.get("children") or []:
				walk(c)

		for b in blocks:
			walk(b)
		return found

	def test_a_bullet_sized_emblem_is_removed(self):
		from builder.site_ai.nora.layout import drop_small_marks

		blocks = self.page("32px")
		self.assertEqual(1, len(drop_small_marks(blocks, "/files/emblem.png")))
		self.assertEqual([], self.marks(blocks))

	def test_an_emblem_with_no_declared_size_is_removed(self):
		from builder.site_ai.nora.layout import drop_small_marks

		blocks = self.page(None)
		self.assertEqual(1, len(drop_small_marks(blocks, "/files/emblem.png")))
		self.assertEqual([], self.marks(blocks))

	def test_an_emblem_drawn_as_an_ornament_stays(self):
		from builder.site_ai.nora.layout import drop_small_marks

		blocks = self.page("420px")
		self.assertEqual([], drop_small_marks(blocks, "/files/emblem.png"))
		self.assertEqual(["/files/emblem.png"], self.marks(blocks))

	def test_another_picture_is_never_touched(self):
		from builder.site_ai.nora.layout import drop_small_marks

		blocks = [{"element": "div", "children": [{"element": "img", "attributes": {"src": "/files/photo.jpg"}, "baseStyles": {"width": "40px"}}]}]
		self.assertEqual([], drop_small_marks(blocks, "/files/emblem.png"))
		self.assertEqual(["/files/photo.jpg"], self.marks(blocks))


# //// Neoffice — added tests (2026-09-15): copy inside a scrim reads on the scrim.
class TestReadOverPhotos(unittest.TestCase):
	PALETTE = {"x-primary": "#111111", "x-background": "#ffffff", "x-text": "#111111"}

	def hero(self, *children):
		return {"element": "section", "classes": ["u-over-image", "u-over-image--bottom"], "children": list(children)}

	def test_dark_copy_on_a_scrim_takes_the_reading_ink(self):
		from builder.site_ai.nora.contrast import read_over_photos

		link = {"element": "a", "innerHTML": "Shop now", "baseStyles": {"color": "#000000"}}
		title = {"element": "h1", "innerHTML": "The shop", "baseStyles": {"color": "#ffffff"}}
		blocks = [self.hero(title, link)]
		fixes = read_over_photos(blocks, self.PALETTE)
		self.assertEqual(1, len(fixes))
		self.assertEqual("#ffffff", link["baseStyles"]["color"])
		self.assertEqual("#ffffff", title["baseStyles"]["color"])

	def test_a_card_painting_its_own_background_keeps_its_colours(self):
		from builder.site_ai.nora.contrast import read_over_photos

		card = {"element": "div", "baseStyles": {"backgroundColor": "#ffffff"}, "children": [
			{"element": "p", "innerHTML": "Читать", "baseStyles": {"color": "#111111"}},
		]}
		blocks = [self.hero(card)]
		self.assertEqual([], read_over_photos(blocks, self.PALETTE))
		self.assertEqual("#111111", card["children"][0]["baseStyles"]["color"])

	def test_a_section_without_a_scrim_is_left_alone(self):
		from builder.site_ai.nora.contrast import read_over_photos

		plain = {"element": "section", "children": [{"element": "p", "innerHTML": "Hi", "baseStyles": {"color": "#000000"}}]}
		self.assertEqual([], read_over_photos([plain], self.PALETTE))
		self.assertEqual("#000000", plain["children"][0]["baseStyles"]["color"])

