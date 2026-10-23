# //// Neoffice — added file (no upstream equivalent): every picture of a generated page has an alt text.
"""The pass after the writer (alt_text.py): a picture with no usable alt gets the heading of its card or section, else the page's
title, else the site's name; a logo is the site's name; a decorative picture keeps its empty alt; the writer's own alt is never
touched. No model is called."""

import unittest

from builder.site_ai.nora import alt_text


def img(src="/files/a.jpg", alt=None, **extra):
	attrs = {"src": src}
	if alt is not None:
		attrs["alt"] = alt
	attrs.update(extra)
	return {"element": "img", "attributes": attrs}


def text(tag, value):
	return {"element": tag, "innerHTML": value}


def body(*sections):
	return [{"element": "div", "blockName": "body", "children": list(sections)}]


def section(*children):
	return {"element": "section", "children": list(children)}


def alts(blocks):
	out = []
	stack = list(blocks)
	while stack:
		b = stack.pop(0)
		if b.get("element") == "img":
			out.append((b.get("attributes") or {}).get("alt"))
		stack = list(b.get("children") or []) + stack
	return out


class TestWhatIsNotAnAlt(unittest.TestCase):
	def test_missing_blank_and_meaningless_alts_are_poor(self):
		for poor in (None, "", "  ", "ab", "image", "Image 3", "photo_12", "IMG_2041.jpg", "hero.png", "WRITE alt: a scene", "https://x.example/a.jpg", "placehold.co 1200x800"):
			self.assertTrue(alt_text.is_poor(poor), repr(poor))

	def test_a_description_is_not_poor(self):
		for good in ("A cheese counter lit from the side", "Notre cuisine ouverte", "Chef plating a dish in the evening light"):
			self.assertFalse(alt_text.is_poor(good), good)


class TestEveryPictureGetsOne(unittest.TestCase):
	def test_a_picture_in_a_card_takes_the_heading_of_its_card(self):
		blocks = body(section({"element": "div", "children": [img(), text("h3", "Fondue maison")]}, {"element": "div", "children": [img("/files/b.jpg"), text("h3", "Raclette")]}))
		alt_text.ensure_alts(blocks, "La carte", "Chez Test")
		self.assertCountEqual(["Fondue maison", "Raclette"], alts(blocks))

	def test_a_picture_in_a_section_with_one_heading_takes_it(self):
		blocks = body(section(img(), text("h2", "Une cuisine de saison")))
		alt_text.ensure_alts(blocks, "Accueil", "Chez Test")
		self.assertEqual(["Une cuisine de saison"], alts(blocks))

	def test_a_tag_does_not_leave_a_space_before_the_punctuation(self):
		blocks = body(section(img(), text("h2", "Nos <em>spécialités</em>.")))
		alt_text.ensure_alts(blocks, "Accueil", "Chez Test")
		self.assertEqual(["Nos spécialités."], alts(blocks))

	def test_a_line_break_is_a_space(self):
		blocks = body(section(img(), text("h2", "Nos vins<br>et nos fromages")))
		alt_text.ensure_alts(blocks, "Accueil", "Chez Test")
		self.assertEqual(["Nos vins et nos fromages"], alts(blocks))

	def test_a_heading_inside_a_tag_is_read_as_text(self):
		blocks = body(section(img(), text("h2", "Notre <em>histoire</em>")))
		alt_text.ensure_alts(blocks, "Accueil", "Chez Test")
		self.assertEqual(["Notre histoire"], alts(blocks))

	def test_a_picture_among_several_headings_takes_the_title_of_the_page_not_the_first_card(self):
		blocks = body(section(img(), {"element": "div", "children": [text("h3", "A"), text("h3", "B")]}))
		alt_text.ensure_alts(blocks, "La carte", "Chez Test")
		self.assertEqual(["La carte"], alts(blocks))

	def test_with_no_heading_and_no_title_the_name_of_the_site_stands_in(self):
		blocks = body(section(img()))
		alt_text.ensure_alts(blocks, "", "Chez Test")
		self.assertEqual(["Chez Test"], alts(blocks))

	def test_a_logo_is_the_name_of_the_site(self):
		blocks = body(section(img("/files/logo-default.png"), text("h2", "Bienvenue")))
		alt_text.ensure_alts(blocks, "Accueil", "Chez Test")
		self.assertEqual(["Chez Test"], alts(blocks))

	def test_a_file_name_is_replaced(self):
		blocks = body(section(img(alt="IMG_2041.jpg"), text("h2", "Nos vins")))
		alt_text.ensure_alts(blocks, "Cave", "Chez Test")
		self.assertEqual(["Nos vins"], alts(blocks))

	def test_a_long_heading_is_cut_at_a_word(self):
		blocks = body(section(img(), text("h2", "mot " * 60)))
		alt_text.ensure_alts(blocks, "P", "S")
		self.assertLessEqual(len(alts(blocks)[0]), alt_text.MAX_ALT)


