# //// Neoffice — added file (no upstream equivalent): a category tile leads to its own panel
# //// (builder/site_ai/nora/anchors.py).
import unittest

from builder.site_ai.nora.anchors import (
	anchor_category_data_links,
	anchor_category_links,
	anchor_category_panels,
	anchor_repeated_panels,
	category_slug,
)

CATEGORIES = ["Snow", "Street", "Water"]


def text(element, words, **extra):
	return {"element": element, "innerHTML": words, **extra}


def box(*children, **extra):
	return {"element": "div", "children": list(children), **extra}


def photo(src="/files/a.jpg"):
	return {"element": "img", "attributes": {"src": src}}


def link(href, *children, words=""):
	block = {"element": "a", "attributes": {"href": href}, "children": list(children)}
	if words:
		block["innerHTML"] = words
	return block


class TestCategorySlug(unittest.TestCase):
	def test_slugs(self):
		self.assertEqual(category_slug("Outdoor Gear"), "outdoor-gear")
		self.assertEqual(category_slug("Été & Hiver"), "ete-hiver")


class TestPanels(unittest.TestCase):
	def test_each_panel_of_the_listing_page_gets_its_anchor(self):
		panels = [
			box(photo(), text("h2", name), text("p", f"All about {name.lower()}.")) for name in CATEGORIES
		]
		page = [box(box(text("h1", "Brands"), *panels))]
		self.assertEqual(len(anchor_category_panels(page, CATEGORIES)), 3)
		self.assertEqual([p["attributes"]["id"] for p in panels], ["snow", "street", "water"])
		# a sticky header does not cover the panel it scrolls to
		self.assertIn("scrollMarginTop", panels[0]["baseStyles"])

	def test_the_section_holding_every_category_is_not_one_panel(self):
		# the pictures sit in the section, not around each heading: the headings get the anchors
		headings = [text("h3", name) for name in CATEGORIES]
		section = box(photo(), *headings)
		anchor_category_panels([section], CATEGORIES)
		self.assertNotIn("id", section.get("attributes") or {})
		self.assertEqual([h["attributes"]["id"] for h in headings], ["snow", "street", "water"])

	def test_an_existing_id_is_kept(self):
		heading = text("h2", "Snow")
		panel = box(photo(), heading, attributes={"id": "winter"})
		anchor_category_panels([panel], ["Snow"])
		self.assertEqual(panel["attributes"]["id"], "winter")
		self.assertEqual(heading["attributes"]["id"], "snow")

	def test_a_category_the_page_does_not_show_is_skipped(self):
		self.assertEqual(anchor_category_panels([box(text("h2", "Brands"))], CATEGORIES), [])


class TestLinks(unittest.TestCase):
	def test_a_tile_to_the_listing_page_points_at_its_panel(self):
		# the tile's link says "Explore": the tile around it names the category
		explore = link("/brands", words="Explore")
		tile = box(photo(), text("h3", "Street"), explore)
		edits = anchor_category_links([box(tile)], "/brands", CATEGORIES)
		self.assertEqual(explore["attributes"]["href"], "/brands#street")
		self.assertEqual(len(edits), 1)

	def test_a_link_wrapping_the_whole_tile(self):
		tile = link("/brands", photo(), text("h3", "Water"))
		anchor_category_links([tile], "/brands", CATEGORIES)
		self.assertEqual(tile["attributes"]["href"], "/brands#water")

	def test_links_that_name_no_category_or_several_are_left_alone(self):
		all_brands = link("/brands", words="See all brands")
		two = link("/brands", words="Snow and Street")
		anchored = link("/brands#snow", words="Snow")
		elsewhere = link("/contact", words="Snow")
		anchor_category_links([box(all_brands, two, anchored, elsewhere)], "/brands", CATEGORIES)
		self.assertEqual(all_brands["attributes"]["href"], "/brands")
		self.assertEqual(two["attributes"]["href"], "/brands")
		self.assertEqual(anchored["attributes"]["href"], "/brands#snow")
		self.assertEqual(elsewhere["attributes"]["href"], "/contact")

	def test_a_word_inside_another_is_not_the_category(self):
		self.assertEqual(
			anchor_category_links([link("/brands", words="Snowboards")], "/brands", ["Snow"]), []
		)


class TestDataLinks(unittest.TestCase):
	def test_the_data_script_tiles_point_at_their_panels(self):
		script = (
			'data.tiles = [{"title": "Snow", "image": "/files/a.jpg", "route": "/brands"}, '
			'{"title": "Street", "route": "/brands/"}, {"title": "All", "route": "/brands"}]'
		)
		new, edits = anchor_category_data_links(script, "/brands", CATEGORIES)
		self.assertIn('"route": "/brands#snow"', new)
		self.assertIn('"route": "/brands/#street"', new)
		self.assertIn('{"title": "All", "route": "/brands"}', new)
		self.assertEqual(len(edits), 2)

	def test_a_key_the_page_binds_to_an_href(self):
		new, _ = anchor_category_data_links(
			'[{"name": "Water", "slug": "/brands"}]', "/brands", CATEGORIES, {"slug"}
		)
		self.assertIn('"slug": "/brands#water"', new)


class TestRepeatedPanels(unittest.TestCase):
	"""A listing page drawing its five category panels by repeating one block over its data
	script: the names bound, no heading to anchor (2026-09-13)."""

	def page(self):
		item = {
			"element": "a",
			"dynamicValues": [{"key": "path", "property": "href", "type": "attribute"}],
			"children": [
				{
					"element": "img",
					"dynamicValues": [{"key": "image", "property": "src", "type": "attribute"}],
				},
				{"element": "h2", "dynamicValues": [{"key": "name", "property": "innerHTML", "type": "key"}]},
			],
		}
		repeater = {
			"element": "div",
			"isRepeaterBlock": True,
			"dataKey": {"key": "cultures"},
			"children": [item],
		}
		return [{"element": "div", "children": [repeater]}], item

	def test_each_repeated_panel_gets_its_anchor(self):
		blocks, item = self.page()
		script = (
			'data.cultures = [{"name":"Snow","path":"/brands"},{"name":"Street","path":"/brands"},'
			'{"name":"Water","path":"/brands"}]'
		)
		new, edits = anchor_repeated_panels(blocks, script, CATEGORIES)
		self.assertIn('{"anchor": "snow", "name":"Snow"', new)
		self.assertIn('{"anchor": "water", "name":"Water"', new)
		self.assertIn({"key": "anchor", "property": "id", "type": "attribute"}, item["dynamicValues"])
		self.assertIn("scrollMarginTop", item["baseStyles"])
		self.assertEqual(len(edits), 1)
		# a second pass adds nothing
		again, _ = anchor_repeated_panels(blocks, new, CATEGORIES)
		self.assertEqual(again, new)
		self.assertEqual(sum(1 for d in item["dynamicValues"] if d["property"] == "id"), 1)

	def test_a_list_with_an_entry_of_no_category_is_left_alone(self):
		blocks, item = self.page()
		script = 'data.cultures = [{"name":"Snow"},{"name":"Gift cards"}]'
		self.assertEqual(anchor_repeated_panels(blocks, script, CATEGORIES), (script, []))
		self.assertNotIn("baseStyles", item)
