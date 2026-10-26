# //// Neoffice — added file (no upstream equivalent): a menu that does not repeat the header's button, a page that does not repeat its band.
"""Two faults a visitor sees at once (2026-10-26, a client's regenerated site): "Contact" in the menu beside a "Contact us" button that leads
to the same page, and the contact page opening on a band that says "Contact" over a first heading that says "Contact" again (the heading was
a flex row of a dot and a span, so it had no text of its own and nothing matched). Pinned here: the menu leaves out the page the call to action
leads to (and the home, and the legal pages); a heading repeats the band's title however it is nested, with or without its article, and a
heading that says something else stays. No model, no database."""

import unittest

from builder.site_ai.nora.layout import repeats_title, strip_title_band
from builder.site_ai.nora.site_builder import menu_pages


def page(route, title=None):
	return {"route": route, "title": title or route.strip("/").title(), "name": route}


class TestTheMenuDoesNotRepeatTheButton(unittest.TestCase):
	PAGES = (page("/home", "Accueil"), page("/about", "À propos"), page("/services"), page("/contact"), page("/privacy-policy"), page("/legal-notice"))

	def test_the_page_the_button_leads_to_is_not_in_the_menu(self):
		routes = [p["route"] for p in menu_pages(list(self.PAGES), "/contact")]
		self.assertEqual(["/about", "/services"], routes)

	def test_without_a_button_page_the_contact_page_stays(self):
		routes = [p["route"] for p in menu_pages(list(self.PAGES), "/")]
		self.assertEqual(["/about", "/services", "/contact"], routes)
		self.assertEqual(["/about", "/services", "/contact"], [p["route"] for p in menu_pages(list(self.PAGES))])

	def test_an_anchor_or_a_trailing_slash_does_not_hide_the_page(self):
		for cta in ("/contact#form", "/contact/", "/contact?x=1".split("?")[0]):
			self.assertNotIn("/contact", [p["route"] for p in menu_pages(list(self.PAGES), cta)], cta)

	def test_a_button_that_asks_for_an_account_leaves_the_menu_alone(self):
		self.assertEqual(["/about", "/services", "/contact"], [p["route"] for p in menu_pages(list(self.PAGES), "/business-account")])

	def test_the_home_and_the_legal_pages_are_never_in_the_menu_and_a_page_is_listed_once(self):
		pages = [*self.PAGES, page("/about", "À propos bis")]
		self.assertEqual(["/about", "/services", "/contact"], [p["route"] for p in menu_pages(pages, "")])

	def test_the_pages_are_not_changed(self):
		pages = list(self.PAGES)
		menu_pages(pages, "/contact")
		self.assertEqual(list(self.PAGES), pages)


def heading(*kids, tag="h2"):
	return {"element": tag, "baseStyles": {"display": "flex"}, "children": list(kids)}


def span(text=""):
	return {"element": "span", "innerHTML": text, "children": []}


def para(text):
	return {"element": "p", "innerHTML": text, "children": []}


def first_section(*kids):
	return [{"element": "div", "children": [{"element": "section", "children": [{"element": "div", "children": list(kids)}]}]}]


class TestAPageDoesNotRepeatItsBand(unittest.TestCase):
	def test_a_heading_made_of_a_dot_and_a_span_repeats_the_title(self):
		"""The case of the client's contact page: the text is in a child span, the heading has none of its own."""
		title = heading(span(), span("Contact"))
		blocks = first_section(title, para("Region · Town · Valley"), para("A question, a fault ?"), para("Since the beginning"))
		self.assertEqual(1, strip_title_band(blocks, "Contact"))
		inner = blocks[0]["children"][0]["children"][0]["children"]
		self.assertNotIn(title, inner)
		self.assertEqual(3, len(inner), "the lines under the heading stay")

	def test_a_first_section_that_is_only_that_heading_and_a_line_goes(self):
		blocks = first_section(heading(span(), span("Contact")), para("Écrivez-nous"))
		self.assertEqual(1, strip_title_band(blocks, "Contact"))
		self.assertEqual([], blocks[0]["children"])

	def test_the_article_is_not_part_of_the_title(self):
		self.assertTrue(repeats_title("nos services", "services"))
		self.assertTrue(repeats_title("services", "nos services"))
		self.assertTrue(repeats_title("notre equipe", "equipe"))
		self.assertTrue(repeats_title("our services", "services"))

	def test_the_ways_a_page_says_contact_are_one_title(self):
		for said in ("contactez nous", "nous contacter", "contact us", "contact", "kontakt", "contattaci"):
			self.assertTrue(repeats_title(said, "contact"), said)
		self.assertTrue(repeats_title("contact", "nous contacter"))

	def test_a_heading_that_says_something_else_stays(self):
		self.assertFalse(repeats_title("une question une panne un projet", "contact"))
		self.assertFalse(repeats_title("notre histoire", "a propos"))
		self.assertFalse(repeats_title("services informatiques pour les particuliers", "services"))
		self.assertFalse(repeats_title("", "contact"))
		self.assertFalse(repeats_title("contact", ""))
		self.assertFalse(repeats_title("contact", "services"))

	def test_a_page_whose_first_heading_says_something_else_is_left_alone(self):
		blocks = first_section(heading(span(), span("Une question ?")), para("Écrivez-nous"), para("Ou appelez"), para("Since the beginning"))
		self.assertEqual(0, strip_title_band(blocks, "Contact"))

	def test_a_plain_heading_still_works(self):
		blocks = first_section({"element": "h1", "innerHTML": "Contact", "children": []}, para("a"), para("b"), para("c"))
		self.assertEqual(1, strip_title_band(blocks, "Contact"))


if __name__ == "__main__":
	unittest.main()