class TestWhatIsLeftAlone(unittest.TestCase):
	def test_the_alt_of_the_writer_is_never_touched(self):
		blocks = body(section(img(alt="A baker folding dough at dawn"), text("h2", "Pain")))
		self.assertEqual([], alt_text.ensure_alts(blocks, "Accueil", "Chez Test"))
		self.assertEqual(["A baker folding dough at dawn"], alts(blocks))

	def test_an_icon_keeps_its_empty_alt(self):
		blocks = body(section(img("/files/icon.svg", alt=""), text("h2", "Pain")))
		self.assertEqual([], alt_text.ensure_alts(blocks, "Accueil", "Chez Test"))
		self.assertEqual([""], alts(blocks))

	def test_a_picture_marked_decorative_keeps_its_empty_alt(self):
		blocks = body(section(img(alt="", **{"aria-hidden": "true"}), text("h2", "Pain")))
		alt_text.ensure_alts(blocks, "Accueil", "Chez Test")
		self.assertEqual([""], alts(blocks))

	def test_an_svg_with_no_alt_gets_the_empty_one(self):
		blocks = body(section(img("/files/mark.svg"), text("h2", "Pain")))
		alt_text.ensure_alts(blocks, "Accueil", "Chez Test")
		self.assertEqual([""], alts(blocks))

	def test_a_photograph_with_an_empty_alt_is_not_decorative(self):
		blocks = body(section(img(alt=""), text("h2", "Pain")))
		alt_text.ensure_alts(blocks, "Accueil", "Chez Test")
		self.assertEqual(["Pain"], alts(blocks))

	def test_a_page_without_pictures_is_untouched(self):
		self.assertEqual([], alt_text.ensure_alts(body(section(text("h2", "Pain"))), "Accueil", "Chez Test"))
		self.assertEqual([], alt_text.ensure_alts([], "Accueil", "Chez Test"))


def bound(element, prop, key, **extra):
	node = {"element": element, "dynamicValues": [{"key": key, "property": prop, "type": "key" if prop == "innerHTML" else "attribute"}]}
	node.update(extra)
	return node


def repeated_card(*children):
	return {"element": "div", "isRepeaterBlock": True, "children": [{"element": "div", "children": list(children)}]}


class TestThePicturesOfARepeatedCard(unittest.TestCase):
	"""The picture of a card repeated over the page data takes its src from the item: its alt is the title of the same item, not one
	text for every card (seen as the open question of the 22.10 review)."""

	def card(self, alt=None, alt_bound=False):
		picture = bound("img", "src", "image", attributes={"src": ""} if alt is None else {"src": "", "alt": alt})
		if alt_bound:
			picture["dynamicValues"].append({"key": "caption", "property": "alt", "type": "attribute"})
		return repeated_card(picture, bound("h3", "innerHTML", "title", innerHTML=""))

	def test_the_alt_is_bound_to_the_field_the_heading_of_the_card_shows(self):
		blocks = body(section(self.card()))
		edits = alt_text.ensure_alts(blocks, "La carte", "Chez Test")
		picture = blocks[0]["children"][0]["children"][0]["children"][0]["children"][0]
		self.assertIn({"key": "title", "property": "alt", "type": "attribute"}, picture["dynamicValues"])
		self.assertEqual(1, len(edits))
		self.assertIn("title", edits[0])

	def test_an_alt_the_writer_bound_is_left_alone(self):
		blocks = body(section(self.card(alt_bound=True)))
		self.assertEqual([], alt_text.ensure_alts(blocks, "La carte", "Chez Test"))
		picture = blocks[0]["children"][0]["children"][0]["children"][0]["children"][0]
		self.assertEqual(1, sum(1 for d in picture["dynamicValues"] if d["property"] == "alt"))

	def test_a_bound_alt_is_not_a_missing_one(self):
		blocks = body(section(self.card(alt_bound=True)))
		self.assertEqual([], alt_text.pictures_without_alt(blocks))

	def test_after_the_pass_the_card_picture_is_not_missing(self):
		blocks = body(section(self.card()))
		self.assertNotEqual([], alt_text.pictures_without_alt(blocks))
		alt_text.ensure_alts(blocks, "La carte", "Chez Test")
		self.assertEqual([], alt_text.pictures_without_alt(blocks))

	def test_a_repeated_picture_with_no_heading_takes_the_title_of_the_page(self):
		picture = bound("img", "src", "image", attributes={"src": ""})
		blocks = body(section(repeated_card(picture)))
		alt_text.ensure_alts(blocks, "La carte", "Chez Test")
		self.assertEqual("La carte", picture["attributes"]["alt"])
		self.assertNotIn("alt", [d["property"] for d in picture["dynamicValues"]])


class TestNothingIsLeftWithoutOne(unittest.TestCase):
	def test_after_the_pass_no_picture_reads_as_nothing(self):
		blocks = body(
			section(img(), text("h2", "Premier")),
			section(img(alt="photo_3.jpg"), text("h2", "Deuxième")),
			section(img(alt=""), {"element": "div", "children": [img("/files/c.jpg"), text("h3", "Troisième")]}),
			section(img("/files/i.svg", alt=""), img("/files/logo.png")),
		)
		self.assertNotEqual([], alt_text.pictures_without_alt(blocks))
		alt_text.ensure_alts(blocks, "Accueil", "Chez Test")
		self.assertEqual([], alt_text.pictures_without_alt(blocks))


if __name__ == "__main__":
	unittest.main()
